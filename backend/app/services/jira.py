from pydantic_client import get, post
from pydantic_client.async_client import HttpxWebClient
from app.models.models import (
    IssueCreateRequest, IssueDescription, IssueFields, IssueType, JiraConfig, ParagraphContent, Project, ProjectInfo, SearchParams, TextContent, Ticket, JiraProjectResponse, 
    CreatedIssueResponse, JiraSearchResultsResponse
)
from typing import Any


class JiraAPIClient(HttpxWebClient):
    @get("/rest/api/3/project")
    async def get_projects(self) -> list[JiraProjectResponse]: ...

    @post("/rest/api/3/issue")
    async def create_ticket(self, json: IssueCreateRequest) -> CreatedIssueResponse: ...

    @post("/rest/api/3/search/jql")
    async def search_tickets(self, params: SearchParams) -> JiraSearchResultsResponse: ...

class JiraService:
    """
    Service for interacting with Atlassian Jira REST API via OAuth 2.0 (3LO)
    using pydantic-client.
    """

    def __init__(self, config: JiraConfig) -> None:
        """
        Initializes the Jira service with OAuth credentials.
        :param config: The Jira configuration containing access token and cloud ID.
        """
        self.access_token = config.access_token
        self.cloud_id = config.cloud_id
        self.base_api_url = f"https://api.atlassian.com/ex/jira/{self.cloud_id}"
        self.site_url = config.site_url or ""
 
        self.api = JiraAPIClient(
            base_url=self.base_api_url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            })

    async def get_projects(self) -> list[Project]:
        """
        Fetches all projects from the connected Jira workspace.
        :return: A list of projects.
        """
        data = await self.api.get_projects()
        return [
            Project(id=p.id, key=p.key, name=p.name)
            for p in data
        ]

    async def create_ticket(self, project_key: str, summary: str, description: str) -> dict[str, str]:
        """
        Creates a new issue (ticket) in the specified Jira project.
        :param project_key: The key of the Jira project.
        :param summary: The summary (title) of the ticket.
        :param description: The description of the ticket.
        :return: A dictionary containing the created ticket's ID and key.
        """
        request = IssueCreateRequest(
            fields=IssueFields(
                project=ProjectInfo(key=project_key),
                summary=summary,
                description=IssueDescription(
                    content=[
                        ParagraphContent(
                            content=[TextContent(text=description)]
                        )
                    ]
                ),
                issuetype=IssueType(name="Task")
            )
        )
        response = await self.api.create_ticket(json=request)
        return {"id": response.id, "key": response.key, "self": response.self}

    @staticmethod
    def issue_priority(priority: Any | None) -> str:
        if not priority or not hasattr(priority, "name") or not priority.name:
            return "None"
        return priority.name
    
    async def get_recent_tickets(self, project_key: str, limit: int = 10) -> list[Ticket]:
        """
        Fetches the most recent tickets for a specific project.
        :param project_key: The key of the Jira project.
        :param limit: The maximum number of tickets to retrieve.
        :return: A list of tickets.
        """
        data = await self.api.search_tickets(params=SearchParams(
            jql=f'project = "{project_key}" ORDER BY created DESC',
            maxResults=limit,
            fields=["summary", "created", "status", "priority", "issuetype"]
        ))
        
        issues = data.issues

        return [
            Ticket(
                id=issue.id,
                key=issue.key,
                self=f"{self.site_url}/browse/{issue.key}" if self.site_url else f"https://atlassian.net/browse/{issue.key}",
                summary=issue.fields.summary,
                status=issue.fields.status.name,
                priority=self.issue_priority(issue.fields.priority),
                issuetype=issue.fields.issuetype.name,
                created=issue.fields.created
            )
            for issue in issues
        ]
