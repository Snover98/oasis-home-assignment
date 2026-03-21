import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from app.main import app
from app.core.config import settings
from app.models.models import AtlassianResourceResponse, AtlassianTokenResponse, JiraConfig

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
    assert me_response.json()["jira_config"] is None

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
        refresh_token = ac.cookies.get(settings.REFRESH_COOKIE_NAME)

        refresh_response = await ac.post("/api/v1/auth/refresh")
        assert refresh_response.status_code == 204
        assert settings.ACCESS_COOKIE_NAME in "\n".join(refresh_response.headers.get_list("set-cookie"))

        csrf_token = ac.cookies.get(settings.CSRF_COOKIE_NAME)
        logout_response = await ac.post("/api/v1/auth/logout", headers={settings.CSRF_HEADER_NAME: csrf_token})
        assert logout_response.status_code == 204

        ac.cookies.set(settings.REFRESH_COOKIE_NAME, refresh_token)
        refresh_after_logout = await ac.post("/api/v1/auth/refresh")
        assert refresh_after_logout.status_code == 401

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


@pytest.mark.asyncio
async def test_users_me_does_not_expose_jira_tokens(create_user):
    await create_user(
        "testuser",
        "test@example.com",
        "password",
        jira_config=JiraConfig(access_token="secret-access", refresh_token="secret-refresh"),
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/token", data={"username": "testuser", "password": "password"})
        response = await ac.get("/api/v1/users/me")

    assert response.status_code == 200
    body = response.json()
    assert "access_token" not in str(body)
    assert "refresh_token" not in str(body)


@pytest.mark.asyncio
async def test_jira_oauth_state_flow(create_user):
    await create_user("testuser", "test@example.com", "password")

    with (
        patch("app.api.auth.router.AtlassianAuthClient") as mock_auth_client_cls,
        patch("app.api.auth.router.AtlassianAPIClient") as mock_api_client_cls,
    ):
        mock_auth_client_cls.return_value.exchange_token = AsyncMock(
            return_value=AtlassianTokenResponse(
                access_token="jira-access-token",
                refresh_token="jira-refresh-token",
                expires_in=3600,
                scope="read:jira-work",
                token_type="Bearer",
            )
        )
        mock_api_client_cls.return_value.get_accessible_resources = AsyncMock(
            return_value=[
                AtlassianResourceResponse(
                    id="cloud-123",
                    url="https://example.atlassian.net",
                    name="Example Jira",
                    scopes=["read:jira-work"],
                )
            ]
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            login_response = await ac.post("/token", data={"username": "testuser", "password": "password"})
            assert login_response.status_code == 204

            auth_url_response = await ac.get("/api/v1/jira/auth/url")
            assert auth_url_response.status_code == 200
            auth_url = auth_url_response.json()["url"]
            state = auth_url.split("state=")[1].split("&")[0]
            assert state != "testuser"
            assert ac.cookies.get(settings.JIRA_OAUTH_STATE_COOKIE_NAME) == state

            csrf_token = ac.cookies.get(settings.CSRF_COOKIE_NAME)

            invalid_state_response = await ac.post(
                "/api/v1/jira/auth/callback",
                params={"code": "oauth-code", "state": "wrong-state"},
                headers={settings.CSRF_HEADER_NAME: csrf_token},
            )
            assert invalid_state_response.status_code == 400

            valid_state_response = await ac.post(
                "/api/v1/jira/auth/callback",
                params={"code": "oauth-code", "state": state},
                headers={settings.CSRF_HEADER_NAME: csrf_token},
            )
            assert valid_state_response.status_code == 200
            assert valid_state_response.json()["status"] == "success"

            reused_state_response = await ac.post(
                "/api/v1/jira/auth/callback",
                params={"code": "oauth-code", "state": state},
                headers={settings.CSRF_HEADER_NAME: csrf_token},
            )
            assert reused_state_response.status_code == 400
