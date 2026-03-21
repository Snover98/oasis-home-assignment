import pytest
from unittest.mock import AsyncMock, patch
from app.api.jobs.router import perform_blog_digest
from app.core.auth import get_user_store
from app.models.models import BlogPost, JiraCacheContext, JiraConfig, TicketReference, User

@pytest.fixture
def mock_blog_services():
    with patch("app.api.jobs.router.BlogScraper") as MockScraper, \
         patch("app.api.jobs.router.AISummaryService") as MockAI, \
         patch("app.api.jobs.router.JiraService") as MockJira:
        
        scraper_instance = MockScraper.return_value
        scraper_instance.get_latest_post = AsyncMock(return_value=BlogPost(
            title="Latest Security Trends",
            url="https://oasis.security/blog/trends",
            content="Some interesting content."
        ))
        
        ai_instance = MockAI.return_value
        ai_instance.summarize_blog_post = AsyncMock(return_value="AI Summary of the post.")
        
        jira_instance = MockJira.return_value
        jira_instance.create_ticket = AsyncMock(return_value=TicketReference(
            id="10002",
            key="BLOG-1",
            self="https://atlassian.net/browse/BLOG-1"
        ))
        
        yield scraper_instance, ai_instance, jira_instance

@pytest.mark.asyncio
async def test_perform_blog_digest_success(mock_blog_services, create_user):
    scraper, ai, jira = mock_blog_services
    await create_user("testuser", "test@example.com", "password", jira_config=JiraConfig(access_token="fake"))
    await get_user_store().set_jira_cache_context("testuser", JiraCacheContext(cloud_id="fake"))
    
    current_user = User(
        username="testuser",
        email="test@example.com",
        jira_config=None,
        api_keys=[],
    )
    
    result = await perform_blog_digest(current_user, "NHI")
    
    assert result.key == "BLOG-1"
    scraper.get_latest_post.assert_called_once()
    ai.summarize_blog_post.assert_called_once_with("Latest Security Trends", "Some interesting content.")
    jira.create_ticket.assert_called_once_with(
        project_key="NHI",
        summary="Blog Digest: Latest Security Trends",
        description="Link: https://oasis.security/blog/trends\n\nSummary:\nAI Summary of the post."
    )

@pytest.mark.asyncio
async def test_perform_blog_digest_no_post(mock_blog_services, create_user):
    scraper, ai, jira = mock_blog_services
    scraper.get_latest_post = AsyncMock(return_value=None)
    await create_user("testuser", "test@example.com", "password", jira_config=JiraConfig(access_token="fake"))
    await get_user_store().set_jira_cache_context("testuser", JiraCacheContext(cloud_id="fake"))
    
    from fastapi import HTTPException
    
    current_user = User(
        username="testuser",
        email="test@example.com",
        jira_config=None,
        api_keys=[],
    )
    
    with pytest.raises(HTTPException) as excinfo:
        await perform_blog_digest(current_user, "NHI")
    
    assert excinfo.value.status_code == 500
    assert "Failed to fetch the latest blog post" in excinfo.value.detail
