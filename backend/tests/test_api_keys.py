import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_api_keys_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Login to get token
        login_response = await ac.post("/token", data={"username": "testuser", "password": "password"})
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Get initial API keys
        list_response = await ac.get("/api/v1/api-keys", headers=headers)
        assert list_response.status_code == 200
        initial_keys = list_response.json()
        assert len(initial_keys) == 1
        assert initial_keys[0]["name"] == "Default Key"
        assert "key" not in initial_keys[0]

        # 3. Create a new API key
        create_response = await ac.post("/api/v1/api-keys", json={"name": "Test Key"}, headers=headers)
        assert create_response.status_code == 200
        new_key = create_response.json()
        assert new_key["name"] == "Test Key"
        assert "key" in new_key
        key_id = new_key["id"]

        # 4. Verify it was added
        list_response_2 = await ac.get("/api/v1/api-keys", headers=headers)
        assert len(list_response_2.json()) == 2
        assert all("key" not in api_key for api_key in list_response_2.json())

        # 5. Revoke the key
        delete_response = await ac.delete(f"/api/v1/api-keys/{key_id}", headers=headers)
        assert delete_response.status_code == 204

        # 6. Verify it was removed
        list_response_3 = await ac.get("/api/v1/api-keys", headers=headers)
        assert len(list_response_3.json()) == 1

        # 7. Try to revoke a non-existent key
        delete_fail_response = await ac.delete("/api/v1/api-keys/fake-id", headers=headers)
        assert delete_fail_response.status_code == 404
