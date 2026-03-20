import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.api.jobs.router import run_automated_blog_digest, job_state
from app.models.models import User, JiraConfig, BlogPost, TicketReference
from app.core.config import settings

@pytest.fixture
def mock_automated_job_deps():
    # Mock settings
    with patch("app.api.jobs.router.settings") as mock_settings, \
         patch("app.api.jobs.router.USERS_DB") as mock_db, \
         patch("app.api.jobs.router.BlogScraper") as MockScraper, \
         patch("app.api.jobs.router.perform_blog_digest") as mock_perform, \
         patch("app.api.jobs.router.asyncio.sleep") as mock_sleep:
        
        mock_settings.AUTO_BLOG_DIGEST_ENABLED = True
        mock_settings.AUTO_BLOG_DIGEST_USER = "testuser"
        mock_settings.AUTO_BLOG_DIGEST_PROJECT_KEY = "NHI"
        mock_settings.AUTO_BLOG_DIGEST_INTERVAL_SECONDS = 3600
        
        # Mock user in DB
        mock_user = MagicMock()
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.jira_config = JiraConfig(access_token="fake", cloud_id="fake")
        mock_user.api_key = "fake_key"
        mock_db.get.return_value = mock_user
        
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
        
        yield mock_settings, mock_db, scraper_instance, mock_perform, mock_sleep

@pytest.mark.asyncio
async def test_run_automated_blog_digest_new_post(mock_automated_job_deps):
    _, mock_db, scraper, mock_perform, _ = mock_automated_job_deps
    
    # Reset job state
    job_state.latest_processed_url = None
    
    # Run the job (it will run once and then be cancelled by the sleep mock)
    try:
        await run_automated_blog_digest()
    except asyncio.CancelledError:
        pass
    
    # Verify logic
    mock_db.get.assert_called_with("testuser")
    scraper.get_latest_post.assert_called_once()
    mock_perform.assert_called_once()
    assert job_state.latest_processed_url == "https://oasis.security/blog/automated"

@pytest.mark.asyncio
async def test_run_automated_blog_digest_no_new_post(mock_automated_job_deps):
    _, mock_db, scraper, mock_perform, _ = mock_automated_job_deps
    
    # Set job state to current post URL
    job_state.latest_processed_url = "https://oasis.security/blog/automated"
    
    # Run the job
    try:
        await run_automated_blog_digest()
    except asyncio.CancelledError:
        pass
    
    # Verify perform_blog_digest was NOT called again
    mock_perform.assert_not_called()
