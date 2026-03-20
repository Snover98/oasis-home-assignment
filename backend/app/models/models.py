"""
Data models for the Oasis NHI Ticket System.
Defines Pydantic models for internal data structures, API requests, and external API responses.
"""

from pydantic import BaseModel, Field
from datetime import datetime

class APIKey(BaseModel):
    """Represents an API key for programmatic access."""
    id: str
    name: str
    created_at: datetime

class APIKeyWithSecret(APIKey):
    """Represents a newly created API key including the one-time secret value."""
    key: str

class StoredAPIKey(APIKey):
    """Internal representation of an API key stored by hash only."""
    key_hash: str

class APIKeyCreate(BaseModel):
    """Request schema for creating a new API key."""
    name: str

class JiraConfig(BaseModel):
    """Configuration for a user's Jira connection."""
    access_token: str
    refresh_token: str | None = None
    cloud_id: str | None = None
    site_url: str | None = None

class Project(BaseModel):
    """Represents a Jira project."""
    id: str
    key: str
    name: str

class TicketCreate(BaseModel):
    """Schema for creating a new Jira ticket manually."""
    project_key: str
    summary: str
    description: str

class Ticket(BaseModel):
    """Represents a Jira issue/ticket with relevant fields for the UI."""
    id: str
    key: str
    self: str
    summary: str
    status: str
    priority: str
    issuetype: str
    created: datetime

class FindingCreate(BaseModel):
    """Schema for reporting a new NHI finding."""
    project_key: str
    title: str
    description: str

class BlogDigestRequest(BaseModel):
    """Request schema for triggering a blog digest job."""
    project_key: str

class AuthUrlResponse(BaseModel):
    """Response containing the OAuth authorization URL."""
    url: str

class AuthCallbackResponse(BaseModel):
    """Response confirming successful OAuth callback."""
    status: str
    site_name: str

class TicketReference(BaseModel):
    """Reference to a created Jira ticket."""
    id: str
    key: str
    self: str

class FindingResponse(BaseModel):
    """Response when a finding is successfully reported."""
    status: str
    ticket: TicketReference

class BlogDigestResponse(BaseModel):
    """Response when a blog digest job succeeds."""
    status: str
    ticket: TicketReference

class HealthResponse(BaseModel):
    """Health check response."""
    status: str

class BlogPost(BaseModel):
    """Data model representing a scraped blog post."""
    title: str
    url: str
    content: str

class User(BaseModel):
    """Represents a user in the system (public profile)."""
    username: str
    email: str
    jira_config: JiraConfig | None = None
    api_keys: list[APIKey] = Field(default_factory=list)

class UserCreate(BaseModel):
    """Schema for creating a new user."""
    username: str
    email: str
    password: str

class UserInDB(User):
    """Internal representation of a user stored in the database."""
    password_hash: str
    api_keys: list[StoredAPIKey] = Field(default_factory=list)

class Token(BaseModel):
    """JWT Token response schema."""
    access_token: str
    token_type: str

"""
Jira API Response Models (External)
"""

class JiraProjectResponse(BaseModel):
    """Raw response from Jira's project list API."""
    id: str
    key: str
    name: str
    self: str

class CreatedIssueResponse(BaseModel):
    """Raw response from Jira's issue creation API."""
    id: str
    key: str
    self: str

class JiraIssueStatus(BaseModel):
    """Status field in a Jira issue."""
    name: str

class JiraIssuePriority(BaseModel):
    """Priority field in a Jira issue."""
    name: str | None = None

class JiraIssueType(BaseModel):
    """Issue type field in a Jira issue."""
    name: str

class JiraIssueFields(BaseModel):
    """Relevant fields within a Jira issue object."""
    summary: str
    created: datetime
    status: JiraIssueStatus
    priority: JiraIssuePriority | None = None
    issuetype: JiraIssueType

class JiraIssue(BaseModel):
    """Raw issue object from Jira's search/get APIs."""
    id: str
    key: str
    self: str
    fields: JiraIssueFields

class JiraSearchResultsResponse(BaseModel):
    """Raw response from Jira's search API."""
    # total: int
    issues: list[JiraIssue]

"""
Atlassian OAuth Response Models (External)
"""

class AtlassianResourceResponse(BaseModel):
    """Represents an accessible Atlassian resource (e.g., a Jira site)."""
    id: str
    url: str
    name: str
    scopes: list[str]
    avatarUrl: str | None = None

class AtlassianTokenResponse(BaseModel):
    """Raw response from Atlassian's OAuth token endpoint."""
    access_token: str
    refresh_token: str | None = None
    expires_in: int
    scope: str
    token_type: str

class AtlassianTokenExchangeRequest(BaseModel):
    """Request schema for exchanging an auth code for Atlassian tokens."""
    grant_type: str = "authorization_code"
    client_id: str
    client_secret: str
    code: str
    redirect_uri: str

"""
Jira Request Schemas (Internal to Client)
"""

class SearchParams(BaseModel):
    """Parameters for Jira JQL search."""
    jql: str
    maxResults: int
    fields: list[str]

class TextContent(BaseModel):
    """Represents text content in Jira's Document Format (ADF)."""
    type: str = "text"
    text: str

class ParagraphContent(BaseModel):
    """Represents a paragraph in Jira's Document Format (ADF)."""
    type: str = "paragraph"
    content: list[TextContent]

class IssueDescription(BaseModel):
    """Represents an issue description in Jira's Document Format (ADF)."""
    version: int = 1
    type: str = "doc"
    content: list[ParagraphContent]

class IssueType(BaseModel):
    """Wrapper for issue type name in creation requests."""
    name: str

class ProjectInfo(BaseModel):
    """Wrapper for project key in creation requests."""
    key: str

class IssueFields(BaseModel):
    """Field container for creating a new Jira issue."""
    project: ProjectInfo
    summary: str
    description: IssueDescription
    issuetype: IssueType

class IssueCreateRequest(BaseModel):
    """Root container for creating a new Jira issue."""
    fields: IssueFields
