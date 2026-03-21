import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings

@pytest.mark.asyncio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_login_fail():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/token", data={"username": "wrong", "password": "wrong"})
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_login_success(create_user):
    await create_user("testuser", "test@example.com", "password")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/token", data={"username": "testuser", "password": "password"})
        me_response = await ac.get("/api/v1/users/me")
    assert response.status_code == 204
    assert settings.ACCESS_COOKIE_NAME in response.headers.get_list("set-cookie")[0]
    assert settings.REFRESH_COOKIE_NAME in "\n".join(response.headers.get_list("set-cookie"))
    assert settings.CSRF_COOKIE_NAME in "\n".join(response.headers.get_list("set-cookie"))
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "testuser"

@pytest.mark.asyncio
async def test_register_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/auth/register", 
            json={"username": "newuser", "email": "new@example.com", "password": "newpassword"}
        )
        me_response = await ac.get("/api/v1/users/me")
    assert response.status_code == 204
    assert settings.ACCESS_COOKIE_NAME in "\n".join(response.headers.get_list("set-cookie"))
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "newuser"

@pytest.mark.asyncio
async def test_refresh_and_logout_flow(create_user):
    await create_user("testuser", "test@example.com", "password")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login_response = await ac.post("/token", data={"username": "testuser", "password": "password"})
        assert login_response.status_code == 204

        refresh_response = await ac.post("/api/v1/auth/refresh")
        assert refresh_response.status_code == 204
        assert settings.ACCESS_COOKIE_NAME in "\n".join(refresh_response.headers.get_list("set-cookie"))

        csrf_token = ac.cookies.get(settings.CSRF_COOKIE_NAME)
        logout_response = await ac.post("/api/v1/auth/logout", headers={settings.CSRF_HEADER_NAME: csrf_token})
        assert logout_response.status_code == 204

        me_response = await ac.get("/api/v1/users/me")
        assert me_response.status_code == 401

@pytest.mark.asyncio
async def test_register_duplicate_username(create_user):
    await create_user("testuser", "test@example.com", "password")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/auth/register", 
            json={"username": "testuser", "email": "other@example.com", "password": "password"}
        )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]
