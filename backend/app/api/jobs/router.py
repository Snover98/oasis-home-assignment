"""
API Router for automated and manual background jobs in the Oasis NHI Ticket System.
Currently handles the NHI Blog Digest job.
"""

import asyncio
from fastapi import APIRouter, Depends, HTTPException

from app.models.models import User, BlogDigestRequest, BlogDigestResponse, TicketReference, BlogPost
from app.core.auth import get_current_user, USERS_DB, require_csrf_for_cookie_auth
from app.services.ai_summary import AISummaryService
from app.services.blog_scraper import BlogScraper
from app.services.jira import JiraService
from app.core.config import settings

router = APIRouter(tags=["jobs"])

class JobStateStore:
    """
    In-memory storage for job-related state that would typically be in a database.
    """
    def __init__(self) -> None:
        self.latest_processed_url: str | None = None

# Global instance of the state store
job_state = JobStateStore()


async def perform_blog_digest(current_user: User, project_key: str, blog_post: BlogPost | None = None) -> TicketReference:
    """
    Core logic for the blog digest job: scrapes the latest blog post (if not provided),
    summarizes it with AI, and creates a Jira ticket.

    Args:
        current_user (User): The user performing the action.
        project_key (str): The Jira project where the ticket should be created.
        blog_post (BlogPost | None): Optional already fetched blog post.

    Returns:
        TicketReference: Details of the created Jira ticket.

    Raises:
        HTTPException: If Jira is not connected, scraping fails, or the ticket creation fails.
    """
    if not current_user.jira_config:
        raise HTTPException(status_code=400, detail="Jira configuration is missing for this user")

    latest_post = blog_post
    if not latest_post:
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


async def run_automated_blog_digest() -> None:
    """
    Background task loop that periodically runs the blog digest job
    for the configured system user and project.
    """
    if not settings.AUTO_BLOG_DIGEST_ENABLED:
        return

    print(f"Starting automated blog digest job for user {settings.AUTO_BLOG_DIGEST_USER}")
    
    while True:
        try:
            # 1. Fetch user from USERS_DB
            user_in_db = USERS_DB.get(settings.AUTO_BLOG_DIGEST_USER)
            if not user_in_db or not user_in_db.jira_config:
                await asyncio.sleep(settings.AUTO_BLOG_DIGEST_INTERVAL_SECONDS)
                continue

            current_user = User(
                username=user_in_db.username,
                email=user_in_db.email,
                jira_config=user_in_db.jira_config,
                api_key=user_in_db.api_key
            )

            # 2. Check for latest post
            scraper = BlogScraper()
            latest_post = await scraper.get_latest_post()
            
            if latest_post and latest_post.url != job_state.latest_processed_url:
                print(f"New blog post found: {latest_post.title}. Generating digest ticket...")
                
                # 3. Create Jira ticket
                await perform_blog_digest(current_user, settings.AUTO_BLOG_DIGEST_PROJECT_KEY, blog_post=latest_post)
                
                # 4. Update state store
                job_state.latest_processed_url = latest_post.url
                print(f"Successfully created blog digest ticket for {latest_post.title}")
            
        except Exception as e:
            print(f"Error in automated blog digest background job: {e}")
        
        await asyncio.sleep(settings.AUTO_BLOG_DIGEST_INTERVAL_SECONDS)

@router.post("/api/v1/jobs/blog-digest", response_model=BlogDigestResponse)
async def trigger_blog_digest(
    request: BlogDigestRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf_for_cookie_auth),
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
