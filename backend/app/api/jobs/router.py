from fastapi import APIRouter, Depends, HTTPException, status
from typing import Any

from app.models.models import User, BlogDigestRequest
from app.core.auth import get_current_user
from app.services.jira import JiraService
from app.services.blog_scraper import BlogScraper
from app.services.ai_summary import AISummaryService

router = APIRouter(tags=["jobs"])

async def perform_blog_digest(current_user: User, project_key: str) -> dict[str, Any]:
    """
    Logic to fetch blog posts, summarize them, and create a Jira ticket.
    Raises exceptions on failure.
    """
    if not current_user.jira_config:
        raise Exception("Jira configuration is missing for this user")

    scraper = BlogScraper()
    latest_post = await scraper.get_latest_post()
    if not latest_post:
        raise Exception("Failed to fetch the latest blog post from Oasis website")

    jira_service = JiraService(current_user.jira_config)
    ai_service = AISummaryService()
    summary = await ai_service.summarize_blog_post(latest_post["title"], latest_post["content"])

    return await jira_service.create_ticket(
        project_key=project_key,
        summary=f"Blog Digest: {latest_post['title']}",
        description=f"Link: {latest_post['url']}\n\nSummary:\n{summary}"
    )

@router.post("/api/v1/jobs/blog-digest")
async def trigger_blog_digest(
    request: BlogDigestRequest,
    current_user: User = Depends(get_current_user)
) -> dict[str, Any]:
    """
    Manually triggers the blog digest job for a specific project.
    """
    try:
        result = await perform_blog_digest(current_user, request.project_key)
        return {"status": "success", "ticket": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
