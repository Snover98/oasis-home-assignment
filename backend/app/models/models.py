from pydantic import BaseModel
from datetime import datetime

class JiraConfig(BaseModel):
    access_token: str
    refresh_token: str | None = None
    cloud_id: str | None = None
    site_url: str | None = None

class Project(BaseModel):
    id: str
    key: str
    name: str

class TicketCreate(BaseModel):
    project_key: str
    summary: str
    description: str

class Ticket(BaseModel):
    id: str
    key: str
    self: str
    summary: str
    status: str
    priority: str
    issuetype: str
    created: datetime

class FindingCreate(BaseModel):
    project_key: str
    title: str
    description: str

class BlogDigestRequest(BaseModel):
    project_key: str

class User(BaseModel):
    username: str
    email: str
    jira_config: JiraConfig | None = None

class UserInDB(User):
    password_hash: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None

# Jira API Response Models
class JiraProjectResponse(BaseModel):
    id: str
    key: str
    name: str
    self: str

class CreatedIssueResponse(BaseModel):
    id: str
    key: str
    self: str

class JiraIssueStatus(BaseModel):
    name: str

class JiraIssuePriority(BaseModel):
    name: str | None = None

class JiraIssueType(BaseModel):
    name: str

class JiraIssueFields(BaseModel):
    summary: str
    created: datetime
    status: JiraIssueStatus
    priority: JiraIssuePriority | None = None
    issuetype: JiraIssueType

class JiraIssue(BaseModel):
    id: str
    key: str
    self: str
    fields: JiraIssueFields

class JiraSearchResultsResponse(BaseModel):
    # total: int
    issues: list[JiraIssue]

# Atlassian OAuth Response Models
class AtlassianResourceResponse(BaseModel):
    id: str
    url: str
    name: str
    scopes: list[str]
    avatarUrl: str | None = None

class AtlassianTokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    expires_in: int
    scope: str
    token_type: str

class AtlassianTokenExchangeRequest(BaseModel):
    grant_type: str = "authorization_code"
    client_id: str
    client_secret: str
    code: str
    redirect_uri: str


class SearchParams(BaseModel):
    jql: str
    maxResults: int
    fields: list[str]

class TextContent(BaseModel):
    type: str = "text"
    text: str

class ParagraphContent(BaseModel):
    type: str = "paragraph"
    content: list[TextContent]

class IssueDescription(BaseModel):
    version: int = 1
    type: str = "doc"
    content: list[ParagraphContent]

class IssueType(BaseModel):
    name: str

class ProjectInfo(BaseModel):
    key: str

class IssueFields(BaseModel):
    project: ProjectInfo
    summary: str
    description: IssueDescription
    issuetype: IssueType

class IssueCreateRequest(BaseModel):
    fields: IssueFields