"""
Redis-backed persistence for users, Jira configuration, and API keys.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from redis.asyncio import Redis

import json
from app.core.security import get_secret_hash, verify_secret
from app.models.models import JiraConfig, Project, StoredAPIKey, UserInDB, UserCore, Ticket


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
    def _user_api_keys_set_key(username: str) -> str:
        return f"user:{username}:api_keys_set"

    @staticmethod
    def _api_key_obj_key(key_id: str) -> str:
        return f"api_key:{key_id}"

    @staticmethod
    def _jira_tickets_cache_key(cloud_id: str, project_key: str) -> str:
        return f"jira:{cloud_id}:{project_key}:latest_tickets"

    @staticmethod
    def _jira_projects_cache_key(cloud_id: str) -> str:
        return f"jira:{cloud_id}:projects"

    async def close(self) -> None:
        await self.redis.aclose()

    async def get_user(self, username: str) -> UserInDB | None:
        user_core_raw = await self.redis.get(self._user_core_key(username))
        if user_core_raw is None:
            return None
        user_core = UserCore.model_validate_json(user_core_raw)

        jira_config: JiraConfig | None = None
        jira_config_raw = await self.redis.get(self._user_jira_config_key(username))
        if jira_config_raw:
            jira_config = JiraConfig.model_validate_json(jira_config_raw)

        api_keys: list[StoredAPIKey] = []
        api_key_ids = await self.redis.smembers(self._user_api_keys_set_key(username))
        for key_id in api_key_ids:
            api_key_raw = await self.redis.get(self._api_key_obj_key(key_id.decode()))
            if api_key_raw:
                api_keys.append(StoredAPIKey.model_validate_json(api_key_raw))
        
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

    async def add_api_key(self, username: str, api_key: StoredAPIKey) -> UserInDB | None:
        if not await self.user_exists(username):
            return None
        
        # Ensure API key is linked to the correct user
        api_key.username = username
        await self.redis.sadd(self._user_api_keys_set_key(username), api_key.id)
        await self.redis.set(self._api_key_obj_key(api_key.id), api_key.model_dump_json())
        return await self.get_user(username)

    async def revoke_api_key(self, username: str, key_id: str) -> bool:
        if not await self.user_exists(username):
            return False
        
        # Check if the key belongs to the user before deleting
        api_key_raw = await self.redis.get(self._api_key_obj_key(key_id))
        if not api_key_raw:
            return False
        stored_api_key = StoredAPIKey.model_validate_json(api_key_raw)
        if stored_api_key.username != username:
            return False # Key does not belong to this user

        await self.redis.srem(self._user_api_keys_set_key(username), key_id)
        await self.redis.delete(self._api_key_obj_key(key_id))
        return True

    async def find_user_by_api_key(self, plain_api_key: str) -> UserInDB | None:
        # This will scan all API keys, which can be inefficient for very large number of keys
        # Consider using HASH or a reverse index if performance is critical
        async for key_name in self.redis.scan_iter(match="api_key:*"):
            api_key_raw = await self.redis.get(key_name)
            if api_key_raw:
                stored_api_key = StoredAPIKey.model_validate_json(api_key_raw)
                if verify_secret(plain_api_key, stored_api_key.key_hash):
                    return await self.get_user(stored_api_key.username)
        return None

    async def save_jira_tickets_cache(self, cloud_id: str, project_key: str, tickets: list[Ticket], ttl: int = 300) -> None:
        key = self._jira_tickets_cache_key(cloud_id, project_key)
        await self.redis.set(key, json.dumps([t.model_dump(mode='json') for t in tickets]), ex=ttl) 
    
    async def get_jira_tickets_cache(self, cloud_id: str, project_key: str) -> list[Ticket] | None:
        key = self._jira_tickets_cache_key(cloud_id, project_key)
        cached_data = await self.redis.get(key)
        if cached_data:
            return [Ticket.model_validate(item) for item in json.loads(cached_data)]
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
            return [Project.model_validate(item) for item in json.loads(cached_data)]
        return None
