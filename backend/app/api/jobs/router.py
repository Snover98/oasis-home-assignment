"""
API Router for automated and manual background jobs in the Oasis NHI Ticket System.
Currently handles the NHI Blog Digest job.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.models.models import User, BlogDigestRequest, BlogDigestResponse, TicketReference
from app.core.auth import get_current_user
from app.services.ai_summary import AISummaryService
from app.services.blog_scraper import BlogScraper
from app.services.jira import JiraService
...
router = APIRouter(tags=["jobs"])

async def perform_blog_digest(current_user: User, project_key: str) -> TicketReference:
    """
    Core logic for the blog digest job: scrapes the latest blog post,
    summarizes it with AI, and creates a Jira ticket.

    Args:
        current_user (User): The user performing the action.
        project_key (str): The Jira project where the ticket should be created.

    Returns:
        TicketReference: Details of the created Jira ticket.

    Raises:
        HTTPException: If Jira is not connected, scraping fails, or the ticket creation fails.
    """
    if not current_user.jira_config:
        raise HTTPException(status_code=400, detail="Jira configuration is missing for this user")

    scraper = BlogScraper()
    latest_post = await scraper.get_latest_post()
    if not latest_post:
        raise HTTPException(status_code=500, detail="Failed to fetch the latest blog post from Oasis website")

    ai_service = AISummaryService()
    summary = await ai_service.summarize_blog_post(latest_post.title, latest_post.content)

    jira_service = JiraService(current_user.jira_config)
    return await jira_service.create_ticket(
        project_key=project_key,
        summary=f"Blog Digest: {latest_post.title}",
        description=f"Link: {latest_post.url}\n\nSummary:\n{summary}"
    )

@router.post("/api/v1/jobs/blog-digest", response_model=BlogDigestResponse)
async def trigger_blog_digest(
    request: BlogDigestRequest,
    current_user: User = Depends(get_current_user)
) -> BlogDigestResponse:
    """
    Manual trigger for the NHI Blog Digest job.

    Args:
        request (BlogDigestRequest): Request body containing the target project key.
        current_user (User): The authenticated user (from dependency).

    Returns:
        BlogDigestResponse: Success status and the created ticket details.

    Raises:
        HTTPException: If the job execution fails.
    """
    try:
        result = await perform_blog_digest(current_user, request.project_key)
        return BlogDigestResponse(status="success", ticket=result)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
