import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from app.main import app
from app.models.models import JiraConfig, TicketReference
from app.core.auth import get_user_store

@pytest.fixture
def mock_jira_service():
    with patch("app.api.endpoints.jira.JiraService") as MockService:
        service_instance = MockService.return_value
        service_instance.create_ticket = AsyncMock(return_value=TicketReference(
            id="10001",
            key="NHI-123",
            self="https://atlassian.net/browse/NHI-123"
        ))
        yield service_instance

@pytest.mark.asyncio
async def test_report_finding_with_api_key(mock_jira_service, create_user):
    user = await create_user(
        "testuser",
        "test@example.com",
        "password",
        api_keys=[("Default Key", "oasis_test_key_1")],
    )
    user_store = get_user_store()
    jira_config = JiraConfig(
        access_token="fake_token",
        cloud_id="fake_cloud_id"
    )
    # Use set_jira_config to update the Jira config
    await user_store.set_jira_config(user.username, jira_config)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        finding_data = {
            "project_key": "NHI",
            "title": "Stale Service Account",
            "description": "The account svc-deploy has not been used in 90 days."
        }
        # Use valid API key
        headers = {"X-API-Key": "oasis_test_key_1"}
        response = await ac.post("/api/v1/findings", json=finding_data, headers=headers)
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["ticket"]["key"] == "NHI-123"
    
    # Verify JiraService was called with correct data
    mock_jira_service.create_ticket.assert_called_once_with(
        project_key="NHI",
        summary="[Finding] Stale Service Account",
        description="The account svc-deploy has not been used in 90 days."
    )

@pytest.mark.asyncio
async def test_report_finding_invalid_api_key():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        finding_data = {
            "project_key": "NHI",
            "title": "Stale Service Account",
            "description": "..."
        }
        # Use invalid API key
        headers = {"X-API-Key": "invalid_key"}
        response = await ac.post("/api/v1/findings", json=finding_data, headers=headers)
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API Key"

@pytest.mark.asyncio
async def test_report_finding_missing_api_key():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        finding_data = {
            "project_key": "NHI",
            "title": "...",
            "description": "..."
        }
        # No headers
        response = await ac.post("/api/v1/findings", json=finding_data)
    
    assert response.status_code == 401
    assert "No valid authentication provided" in response.json()["detail"]

@pytest.mark.asyncio
async def test_report_finding_no_jira_connected(create_user):
    await create_user(
        "testuser2",
        "test2@example.com",
        "notpass",
        api_keys=[("Default Key", "oasis_test_key_2")],
    )
    user_store = get_user_store()
    # To simulate no Jira connected, explicitly set JiraConfig to None
    await user_store.set_jira_config("testuser2", None)
    # We should re-fetch the user to get the updated state
    user = await user_store.get_user("testuser2")
    assert user is not None
    assert user.jira_config is None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        finding_data = {
            "project_key": "NHI",
            "title": "...",
            "description": "..."
        }
        headers = {"X-API-Key": "oasis_test_key_2"}
        response = await ac.post("/api/v1/findings", json=finding_data, headers=headers)
    
    assert response.status_code == 400
    assert response.json()["detail"] == "Jira not connected"
