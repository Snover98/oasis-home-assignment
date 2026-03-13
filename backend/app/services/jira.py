"""
Jira Service module for the Oasis NHI Ticket System.
This module provides a high-level interface for interacting with the Atlassian Jira Cloud API
using OAuth 2.0 (3LO) and the pydantic-client library.
"""

from pydantic_client import get, post
from pydantic_client.async_client import HttpxWebClient
from app.models.models import (
    IssueCreateRequest, IssueDescription, IssueFields, IssueType, JiraConfig, JiraIssuePriority, 
    ParagraphContent, Project, ProjectInfo, SearchParams, TextContent, Ticket, 
    JiraProjectResponse, CreatedIssueResponse, JiraSearchResultsResponse
)
from typing import Any


class JiraAPIClient(HttpxWebClient):
    """
    Declarative REST client for Jira Cloud API using pydantic-client.
    """
    @get("/rest/api/3/project")
    async def get_projects(self) -> list[JiraProjectResponse]: 
        """Fetches the list of accessible Jira projects."""
        ...

    @post("/rest/api/3/issue")
    async def create_ticket(self, json: IssueCreateRequest) -> CreatedIssueResponse: 
        """Creates a new Jira issue."""
        ...

    @post("/rest/api/3/search/jql")
    async def search_tickets(self, params: SearchParams) -> JiraSearchResultsResponse: 
        """Performs a JQL search for Jira issues."""
        ...

class JiraService:
    """
    Business logic service for interacting with Atlassian Jira Cloud.
    Handles credential management and data mapping between Jira API and internal models.
    """

    def __init__(self, config: JiraConfig) -> None:
        """
        Initializes the Jira service with user-specific OAuth credentials.

        Args:
            config (JiraConfig): The user's Jira configuration including access token and cloud ID.
        """
        self.access_token = config.access_token
        self.cloud_id = config.cloud_id
        # The base URL for 3LO Jira requests includes the cloud_id
        self.base_api_url = f"https://api.atlassian.com/ex/jira/{self.cloud_id}"
        self.site_url = config.site_url or "https://atlassian.net"
 
        self.api = JiraAPIClient(
            base_url=self.base_api_url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            })

    async def get_projects(self) -> list[Project]:
        """
        Fetches all projects from the connected Jira workspace and maps them to internal models.

        Returns:
            list[Project]: A list of simplified Project models.
        """
        projects = await self.api.get_projects()
        return [Project(id=p.id, key=p.key, name=p.name) for p in projects]

    async def create_ticket(self, project_key: str, summary: str, description: str) -> dict[str, str]:
        """
        Creates a new issue (ticket) in the specified Jira project.

        Args:
            project_key (str): The key of the Jira project (e.g., 'PROJ').
            summary (str): The title of the ticket.
            description (str): The detailed content of the ticket.

        Returns:
            dict[str, str]: A dictionary containing the created ticket's ID and key.
        """
        request = IssueCreateRequest(
            fields=IssueFields(
                project=ProjectInfo(key=project_key),
                summary=summary,
                description=IssueDescription(
                    content=[ParagraphContent(
                        content=[TextContent(text=description)]
                    )]
                ),
                issuetype=IssueType(name="Task")
            )
        )
        response = await self.api.create_ticket(json=request)
        return {"id": response.id, "key": response.key, "self": response.self}

    @staticmethod
    def issue_priority(priority: JiraIssuePriority | None) -> str:
        """
        Safe helper to extract priority name from various Jira response formats.

        Args:
            priority (Any | None): The priority object from Jira API.

        Returns:
            str: The priority name or 'None'.
        """
        if priority is None or priority.name is None:
            return "None"
        return priority.name
    
    async def get_recent_tickets(self, project_key: str, limit: int = 10) -> list[Ticket]:
        """
        Fetches the most recent tickets for a specific project.

        Args:
            project_key (str): The key of the Jira project.
            limit (int): The maximum number of tickets to retrieve.

        Returns:
            list[Ticket]: A list of Ticket models enriched with status and priority.
        """
        data = await self.api.search_tickets(params=SearchParams(
            jql=f'project = "{project_key}" ORDER BY created DESC',
            maxResults=limit,
            fields=["summary", "created", "status", "priority", "issuetype"]
        ))
        
        return [
            Ticket(
                id=issue.id,
                key=issue.key,
                self=f"{self.site_url}/browse/{issue.key}",
                summary=issue.fields.summary,
                status=issue.fields.status.name,
                priority=self.issue_priority(issue.fields.priority),
                issuetype=issue.fields.issuetype.name,
                created=issue.fields.created
            )
            for issue in data.issues
        ]
