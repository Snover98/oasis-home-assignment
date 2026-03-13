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

    # Authentication Settings
    SECRET_KEY: str = "" # In production, this must be a strong, random value set in .env
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # External Services
    OASIS_BLOG_URL: str = "https://www.oasis.security"
    ATLASSIAN_API_BASE_URL: str = "https://api.atlassian.com"
    ATLASSIAN_DEFAULT_SITE_URL: str = "https://atlassian.net"

# Global settings instance
settings = Settings()
