"""
API Router for Jira-related endpoints in the Oasis NHI Ticket System.
Provides endpoints for project retrieval, ticket creation, and search.
"""

from fastapi import APIRouter, Depends, HTTPException
import httpx # Import httpx

from app.models.models import User, Project, Ticket, TicketCreate, FindingCreate, TicketReference, FindingResponse
from app.core.auth import get_current_user, get_any_user, get_user_store, require_csrf_for_cookie_auth
from app.services.jira import JiraService

router = APIRouter(tags=["jira"])


async def _get_jira_service_for_reads(current_user: User) -> JiraService:
    cache_context = await get_user_store().get_jira_cache_context(current_user.username)
    if current_user.jira_config:
        return JiraService(
            current_user.jira_config,
            cache_cloud_id=cache_context.cloud_id if cache_context else None,
            cache_site_url=cache_context.site_url if cache_context else None,
        )

    if cache_context is None:
        raise HTTPException(status_code=400, detail="Jira not connected")

    return JiraService(
        None,
        cache_cloud_id=cache_context.cloud_id,
        cache_site_url=cache_context.site_url,
    )


async def _get_jira_service_for_writes(current_user: User) -> JiraService:
    if not current_user.jira_config:
        raise HTTPException(status_code=400, detail="Jira not connected")

    cache_context = await get_user_store().get_jira_cache_context(current_user.username)
    if cache_context is None:
        raise HTTPException(status_code=400, detail="Jira not connected")

    return JiraService(
        current_user.jira_config,
        cache_cloud_id=cache_context.cloud_id,
        cache_site_url=cache_context.site_url,
    )

@router.get("/api/v1/jira/projects", response_model=list[Project])
async def get_jira_projects(current_user: User = Depends(get_current_user)) -> list[Project]:
    """
    Fetches all projects from the user's connected Jira workspace.

    Args:
        current_user (User): The currently authenticated user (from dependency).

    Returns:
        list[Project]: A list of Jira projects.

    Raises:
        HTTPException: If Jira is not connected for the user.
    """
    jira_service = await _get_jira_service_for_reads(current_user)
    try:
        return await jira_service.get_projects()
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@router.post("/api/v1/jira/tickets", response_model=TicketReference)
async def create_jira_ticket(
    ticket_data: TicketCreate, 
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf_for_cookie_auth),
) -> TicketReference:
    """
    Creates a new ticket in the user's Jira workspace.

    Args:
        ticket_data (TicketCreate): The data for the new ticket.
        current_user (User): The currently authenticated user (from dependency).

    Returns:
        TicketReference: Details of the created ticket (ID and key).

    Raises:
        HTTPException: If Jira is not connected for the user.
    """
    jira_service = await _get_jira_service_for_writes(current_user)
    try:
        return await jira_service.create_ticket(
            project_key=ticket_data.project_key,
            summary=ticket_data.summary,
            description=ticket_data.description
        )
    except httpx.HTTPStatusError as e: # Catch HTTPStatusError specifically
        raise HTTPException(status_code=e.response.status_code, detail=f"Jira API error: {e.response.text}")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@router.get("/api/v1/jira/tickets/recent", response_model=list[Ticket])
async def get_recent_jira_tickets(
    project_key: str, 
    current_user: User = Depends(get_current_user)
) -> list[Ticket]:
    """
    Fetches the 10 most recent tickets for a specific Jira project.

    Args:
        project_key (str): The key of the Jira project to search in.
        current_user (User): The currently authenticated user (from dependency).

    Returns:
        list[Ticket]: A list of the most recent tickets.

    Raises:
        HTTPException: If Jira is not connected for the user.
    """
    jira_service = await _get_jira_service_for_reads(current_user)
    try:
        return await jira_service.get_recent_tickets(project_key=project_key)
    except HTTPException as e:
        raise e # Re-raise exceptions from JiraService
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@router.post("/api/v1/findings", response_model=FindingResponse)
async def report_finding(
    finding: FindingCreate, 
    current_user: User = Depends(get_any_user)
) -> FindingResponse:
    """
    Reports an NHI finding by creating a corresponding ticket in Jira.

    Args:
        finding (FindingCreate): The finding details and target project.
        current_user (User): The currently authenticated user (from dependency).

    Returns:
        FindingResponse: Success status and the created ticket details.

    Raises:
        HTTPException: If Jira is not connected or the ticket creation fails.
    """
    jira_service = await _get_jira_service_for_writes(current_user)
    
    try:
        result = await jira_service.create_ticket(
            project_key=finding.project_key,
            summary=f"[Finding] {finding.title}",
            description=finding.description
        )
        return FindingResponse(status="success", ticket=result)
    except HTTPException as e: # Catch and re-raise exceptions from JiraService
        raise e
    except Exception as e: # Catch any other unexpected exceptions
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
