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
from app.core.security import get_password_hash, get_secret_hash
from app.core.user_store import RedisUserStore
from app.models.models import StoredAPIKey


@pytest_asyncio.fixture(autouse=True)
async def fake_user_store():
    store = RedisUserStore(FakeRedis(decode_responses=True))
    configure_user_store(store)
    yield store
    await close_user_store()


@pytest_asyncio.fixture
async def create_user(fake_user_store):
    async def _create_user(
        username: str,
        email: str,
        password: str,
        api_keys: list[tuple[str, str]] | None = None,
    ):
        user = await fake_user_store.create_user(
            username=username,
            email=email,
            password_hash=get_password_hash(password),
        )
        user.api_keys = []
        if api_keys:
            for name, plain_key in api_keys:
                user.api_keys.append(
                    StoredAPIKey(
                        id=f"{username}-{name}".replace(" ", "-").lower(),
                        name=name,
                        key_hash=get_secret_hash(plain_key),
                        created_at=datetime.now(timezone.utc),
                    )
                )
        await fake_user_store.save_user(user)
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
