from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
import uvicorn
import httpx
from typing import Any
from datetime import timedelta

from app.models.models import User, Token, Project, Ticket, TicketCreate, FindingCreate, JiraConfig, BlogDigestRequest
from app.core.auth import (
    authenticate_user, 
    create_access_token, 
    get_current_user, 
    ACCESS_TOKEN_EXPIRE_MINUTES,
    USERS_DB
)
from app.services.jira import JiraService
from app.services.blog_scraper import BlogScraper
from app.services.ai_summary import AISummaryService

app = FastAPI(
    title="Oasis NHI Ticket System API",
    description="Backend API for managing NHI findings and Jira integration.",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React frontend dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> dict[str, str]:
    """
    Login endpoint to obtain a JWT access token.
    :param form_data: OAuth2 password request form containing username and password.
    :return: A dictionary containing the access token and token type.
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

from app.core.config import settings
import urllib.parse

@app.get("/api/v1/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)) -> User:
    """
    Returns the currently authenticated user's profile.
    :param current_user: The currently authenticated user.
    :return: The user profile.
    """
    return current_user

@app.get("/api/v1/jira/auth/url")
async def get_jira_auth_url(current_user: User = Depends(get_current_user)) -> dict[str, str]:
    """
    Generates the Atlassian OAuth 2.0 authorization URL.
    """
    params = {
        "audience": "api.atlassian.com",
        "client_id": settings.JIRA_CLIENT_ID,
        "scope": settings.JIRA_SCOPES,
        "redirect_uri": settings.JIRA_REDIRECT_URI,
        "state": current_user.username,
        "response_type": "code",
        "prompt": "consent"
    }
    # Use quote_via=urllib.parse.quote to ensure spaces are %20
    url = f"{settings.ATLASSIAN_AUTH_URL}?{urllib.parse.urlencode(params, quote_via=urllib.parse.quote)}"
    return {"url": url}

@app.post("/api/v1/jira/auth/callback")
async def jira_auth_callback(
    code: str, 
    current_user: User = Depends(get_current_user)
) -> dict[str, str]:
    """
    Handles the redirect from Atlassian, exchanges the code for tokens,
    and fetches the accessible Jira resources (sites).
    """
    async with httpx.AsyncClient() as client:
        # 1. Exchange code for access token
        token_response = await client.post(
            settings.ATLASSIAN_TOKEN_URL,
            json={
                "grant_type": "authorization_code",
                "client_id": settings.JIRA_CLIENT_ID,
                "client_secret": settings.JIRA_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.JIRA_REDIRECT_URI
            }
        )
        if token_response.is_error:
            raise HTTPException(status_code=400, detail=f"Failed to exchange token: {token_response.text}")
        
        token_data = token_response.json()
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")

        # 2. Fetch accessible resources (cloud_id)
        resources_response = await client.get(
            "https://api.atlassian.com/oauth/token/accessible-resources",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        resources = resources_response.json()
        if not resources:
            raise HTTPException(status_code=400, detail="No accessible Jira resources found")
        
        # Look specifically for resources that have Jira scopes
        jira_resource = next(
            (r for r in resources if any("jira" in s for s in r.get("scopes", []))), 
            resources[0]
        )
        
        # 3. Store in USERS_DB
        jira_config = JiraConfig(
            access_token=access_token,
            refresh_token=refresh_token,
            cloud_id=jira_resource["id"],
            site_url=jira_resource["url"]
        )
        
        if current_user.username in USERS_DB:
            USERS_DB[current_user.username]["jira_config"] = jira_config.model_dump()
            return {"status": "success", "site_name": jira_resource["name"]}
            
    raise HTTPException(status_code=404, detail="User not found")

@app.get("/api/v1/jira/projects", response_model=list[Project])
async def get_jira_projects(current_user: User = Depends(get_current_user)) -> list[Project]:
    """
    Fetches all projects from the user's Jira workspace.
    :param current_user: The currently authenticated user.
    :return: A list of Jira projects.
    """
    if not current_user.jira_config:
        raise HTTPException(status_code=400, detail="Jira not connected")
    
    jira_service = JiraService(current_user.jira_config)
    return await jira_service.get_projects()

@app.post("/api/v1/jira/tickets")
async def create_jira_ticket(
    ticket_data: TicketCreate, 
    current_user: User = Depends(get_current_user)
) -> dict[str, str]:
    """
    Creates a new ticket in the user's Jira workspace.
    :param ticket_data: The data for the new ticket.
    :param current_user: The currently authenticated user.
    :return: A dictionary containing the created ticket's ID and key.
    """
    if not current_user.jira_config:
        raise HTTPException(status_code=400, detail="Jira not connected")
    
    jira_service = JiraService(current_user.jira_config)
    return await jira_service.create_ticket(
        project_key=ticket_data.project_key,
        summary=ticket_data.summary,
        description=ticket_data.description
    )

@app.get("/api/v1/jira/tickets/recent", response_model=list[Ticket])
async def get_recent_jira_tickets(
    project_key: str, 
    current_user: User = Depends(get_current_user)
) -> list[Ticket]:
    """
    Fetches the 10 most recent tickets for the selected project.
    :param project_key: The key of the Jira project.
    :param current_user: The currently authenticated user.
    :return: A list of the most recent tickets.
    """
    if not current_user.jira_config:
        raise HTTPException(status_code=400, detail="Jira not connected")
    
    jira_service = JiraService(current_user.jira_config)
    return await jira_service.get_recent_tickets(project_key=project_key)

@app.post("/api/v1/findings")
async def report_finding(
    finding: FindingCreate, 
    current_user: User = Depends(get_current_user)
) -> dict[str, Any]:
    """
    Endpoint to report findings using the current user's Jira context.
    :param finding: The finding data.
    :param current_user: The currently authenticated user.
    :return: A dictionary indicating success and the created ticket details.
    """
    if not current_user.jira_config:
        raise HTTPException(status_code=400, detail="Jira not connected")
    
    jira_service = JiraService(current_user.jira_config)
    
    try:
        result = await jira_service.create_ticket(
            project_key=finding.project_key,
            summary=f"[Finding] {finding.title}",
            description=finding.description
        )
        return {"status": "success", "ticket": result}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/jobs/blog-digest")
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

@app.get("/health")
async def health_check() -> dict[str, str]:
    """
    Simple health check endpoint.
    :return: A dictionary indicating the status of the API.
    """
    return {"status": "ok"}

def main() -> None:
    """
    Main entry point for running the application.
    """
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()
