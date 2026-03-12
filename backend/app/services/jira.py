import httpx
from app.models.models import JiraConfig, Project, Ticket
from typing import Any

class JiraService:
    """
    Service for interacting with Atlassian Jira REST API via OAuth 2.0 (3LO).
    """

    def __init__(self, config: JiraConfig) -> None:
        """
        Initializes the Jira service with OAuth credentials.
        :param config: The Jira configuration containing access token and cloud ID.
        """
        self.access_token = config.access_token
        self.cloud_id = config.cloud_id
        # The base URL for 3LO Jira requests
        self.base_api_url = f"https://api.atlassian.com/ex/jira/{self.cloud_id}"
        self.site_url = config.site_url or ""
        
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """
        Centralized request helper with error logging.
        """
        async with httpx.AsyncClient() as client:
            url = f"{self.base_api_url}{path}"
            try:
                response = await client.request(method, url, headers=self.headers, **kwargs)
                
                if response.status_code == 410:
                    print(f"CRITICAL: Jira API returned 410 Gone for {url}. This often means the site is deactivated or scopes need re-authorization.")
                    print(f"Response Body: {response.text}")
                
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                print(f"Jira API Error: {response.status_code} - {response.text}")
                raise e
            except Exception as e:
                print(f"Connection Error: {str(e)}")
                raise e

    async def get_projects(self) -> list[Project]:
        """
        Fetches all projects from the connected Jira workspace.
        :return: A list of projects.
        """
        data = await self._request("GET", "/rest/api/3/project")
        return [
            Project(id=p["id"], key=p["key"], name=p["name"])
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
        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": {
                    "version": 1,
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description}]
                        }
                    ]
                },
                "issuetype": {"name": "Task"}
            }
        }
        return await self._request("POST", "/rest/api/3/issue", json=payload)

    @staticmethod
    def issue_priority(priority: dict[str, str] | None) -> str:
        if not priority:
            return "None"
        return priority.get("name", "None")
    
    async def get_recent_tickets(self, project_key: str, limit: int = 10) -> list[Ticket]:
        """
        Fetches the most recent tickets for a specific project.
        :param project_key: The key of the Jira project.
        :param limit: The maximum number of tickets to retrieve.
        :return: A list of tickets.
        """
        # Using POST for search to avoid encoding issues and provide more stability
        payload = {
            "jql": f'project = "{project_key}" ORDER BY created DESC',
            "maxResults": limit,
            "fields": ["summary", "created", "status", "priority", "issuetype"]
        }
        data = await self._request("POST", "/rest/api/3/search/jql", json=payload)
        issues = data.get("issues", [])
        
        return [
            Ticket(
                id=issue["id"],
                key=issue["key"],
                self=f"{self.site_url}/browse/{issue['key']}" if self.site_url else f"https://atlassian.net/browse/{issue['key']}",
                summary=issue["fields"]["summary"],
                status=issue["fields"]["status"]["name"],
                priority=self.issue_priority(issue["fields"].get("priority", {})),
                issuetype=issue["fields"]["issuetype"]["name"],
                created=issue["fields"]["created"]
            )
            for issue in issues
        ]
