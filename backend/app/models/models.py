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

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None
