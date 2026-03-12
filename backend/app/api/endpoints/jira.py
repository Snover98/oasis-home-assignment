from fastapi import APIRouter, Depends, HTTPException
from typing import Any

from app.models.models import User, Project, Ticket, TicketCreate, FindingCreate
from app.core.auth import get_current_user
from app.services.jira import JiraService

router = APIRouter(tags=["jira"])

@router.get("/api/v1/jira/projects", response_model=list[Project])
async def get_jira_projects(current_user: User = Depends(get_current_user)) -> list[Project]:
    """
    Fetches all projects from the user's Jira workspace.
    """
    if not current_user.jira_config:
        raise HTTPException(status_code=400, detail="Jira not connected")
    
    jira_service = JiraService(current_user.jira_config)
    return await jira_service.get_projects()

@router.post("/api/v1/jira/tickets")
async def create_jira_ticket(
    ticket_data: TicketCreate, 
    current_user: User = Depends(get_current_user)
) -> dict[str, str]:
    """
    Creates a new ticket in the user's Jira workspace.
    """
    if not current_user.jira_config:
        raise HTTPException(status_code=400, detail="Jira not connected")
    
    jira_service = JiraService(current_user.jira_config)
    return await jira_service.create_ticket(
        project_key=ticket_data.project_key,
        summary=ticket_data.summary,
        description=ticket_data.description
    )

@router.get("/api/v1/jira/tickets/recent", response_model=list[Ticket])
async def get_recent_jira_tickets(
    project_key: str, 
    current_user: User = Depends(get_current_user)
) -> list[Ticket]:
    """
    Fetches the 10 most recent tickets for the selected project.
    """
    if not current_user.jira_config:
        raise HTTPException(status_code=400, detail="Jira not connected")
    
    jira_service = JiraService(current_user.jira_config)
    return await jira_service.get_recent_tickets(project_key=project_key)

@router.post("/api/v1/findings")
async def report_finding(
    finding: FindingCreate, 
    current_user: User = Depends(get_current_user)
) -> dict[str, Any]:
    """
    Endpoint to report findings using the current user's Jira context.
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
