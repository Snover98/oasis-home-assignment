from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Jira OAuth 2.0 (3LO) Settings
    JIRA_CLIENT_ID: str = ""
    JIRA_CLIENT_SECRET: str = ""
    JIRA_REDIRECT_URI: str = "http://localhost:5173/dashboard"
    
    # Atlassian Auth URLs
    ATLASSIAN_AUTH_URL: str = "https://auth.atlassian.com/authorize"
    ATLASSIAN_TOKEN_URL: str = "https://auth.atlassian.com/oauth/token"
    
    # Required scopes for Jira 3LO
    JIRA_SCOPES: str = "read:jira-work write:jira-work read:jira-user"

    model_config = {
        "env_file": (".env", "backend/.env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

settings = Settings()
