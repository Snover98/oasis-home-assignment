"""
Configuration management for the Oasis NHI Ticket System.
This module defines the application settings using pydantic-settings,
loading environment variables from .env files.
"""

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Application-wide settings and environment variables.
    """
    
    # Jira OAuth 2.0 (Three-Legged OAuth - 3LO) Settings
    JIRA_CLIENT_ID: str = ""
    JIRA_CLIENT_SECRET: str = ""
    JIRA_REDIRECT_URI: str = "http://localhost:5173/dashboard"
    
    # Atlassian Authorization and Token URLs
    ATLASSIAN_AUTH_URL: str = "https://auth.atlassian.com/authorize"
    ATLASSIAN_TOKEN_URL: str = "https://auth.atlassian.com/oauth/token"
    
    # Required scopes for Jira 3LO to access work items and user data
    JIRA_SCOPES: str = "read:jira-work write:jira-work read:jira-user"

    # Pydantic model configuration for environment file discovery
    model_config = {
        "env_file": (".env", "backend/.env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

# Global settings instance
settings = Settings()
