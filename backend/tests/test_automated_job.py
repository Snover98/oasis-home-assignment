import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from app.api.jobs.router import run_automated_blog_digest, job_state
from app.models.models import JiraConfig, BlogPost, TicketReference, UserInDB
from app.core.config import settings

@pytest.fixture
def mock_automated_job_deps():
    # Mock settings
    with patch("app.api.jobs.router.settings") as mock_settings, \
         patch("app.api.jobs.router.get_user_record", new_callable=AsyncMock) as mock_get_user_record, \
         patch("app.api.jobs.router.BlogScraper") as MockScraper, \
         patch("app.api.jobs.router.perform_blog_digest") as mock_perform, \
         patch("app.api.jobs.router.asyncio.sleep") as mock_sleep:
        
        mock_settings.AUTO_BLOG_DIGEST_ENABLED = True
        mock_settings.AUTO_BLOG_DIGEST_USER = "testuser"
        mock_settings.AUTO_BLOG_DIGEST_PROJECT_KEY = "NHI"
        mock_settings.AUTO_BLOG_DIGEST_INTERVAL_SECONDS = settings.AUTO_BLOG_DIGEST_INTERVAL_SECONDS
        
        # Mock user in DB
        mock_get_user_record.return_value = UserInDB(
            username="testuser",
            email="test@example.com",
            password_hash="hashed",
            jira_config=JiraConfig(access_token="fake", cloud_id="fake"),
            api_keys=[],
        )
        
        # Mock scraper
        scraper_instance = MockScraper.return_value
        scraper_instance.get_latest_post = AsyncMock(return_value=BlogPost(
            title="Automated Test Post",
            url="https://oasis.security/blog/automated",
            content="..."
        ))
        
        # Mock perform_blog_digest
        mock_perform.return_value = TicketReference(id="1", key="NHI-1", self="...")
        
        # Mock sleep to raise exception to break the loop after first iteration
        mock_sleep.side_effect = asyncio.CancelledError
        
        yield mock_settings, mock_get_user_record, scraper_instance, mock_perform, mock_sleep

@pytest.mark.asyncio
async def test_run_automated_blog_digest_new_post(mock_automated_job_deps):
    _, mock_get_user_record, scraper, mock_perform, _ = mock_automated_job_deps
    
    # Reset job state
    job_state.latest_processed_url = None
    
    # Run the job (it will run once and then be cancelled by the sleep mock)
    try:
        await run_automated_blog_digest()
    except asyncio.CancelledError:
        pass
    
    # Verify logic
    mock_get_user_record.assert_awaited_with("testuser")
    scraper.get_latest_post.assert_called_once()
    mock_perform.assert_called_once()
    assert job_state.latest_processed_url == "https://oasis.security/blog/automated"

@pytest.mark.asyncio
async def test_run_automated_blog_digest_no_new_post(mock_automated_job_deps):
    _, mock_get_user_record, scraper, mock_perform, _ = mock_automated_job_deps
    
    # Set job state to current post URL
    job_state.latest_processed_url = "https://oasis.security/blog/automated"
    
    # Run the job
    try:
        await run_automated_blog_digest()
    except asyncio.CancelledError:
        pass
    
    # Verify perform_blog_digest was NOT called again
    mock_perform.assert_not_called()
