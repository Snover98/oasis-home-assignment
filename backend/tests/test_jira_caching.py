import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, ANY
from app.main import app
from app.models.models import JiraConfig, Ticket, TicketReference, UserInDB, CreatedIssueResponse, JiraSearchResultsResponse
from app.core.user_store import RedisUserStore
from datetime import datetime, timezone
import httpx
import tenacity
from tenacity import RetryError
from app.core.config import settings
from app.services.jira import JiraAPIClient
import time

# Mocking the get_user_store dependency for JiraService tests
@pytest.fixture
def mock_user_store():
    with patch("app.services.jira.get_user_store") as mock_get_user_store:
        mock_store_instance = AsyncMock(spec=RedisUserStore)
        mock_get_user_store.return_value = mock_store_instance
        yield mock_store_instance

@pytest.fixture
def mock_jira_service_deps(mock_user_store):
    mock_api_client = AsyncMock(spec=JiraAPIClient) # Mock the instance directly
    with patch("app.services.jira.JiraAPIClient", return_value=mock_api_client):
        yield mock_user_store, mock_api_client # Yield the directly mocked instance

@pytest.mark.asyncio
async def test_get_recent_jira_tickets_cache_hit(create_user, mock_jira_service_deps):
    mock_user_store, mock_api_client = mock_jira_service_deps
    
    # Setup user with Jira config
    user = await create_user(
        "testuser",
        "test@example.com",
        "password",
        jira_config=JiraConfig(access_token="fake_token", cloud_id="fake_cloud_id")
    )

    # Mock cached tickets
    cached_tickets = [
        Ticket(id="1", key="NHI-1", self="url", summary="Cached Ticket 1", status="Open", priority="High", issuetype="Task", created=datetime.now(timezone.utc)),
        Ticket(id="2", key="NHI-2", self="url", summary="Cached Ticket 2", status="Closed", priority="Medium", issuetype="Bug", created=datetime.now(timezone.utc))
    ]
    mock_user_store.get_jira_tickets_cache.return_value = cached_tickets

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Login to get cookies
        await ac.post("/token", data={"username": "testuser", "password": "password"})
        
        # Mock Jira API to fail, so cache fallback is triggered
        mock_api_client.search_tickets.side_effect = httpx.NetworkError("Simulated Jira network error")

        # Call endpoint
        response = await ac.get("/api/v1/jira/tickets/recent?project_key=NHI")
    
    assert response.status_code == 200
    assert response.json() == [ticket.model_dump(mode='json') for ticket in cached_tickets]
    
    # Verify Jira API was called (and failed due to side_effect, triggering retries)
    assert mock_api_client.search_tickets.call_count == 3 # Due to retries
    # Verify cache was checked and then returned
    mock_user_store.get_jira_tickets_cache.assert_called_once()
    mock_user_store.save_jira_tickets_cache.assert_not_called()

@pytest.mark.asyncio
async def test_get_recent_jira_tickets_cache_miss_jira_success(create_user, mock_jira_service_deps):
    mock_user_store, mock_api_client = mock_jira_service_deps
    
    user = await create_user(
        "testuser",
        "test@example.com",
        "password",
        jira_config=JiraConfig(access_token="fake_token", cloud_id="fake_cloud_id")
    )

    # Mock no cached tickets
    mock_user_store.get_jira_tickets_cache.return_value = None

    # Mock Jira API success
    jira_tickets_response = {
        "issues": [
            {"id": "3", "key": "NHI-3", "self": "jira_url_3", "fields": {"summary": "Jira Ticket 3", "status": {"name": "Open"}, "priority": {"name": "High"}, "issuetype": {"name": "Task"}, "created": datetime.now(timezone.utc).isoformat()}},
        ]
    }
    mock_api_client.search_tickets.return_value = JiraSearchResultsResponse.model_validate(jira_tickets_response)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/token", data={"username": "testuser", "password": "password"})
        response = await ac.get("/api/v1/jira/tickets/recent?project_key=NHI")
    
    assert response.status_code == 200
    assert response.json()[0]["key"] == "NHI-3"
    
    # Verify Jira API was called
    mock_api_client.search_tickets.assert_called_once()
    # Verify cache was NOT checked in this scenario (Jira success, no prior cache check)
    mock_user_store.get_jira_tickets_cache.assert_not_called() 
    mock_user_store.save_jira_tickets_cache.assert_called_once()

