import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.auth import get_user_store
from app.core.config import settings

@pytest.mark.asyncio
async def test_api_keys_flow(create_user):
    # Create user without any initial API keys
    await create_user(
        "testuser",
        "test@example.com",
        "password",
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Login to establish cookies
        login_response = await ac.post("/token", data={"username": "testuser", "password": "password"})
        assert login_response.status_code == 204
        csrf_token = ac.cookies.get(settings.CSRF_COOKIE_NAME)
        headers = {settings.CSRF_HEADER_NAME: csrf_token}

        # 2. Get initial API keys - should be empty
        list_response = await ac.get("/api/v1/api-keys")
        assert list_response.status_code == 200
        initial_keys = list_response.json()
        assert len(initial_keys) == 0 # Changed from 1 to 0
        # Removed assertions about initial_keys[0]
        # assert initial_keys[0]["name"] == "Default Key"
        # assert "key" not in initial_keys[0]

        # 3. Create a new API key
        create_response = await ac.post("/api/v1/api-keys", json={"name": "Test Key"}, headers=headers)
        assert create_response.status_code == 200
        new_key = create_response.json()
        assert new_key["name"] == "Test Key"
        assert "key" in new_key
        key_id = new_key["id"]

        # 4. Verify it was added
        list_response_2 = await ac.get("/api/v1/api-keys")
        assert len(list_response_2.json()) == 1 # Changed from 2 to 1 (only the newly created key)
        assert all("key" not in api_key for api_key in list_response_2.json())

        # 5. Revoke the key
        delete_response = await ac.delete(f"/api/v1/api-keys/{key_id}", headers=headers)
        assert delete_response.status_code == 204

        # 6. Verify it was removed - should be empty list
        list_response_3 = await ac.get("/api/v1/api-keys")
        assert len(list_response_3.json()) == 0 # Changed from 1 to 0

        # 7. Try to revoke a non-existent key
        delete_fail_response = await ac.delete("/api/v1/api-keys/fake-id", headers=headers)
        assert delete_fail_response.status_code == 404

@pytest.mark.asyncio
async def test_api_key_write_requires_csrf_for_cookie_auth(create_user):
    await create_user("testuser", "test@example.com", "password")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login_response = await ac.post("/token", data={"username": "testuser", "password": "password"})
        assert login_response.status_code == 204

        create_response = await ac.post("/api/v1/api-keys", json={"name": "Missing CSRF"})
        assert create_response.status_code == 403
        assert create_response.json()["detail"] == "CSRF validation failed"


@pytest.mark.asyncio
async def test_api_key_lookup_uses_indexed_lookup_not_scan(create_user, monkeypatch):
    await create_user(
        "testuser",
        "test@example.com",
        "password",
        api_keys=[("Indexed Key", "oasis_test_key_1")],
    )
    store = get_user_store()

    async def fail_scan_iter(*args, **kwargs):  # pragma: no cover
        raise AssertionError("scan_iter should not be used for API key lookup")
        yield

    monkeypatch.setattr(store.redis, "scan_iter", fail_scan_iter)

    user = await store.find_user_by_api_key("oasis_test_key_1")
    assert user is not None
    assert user.username == "testuser"
