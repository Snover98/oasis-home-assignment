"""
Jira Service module for the Oasis NHI Ticket System.
This module provides a high-level interface for interacting with the Atlassian Jira Cloud API
using OAuth 2.0 (3LO) and the pydantic-client library.
"""

import tenacity
import httpx # For httpx.NetworkError (specific exception for network issues)
import logging # For logging retry attempts
from fastapi import HTTPException # For re-raising as HTTPException

from pydantic_client import get, post
from pydantic_client.async_client import HttpxWebClient
from app.models.models import (
    IssueCreateRequest, IssueDescription, IssueFields, IssueType, JiraConfig, JiraIssuePriority, 
    ParagraphContent, Project, ProjectInfo, SearchParams, TextContent, Ticket, 
    JiraProjectResponse, CreatedIssueResponse, JiraSearchResultsResponse, TicketReference
)
from app.core.config import settings
from app.core.user_store import RedisUserStore
from app.core.auth import get_user_store

logger = logging.getLogger(__name__)

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
        self.config: JiraConfig = config # Store config for cache key
        self.site_url = config.site_url or settings.ATLASSIAN_DEFAULT_SITE_URL
        self.user_store: RedisUserStore = get_user_store() # Get the user store instance
 
        self.api = JiraAPIClient(
            base_url=f"{settings.ATLASSIAN_API_BASE_URL}/ex/jira/{config.cloud_id}",
            headers={
                "Authorization": f"Bearer {config.access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            })

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

    @tenacity.retry(
        wait=tenacity.wait_exponential(multiplier=1, min=settings.JIRA_RETRY_WAIT_MIN, max=settings.JIRA_RETRY_WAIT_MAX),
        stop=tenacity.stop_after_attempt(settings.JIRA_RETRY_ATTEMPTS),
        reraise=True,
        before_sleep=tenacity.before_sleep_log(logger, logging.INFO),
        retry=tenacity.retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException))
    )
    async def get_projects(self) -> list[Project]:
        """
        Fetches all projects from the connected Jira workspace and maps them to internal models.

        Returns:
            list[Project]: A list of simplified Project models.
        """
        projects = await self.api.get_projects()
        return [Project(id=p.id, key=p.key, name=p.name) for p in projects]

    @tenacity.retry(
        wait=tenacity.wait_exponential(multiplier=1, min=settings.JIRA_RETRY_WAIT_MIN, max=settings.JIRA_RETRY_WAIT_MAX),
        stop=tenacity.stop_after_attempt(settings.JIRA_RETRY_ATTEMPTS),
        reraise=True,
        before_sleep=tenacity.before_sleep_log(logger, logging.INFO),
        retry=tenacity.retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException))
    )
    async def create_ticket(self, project_key: str, summary: str, description: str) -> TicketReference:
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
        
        # Invalidate cache for recent tickets of this project
        cloud_id = self.config.cloud_id
        if cloud_id: # Only invalidate if cloud_id is present
            await self.user_store.invalidate_jira_tickets_cache(cloud_id, project_key)
            logger.info(f"Invalidated Jira ticket cache for project {project_key}.")
        
        return TicketReference(id=response.id, key=response.key, self=response.self)
    
    @tenacity.retry(
        wait=tenacity.wait_exponential(multiplier=1, min=settings.JIRA_RETRY_WAIT_MIN, max=settings.JIRA_RETRY_WAIT_MAX), # Exponential backoff
        stop=tenacity.stop_after_attempt(settings.JIRA_RETRY_ATTEMPTS), # Try 3 times
        reraise=True, # Re-raise the exception after retries
        before_sleep=tenacity.before_sleep_log(logger, logging.INFO),
        retry=tenacity.retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException)) # Retry on network errors or timeouts
    )
    async def _get_recent_tickets_from_jira(self, project_key: str, limit: int) -> list[Ticket]:
        """Internal helper to fetch recent tickets from Jira with retry logic."""
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

    async def get_recent_tickets(self, project_key: str, limit: int = 10) -> list[Ticket]:
        """
        Fetches the most recent tickets for a specific project, with Redis caching and Jira retry.
        Always attempts to fetch from Jira first, falling back to cache only on Jira failure.
        """
        cloud_id = self.config.cloud_id
        if not cloud_id: 
            raise HTTPException(status_code=500, detail="Jira Cloud ID missing for caching operations.")

        try:
            # Always try to fetch from Jira first
            tickets = await self._get_recent_tickets_from_jira(project_key, limit)
            await self.user_store.save_jira_tickets_cache(cloud_id, project_key, tickets) # Cache on success
            logger.info(f"Fetched and cached Jira tickets for {project_key}.")
            return tickets
        except tenacity.RetryError as e:
            # Jira API failed after retries, now try the cache
            logger.warning(f"Jira API _get_recent_tickets_from_jira failed after multiple retries for project {project_key}. Attempting to retrieve from cache. Error: {e}")
            cached_tickets = await self.user_store.get_jira_tickets_cache(cloud_id, project_key)
            if cached_tickets:
                logger.info(f"Returning cached Jira tickets for {project_key} due to Jira failure.")
                return cached_tickets
            else:
                logger.error(f"Jira API failed and no cached tickets available for project {project_key}.")
                raise HTTPException(status_code=503, detail="Failed to connect to Jira API after multiple retries. No cached tickets available.")
        except HTTPException as e:
            # Catch other HTTPExceptions from JiraService (e.g., config error from pydantic-client)
            logger.error(f"Jira API _get_recent_tickets_from_jira failed for project {project_key}: {e.detail}. Attempting to retrieve from cache.")
            cached_tickets = await self.user_store.get_jira_tickets_cache(cloud_id, project_key)
            if cached_tickets:
                logger.info(f"Returning cached Jira tickets for {project_key} due to Jira failure.")
                return cached_tickets
            else:
                logger.error(f"Jira API failed and no cached tickets available for project {project_key}.")
                raise HTTPException(status_code=e.status_code, detail=f"Jira API call failed: {e.detail}. No cached tickets available.")
        except Exception as e:
            # Catch any other unexpected exceptions
            logger.error(f"An unexpected error occurred while fetching Jira tickets for project {project_key}: {e}. Attempting to retrieve from cache.")
            cached_tickets = await self.user_store.get_jira_tickets_cache(cloud_id, project_key)
            if cached_tickets:
                logger.info(f"Returning cached Jira tickets for {project_key} due to unexpected error.")
                return cached_tickets
            else:
                logger.error(f"An unexpected error occurred and no cached tickets available for project {project_key}.")
                raise HTTPException(status_code=500, detail="An unexpected error occurred while fetching Jira tickets. No cached tickets available.")