@pytest.mark.asyncio
async def test_get_recent_jira_tickets_jira_failure_cache_fallback(create_user, mock_jira_service_deps):
    mock_user_store, mock_api_client = mock_jira_service_deps
    
    user = await create_user(
        "testuser",
        "test@example.com",
        "password",
        jira_config=JiraConfig(access_token="fake_token", cloud_id="fake_cloud_id")
    )

    # Mock Jira API failure (e.g., network error)
    mock_api_client.search_tickets.side_effect = httpx.NetworkError("Jira is down")

    # Mock cached tickets for fallback
    cached_tickets = [
        Ticket(id="4", key="NHI-4", self="url", summary="Fallback Ticket 4", status="Open", priority="High", issuetype="Task", created=datetime.now(timezone.utc)),
    ]
    mock_user_store.get_jira_tickets_cache.return_value = cached_tickets

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/token", data={"username": "testuser", "password": "password"})
        response = await ac.get("/api/v1/jira/tickets/recent?project_key=NHI")
    
    assert response.status_code == 200
    assert response.json() == [ticket.model_dump(mode='json') for ticket in cached_tickets]
    
    # Verify Jira API was called (and failed)
    assert mock_api_client.search_tickets.call_count == 3 # Due to retries
    # Verify cache was checked and then returned
    mock_user_store.get_jira_tickets_cache.assert_called_once()
    mock_user_store.save_jira_tickets_cache.assert_not_called()

@pytest.mark.asyncio
async def test_get_recent_jira_tickets_jira_failure_no_cache_fallback(create_user, mock_user_store):
    # This test does NOT use mock_jira_service_deps directly as we are patching _get_recent_tickets_from_jira
    user = await create_user(
        "testuser",
        "test@example.com",
        "password",
        jira_config=JiraConfig(access_token="fake_token", cloud_id="fake_cloud_id")
    )

    # Mock no cached tickets
    mock_user_store.get_jira_tickets_cache.return_value = None

    # Patch the internal Jira fetch method to directly raise RetryError
    with patch("app.services.jira.JiraService._get_recent_tickets_from_jira") as mock_internal_jira_fetch:
        mock_internal_jira_fetch.side_effect = RetryError("Simulated Jira failure after retries.") 

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            await ac.post("/token", data={"username": "testuser", "password": "password"})
            response = await ac.get("/api/v1/jira/tickets/recent?project_key=NHI")
        
        assert response.status_code == 503
        assert "Failed to connect to Jira API after multiple retries. No cached tickets available." in response.json()["detail"]
        
        # In this scenario, we assert on the patched internal method, not mock_api_client.search_tickets
        mock_internal_jira_fetch.assert_called_once()
        mock_user_store.get_jira_tickets_cache.assert_called_once()
        mock_user_store.save_jira_tickets_cache.assert_not_called()

