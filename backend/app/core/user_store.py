"""
Redis-backed persistence for users, Jira configuration, and API keys.
"""

from redis.asyncio import Redis
from redis.exceptions import WatchError

import json
from app.core.security import get_secret_lookup_hash, verify_secret
from app.models.models import JiraCacheContext, JiraConfig, Project, StoredAPIKey, UserInDB, UserCore, Ticket


class RedisUserStore:
    def __init__(self, redis: Redis):
        self.redis = redis

    @classmethod
    def from_url(cls, redis_url: str) -> "RedisUserStore":
        return cls(Redis.from_url(redis_url, decode_responses=True))

    @staticmethod
    def _user_core_key(username: str) -> str:
        return f"user:{username}:core"

    @staticmethod
    def _user_jira_config_key(username: str) -> str:
        return f"user:{username}:jira_config"

    @staticmethod
    def _user_jira_cache_context_key(username: str) -> str:
        return f"user:{username}:jira_cache_context"
    
    @staticmethod
    def _user_api_keys_set_key(username: str) -> str:
        return f"user:{username}:api_keys_set"

    @staticmethod
    def _api_key_obj_key(key_id: str) -> str:
        return f"api_key:{key_id}"

    @staticmethod
    def _api_key_lookup_key(lookup_hash: str) -> str:
        return f"api_key_lookup:{lookup_hash}"

    @staticmethod
    def _refresh_session_key(session_id: str) -> str:
        return f"refresh_session:{session_id}"

    @staticmethod
    def _oauth_state_key(state: str) -> str:
        return f"oauth_state:{state}"

    @staticmethod
    def _jira_tickets_cache_key(cloud_id: str, project_key: str) -> str:
        return f"jira:{cloud_id}:{project_key}:latest_tickets"

    @staticmethod
    def _jira_projects_cache_key(cloud_id: str) -> str:
        return f"jira:{cloud_id}:projects"

    async def close(self) -> None:
        await self.redis.aclose()

    @staticmethod
    def _decode_redis_value(value: str | bytes | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode()
        return value

    async def get_user(self, username: str) -> UserInDB | None:
        user_core_raw = await self.redis.get(self._user_core_key(username))
        if user_core_raw is None:
            return None
        user_core = UserCore.model_validate_json(self._decode_redis_value(user_core_raw))

        jira_config: JiraConfig | None = None
        jira_config_raw = await self.redis.get(self._user_jira_config_key(username))
        if jira_config_raw:
            jira_config = JiraConfig.model_validate_json(self._decode_redis_value(jira_config_raw))

        api_keys: list[StoredAPIKey] = []
        api_key_ids = await self.redis.smembers(self._user_api_keys_set_key(username))
        for key_id in api_key_ids:
            normalized_key_id = self._decode_redis_value(key_id)
            if normalized_key_id is None:
                continue
            api_key_raw = await self.redis.get(self._api_key_obj_key(normalized_key_id))
            if api_key_raw:
                api_keys.append(
                    StoredAPIKey.model_validate_json(self._decode_redis_value(api_key_raw))
                )
        
        return UserInDB(
            username=user_core.username,
            email=user_core.email,
            password_hash=user_core.password_hash,
            jira_config=jira_config,
            api_keys=api_keys,
        )

    async def user_exists(self, username: str) -> bool:
        return bool(await self.redis.exists(self._user_core_key(username)))

    async def create_user(self, username: str, email: str, password_hash: str) -> UserInDB:
        if await self.user_exists(username):
            # This check might be redundant if done before calling create_user, but good for safety
            raise ValueError(f"Username {username} already exists")

        user_core = UserCore(username=username, email=email, password_hash=password_hash)
        await self.redis.set(self._user_core_key(username), user_core.model_dump_json())

        return await self.get_user(username) # Return composed UserInDB

    async def set_jira_config(self, username: str, jira_config: JiraConfig | None) -> UserInDB | None: # Updated type hint
        if not await self.user_exists(username):
            return None
        
        if jira_config:
            await self.redis.set(self._user_jira_config_key(username), jira_config.model_dump_json())
        else:
            await self.redis.delete(self._user_jira_config_key(username)) # Delete if None
        
        return await self.get_user(username)

    async def get_jira_cache_context(self, username: str) -> JiraCacheContext | None:
        cache_context_raw = await self.redis.get(self._user_jira_cache_context_key(username))
        if cache_context_raw is None:
            return None
        return JiraCacheContext.model_validate_json(self._decode_redis_value(cache_context_raw))

    async def set_jira_cache_context(self, username: str, cache_context: JiraCacheContext | None) -> None:
        if cache_context is None:
            await self.redis.delete(self._user_jira_cache_context_key(username))
            return

        await self.redis.set(
            self._user_jira_cache_context_key(username),
            cache_context.model_dump_json(),
        )

    async def add_api_key(self, username: str, api_key: StoredAPIKey) -> UserInDB | None:
        if not await self.user_exists(username):
            return None
        
        # Ensure API key is linked to the correct user
        api_key.username = username
        await self.redis.sadd(self._user_api_keys_set_key(username), api_key.id)
        await self.redis.set(self._api_key_obj_key(api_key.id), api_key.model_dump_json())
        if api_key.lookup_hash:
            await self.redis.set(self._api_key_lookup_key(api_key.lookup_hash), api_key.id)
        return await self.get_user(username)

    async def revoke_api_key(self, username: str, key_id: str) -> bool:
        if not await self.user_exists(username):
            return False
        
        # Check if the key belongs to the user before deleting
        api_key_raw = await self.redis.get(self._api_key_obj_key(key_id))
        if not api_key_raw:
            return False
        stored_api_key = StoredAPIKey.model_validate_json(self._decode_redis_value(api_key_raw))
        if stored_api_key.username != username:
            return False # Key does not belong to this user

        await self.redis.srem(self._user_api_keys_set_key(username), key_id)
        await self.redis.delete(self._api_key_obj_key(key_id))
        if stored_api_key.lookup_hash:
            await self.redis.delete(self._api_key_lookup_key(stored_api_key.lookup_hash))
        return True

    async def find_user_by_api_key(self, plain_api_key: str) -> UserInDB | None:
        lookup_hash = get_secret_lookup_hash(plain_api_key)
        key_id = await self.redis.get(self._api_key_lookup_key(lookup_hash))
        normalized_key_id = self._decode_redis_value(key_id)
        if normalized_key_id is None:
            return None

        api_key_raw = await self.redis.get(self._api_key_obj_key(normalized_key_id))
        if api_key_raw:
            stored_api_key = StoredAPIKey.model_validate_json(self._decode_redis_value(api_key_raw))
            if verify_secret(plain_api_key, stored_api_key.key_hash):
                return await self.get_user(stored_api_key.username)
        return None

    async def create_refresh_session(self, session_id: str, username: str, ttl_seconds: int) -> None:
        await self.redis.set(self._refresh_session_key(session_id), username, ex=ttl_seconds)

    async def get_refresh_session_username(self, session_id: str) -> str | None:
        value = await self.redis.get(self._refresh_session_key(session_id))
        return self._decode_redis_value(value)

    async def revoke_refresh_session(self, session_id: str) -> None:
        await self.redis.delete(self._refresh_session_key(session_id))

    async def store_oauth_state(self, state: str, username: str, ttl_seconds: int) -> None:
        await self.redis.set(self._oauth_state_key(state), username, ex=ttl_seconds)

    async def pop_oauth_state(self, state: str) -> str | None:
        key = self._oauth_state_key(state)
        async with self.redis.pipeline(transaction=True) as pipe:
            while True:
                try:
                    await pipe.watch(key)
                    current_username = await pipe.get(key)
                    pipe.multi()
                    pipe.delete(key)
                    await pipe.execute()
                    return self._decode_redis_value(current_username)
                except WatchError:
                    continue

    async def save_jira_tickets_cache(self, cloud_id: str, project_key: str, tickets: list[Ticket], ttl: int = 300) -> None:
        key = self._jira_tickets_cache_key(cloud_id, project_key)
        await self.redis.set(key, json.dumps([t.model_dump(mode='json') for t in tickets]), ex=ttl) 
    
    async def get_jira_tickets_cache(self, cloud_id: str, project_key: str) -> list[Ticket] | None:
        key = self._jira_tickets_cache_key(cloud_id, project_key)
        cached_data = await self.redis.get(key)
        if cached_data:
            return [Ticket.model_validate(item) for item in json.loads(self._decode_redis_value(cached_data))]
        return None

    async def invalidate_jira_tickets_cache(self, cloud_id: str, project_key: str) -> None:
        key = self._jira_tickets_cache_key(cloud_id, project_key)
        await self.redis.delete(key)

    async def save_jira_projects_cache(self, cloud_id: str, projects: list[Project], ttl: int = 300) -> None:
        key = self._jira_projects_cache_key(cloud_id)
        await self.redis.set(key, json.dumps([p.model_dump(mode='json') for p in projects]), ex=ttl)

    async def get_jira_projects_cache(self, cloud_id: str) -> list[Project] | None:
        key = self._jira_projects_cache_key(cloud_id)
        cached_data = await self.redis.get(key)
        if cached_data:
            return [Project.model_validate(item) for item in json.loads(self._decode_redis_value(cached_data))]
        return None
