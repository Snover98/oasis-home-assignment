"""
Redis-backed persistence for users, Jira configuration, and API keys.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from redis.asyncio import Redis

from app.core.security import get_secret_hash, verify_secret
from app.models.models import JiraConfig, StoredAPIKey, UserInDB


class RedisUserStore:
    def __init__(self, redis: Redis):
        self.redis = redis

    @classmethod
    def from_url(cls, redis_url: str) -> "RedisUserStore":
        return cls(Redis.from_url(redis_url, decode_responses=True))

    @staticmethod
    def _user_key(username: str) -> str:
        return f"user:{username}"

    async def close(self) -> None:
        await self.redis.aclose()

    async def get_user(self, username: str) -> UserInDB | None:
        raw_user = await self.redis.get(self._user_key(username))
        if raw_user is None:
            return None
        return UserInDB.model_validate_json(raw_user)

    async def save_user(self, user: UserInDB) -> None:
        await self.redis.set(self._user_key(user.username), user.model_dump_json())

    async def user_exists(self, username: str) -> bool:
        return bool(await self.redis.exists(self._user_key(username)))

    async def set_jira_config(self, username: str, jira_config: JiraConfig) -> UserInDB | None:
        user = await self.get_user(username)
        if user is None:
            return None
        user.jira_config = jira_config
        await self.save_user(user)
        return user

    async def add_api_key(self, username: str, api_key: StoredAPIKey) -> UserInDB | None:
        user = await self.get_user(username)
        if user is None:
            return None
        user.api_keys.append(api_key)
        await self.save_user(user)
        return user

    async def revoke_api_key(self, username: str, key_id: str) -> bool:
        user = await self.get_user(username)
        if user is None:
            return False

        original_length = len(user.api_keys)
        user.api_keys = [api_key for api_key in user.api_keys if api_key.id != key_id]
        if len(user.api_keys) == original_length:
            return False

        await self.save_user(user)
        return True

    async def find_user_by_api_key(self, plain_api_key: str) -> UserInDB | None:
        async for key in self.redis.scan_iter(match="user:*"):
            raw_user = await self.redis.get(key)
            if raw_user is None:
                continue

            user = UserInDB.model_validate_json(raw_user)
            for api_key in user.api_keys:
                if verify_secret(plain_api_key, api_key.key_hash):
                    return user

        return None

    async def create_user(self, username: str, email: str, password_hash: str) -> UserInDB:
        new_user = UserInDB(
            username=username,
            email=email,
            password_hash=password_hash,
            jira_config=None,
            api_keys=[
                StoredAPIKey(
                    id=str(uuid.uuid4()),
                    name="Default Key",
                    key_hash=get_secret_hash(f"oasis_key_{uuid.uuid4().hex}"),
                    created_at=datetime.now(timezone.utc),
                )
            ],
        )
        await self.save_user(new_user)
        return new_user