@pytest.mark.asyncio
async def test_create_jira_ticket_invalidates_cache(create_user, mock_jira_service_deps):
    mock_user_store, mock_api_client = mock_jira_service_deps
    
    user = await create_user(
        "testuser",
        "test@example.com",
        "password",
        jira_config=JiraConfig(access_token="fake_token", cloud_id="fake_cloud_id")
    )

    # Mock Jira API ticket creation success
    mock_api_client.create_ticket.return_value = CreatedIssueResponse(
        id="10005", key="TEST-5", self="http://jira.url/TEST-5"
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/token", data={"username": "testuser", "password": "password"})
        csrf_token = ac.cookies.get(settings.CSRF_COOKIE_NAME)
        headers = {settings.CSRF_HEADER_NAME: csrf_token}

        ticket_data = {"project_key": "TEST", "summary": "New Ticket", "description": "Description"}
        response = await ac.post("/api/v1/jira/tickets", json=ticket_data, headers=headers)
    
    assert response.status_code == 200
    assert response.json()["key"] == "TEST-5"
    
    # Verify cache invalidation was called
    mock_user_store.invalidate_jira_tickets_cache.assert_called_once_with("fake_cloud_id", "TEST")

@pytest.mark.asyncio
async def test_get_recent_jira_tickets_cache_per_project_key(create_user, mock_jira_service_deps):
    mock_user_store, mock_api_client = mock_jira_service_deps
    
    await create_user(
        "testuser",
        "test@example.com",
        "password",
        jira_config=JiraConfig(access_token="fake_token", cloud_id="fake_cloud_id")
    )

    # --- First call for project "PROJA" ---
    mock_user_store.get_jira_tickets_cache.return_value = None
    jira_tickets_response_A = {
        "issues": [{"id": "1", "key": "PROJA-1", "self": "some_url", "fields": {"summary": "Ticket A", "status": {"name": "Open"}, "priority": {"name": "High"}, "issuetype": {"name": "Task"}, "created": datetime.now(timezone.utc).isoformat()}}]}
    mock_api_client.search_tickets.return_value = JiraSearchResultsResponse.model_validate(jira_tickets_response_A)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/token", data={"username": "testuser", "password": "password"})
        response_a = await ac.get("/api/v1/jira/tickets/recent?project_key=PROJA")
    
    assert response_a.status_code == 200
    assert response_a.json()[0]["key"] == "PROJA-1"
    mock_user_store.get_jira_tickets_cache.assert_not_called() # Jira API succeeded, no cache check needed
    mock_user_store.save_jira_tickets_cache.assert_called_once_with("fake_cloud_id", "PROJA", ANY)
    mock_api_client.search_tickets.assert_called_once()

    # --- Second call for project "PROJB" (Jira success, populate cache for PROJB) ---
    mock_user_store.reset_mock()
    mock_api_client.reset_mock()
    mock_user_store.get_jira_tickets_cache.return_value = None # No cache for PROJB yet
    jira_tickets_response_B = {
        "issues": [{"id": "2", "key": "PROJB-1", "self": "some_url", "fields": {"summary": "Ticket B", "status": {"name": "Open"}, "priority": {"name": "High"}, "issuetype": {"name": "Task"}, "created": datetime.now(timezone.utc).isoformat()}}]
    }
    mock_api_client.search_tickets.return_value = JiraSearchResultsResponse.model_validate(jira_tickets_response_B)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/token", data={"username": "testuser", "password": "password"})
        response_b = await ac.get("/api/v1/jira/tickets/recent?project_key=PROJB")

    assert response_b.status_code == 200
    assert response_b.json()[0]["key"] == "PROJB-1"
    mock_user_store.get_jira_tickets_cache.assert_not_called() # Jira API succeeded, no cache check needed
    mock_user_store.save_jira_tickets_cache.assert_called_once_with("fake_cloud_id", "PROJB", ANY)
    mock_api_client.search_tickets.assert_called_once()

    # --- Third call for project "PROJA" with Jira failure (should hit cache for PROJA) ---
    mock_user_store.reset_mock()
    mock_api_client.reset_mock()
    
    # Mock Jira API to fail, so cache fallback is triggered
    mock_api_client.search_tickets.side_effect = httpx.NetworkError("Simulated Jira network error")
    cached_tickets_A = [Ticket(id="1", key="PROJA-1", self="url", summary="Ticket A", status="Open", priority="High", issuetype="Task", created=datetime.now(timezone.utc))]
    mock_user_store.get_jira_tickets_cache.return_value = cached_tickets_A

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/token", data={"username": "testuser", "password": "password"})
        response_a2 = await ac.get("/api/v1/jira/tickets/recent?project_key=PROJA")

    assert response_a2.status_code == 200
    assert response_a2.json()[0]["key"] == "PROJA-1"
    mock_user_store.get_jira_tickets_cache.assert_called_once_with("fake_cloud_id", "PROJA") # Cache *should* be checked here
    mock_user_store.save_jira_tickets_cache.assert_not_called() # No save because it's a cache fallback
    assert mock_api_client.search_tickets.call_count == 3 # Due to retries

@pytest.mark.asyncio
async def test_jira_cache_ttl(create_user, mock_jira_service_deps, monkeypatch):
    mock_user_store, mock_api_client = mock_jira_service_deps
    
    # Temporarily set JIRA_CACHE_TTL for this test
    monkeypatch.setattr(settings, "JIRA_CACHE_TTL", 1) # Set to 1 second for faster testing
    await create_user(
        "testuser",
        "test@example.com",
        "password",
        jira_config=JiraConfig(access_token="fake_token", cloud_id="fake_cloud_id")
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/token", data={"username": "testuser", "password": "password"})

        # --- Initial call to populate cache ---
        mock_user_store.get_jira_tickets_cache.return_value = None
        jira_response = {"issues": [{"id": "1", "key": "TTL-1", "self": "some_url", "fields": {"summary": "Ticket TTL", "status": {"name": "Open"}, "priority": {"name": "High"}, "issuetype": {"name": "Task"}, "created": datetime.now(timezone.utc).isoformat()}}]}
        mock_api_client.search_tickets.return_value = JiraSearchResultsResponse.model_validate(jira_response)
        
        await ac.get("/api/v1/jira/tickets/recent?project_key=TTL")
        
        mock_user_store.get_jira_tickets_cache.assert_not_called() # Jira was successful, so cache was not checked
        mock_user_store.save_jira_tickets_cache.assert_called_once() # Cache was saved
        mock_api_client.search_tickets.assert_called_once() # Jira was called

        # --- Reset mocks and advance time ---
        mock_user_store.reset_mock()
        mock_api_client.reset_mock()
        
        # --- 2. Call again after TTL with Jira failure (should hit cache, find it empty, and try Jira again) ---
        # Cache should return None because it expired
        mock_user_store.get_jira_tickets_cache.return_value = None 

        # Patch the internal Jira fetch method to directly raise RetryError
        with patch("app.services.jira.JiraService._get_recent_tickets_from_jira") as mock_internal_jira_fetch:
            mock_internal_jira_fetch.side_effect = RetryError("Simulated Jira failure after retries after TTL.") 

            with patch("time.time", return_value=time.time() + settings.JIRA_CACHE_TTL + 1):
                response = await ac.get("/api/v1/jira/tickets/recent?project_key=TTL")

            assert response.status_code == 503 # Expected failure because Jira fails and cache is empty after TTL
            mock_user_store.get_jira_tickets_cache.assert_called_once() # Cache should be checked here
            mock_internal_jira_fetch.assert_called_once() # Internal Jira fetch was called
            mock_api_client.search_tickets.assert_not_called() # The lower level api client should not be called directly
            mock_user_store.save_jira_tickets_cache.assert_not_called() # No save because Jira failed

@pytest.mark.asyncio
async def test_create_jira_ticket_failure_does_not_invalidate_cache(create_user, mock_jira_service_deps):
    mock_user_store, mock_api_client = mock_jira_service_deps
    
    await create_user(
        "testuser",
        "test@example.com",
        "password",
        jira_config=JiraConfig(access_token="fake_token", cloud_id="fake_cloud_id")
    )

    # Mock Jira API ticket creation failure
    mock_api_client.create_ticket.side_effect = httpx.HTTPStatusError("Failed to create ticket", request=AsyncMock(), response=AsyncMock(status_code=400))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/token", data={"username": "testuser", "password": "password"})
        csrf_token = ac.cookies.get(settings.CSRF_COOKIE_NAME)
        headers = {settings.CSRF_HEADER_NAME: csrf_token}

        ticket_data = {"project_key": "TEST", "summary": "New Ticket", "description": "Description"}
        response = await ac.post("/api/v1/jira/tickets", json=ticket_data, headers=headers)
    
    assert response.status_code == 400
    
    # Verify cache invalidation was NOT called
    mock_user_store.invalidate_jira_tickets_cache.assert_not_called()
