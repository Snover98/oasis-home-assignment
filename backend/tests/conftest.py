import os
import sys
from pathlib import Path

# Ensure the backend directory is in sys.path so 'app' can be imported
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
import pytest_asyncio
from fakeredis.aioredis import FakeRedis
from datetime import datetime, timezone

from app.core.config import settings
from app.core.auth import close_user_store, configure_user_store
from app.core.security import get_password_hash, get_secret_hash, get_secret_lookup_hash
from app.core.user_store import RedisUserStore
from app.models.models import JiraCacheContext, StoredAPIKey, JiraConfig


@pytest_asyncio.fixture(autouse=True)
async def fake_user_store():
    store = RedisUserStore(FakeRedis(decode_responses=True))
    configure_user_store(store)
    # Ensure Redis is clean before each test
    await store.redis.flushdb() # Explicitly flush the database
    yield store
    await close_user_store()


@pytest_asyncio.fixture
async def create_user(fake_user_store):
    async def _create_user(
        username: str,
        email: str,
        password: str,
        api_keys: list[tuple[str, str]] | None = None,
        jira_config: JiraConfig | None = None, # Add jira_config parameter
        jira_cache_context: JiraCacheContext | None = None,
    ):
        user = await fake_user_store.create_user(
            username=username,
            email=email,
            password_hash=get_password_hash(password),
        )
        
        # Add additional API keys if provided
        if api_keys:
            for name, plain_key in api_keys:
                new_api_key = StoredAPIKey(
                    id=f"{username}-{name}".replace(" ", "-").lower(),
                    name=name,
                    key_hash=get_secret_hash(plain_key),
                    lookup_hash=get_secret_lookup_hash(plain_key),
                    created_at=datetime.now(timezone.utc),
                    username=username, # Pass username
                )
                user = await fake_user_store.add_api_key(username, new_api_key) # Use new add_api_key method
        
        # Set Jira config if provided
        if jira_config:
            user = await fake_user_store.set_jira_config(username, jira_config)
        if jira_cache_context:
            await fake_user_store.set_jira_cache_context(username, jira_cache_context)

        # The user returned by create_user, add_api_key, and set_jira_config is the composed UserInDB
        return user

    return _create_user

@pytest.fixture(autouse=True)
def override_blog_digest_interval(request, monkeypatch):
    """
    Automatically override the blog digest interval for tests related to this feature.
    """
    # Check if the test is in a file related to the blog digest feature
    relevant_files = ["test_automated_job.py", "test_jobs.py"]
    if any(rf in request.node.fspath.strpath for rf in relevant_files):
        # Use monkeypatch to safely override the setting for the duration of the test
        monkeypatch.setattr(settings, "AUTO_BLOG_DIGEST_INTERVAL_SECONDS", 10)


@pytest.fixture(autouse=True)
def fast_jira_retries(monkeypatch):
    """
    Overrides Jira retry settings for faster test failures.
    """
    monkeypatch.setattr(settings, "JIRA_RETRY_ATTEMPTS", 1) # Only 1 attempt
    monkeypatch.setattr(settings, "JIRA_RETRY_WAIT_MIN", 0.01) # Very short wait
    monkeypatch.setattr(settings, "JIRA_RETRY_WAIT_MAX", 0.01) # Very short wait


@pytest.fixture(autouse=True)
def test_secret_key(monkeypatch):
    monkeypatch.setattr(settings, "SECRET_KEY", "test-secret-key-with-at-least-32-bytes")
