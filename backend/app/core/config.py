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
    JIRA_SCOPES: str = "read:jira-work write:jira-work read:jira-user offline_access"

    # Authentication Settings
    SECRET_KEY: str = "" # In production, this must be a strong, random value set in .env
    ALGORITHM: str = "HS256"
    REDIS_URL: str = "redis://localhost:6379/0"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    ACCESS_COOKIE_NAME: str = "oasis_access_token"
    REFRESH_COOKIE_NAME: str = "oasis_refresh_token"
    CSRF_COOKIE_NAME: str = "oasis_csrf_token"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"
    JIRA_OAUTH_STATE_COOKIE_NAME: str = "oasis_jira_oauth_state"
    JIRA_OAUTH_STATE_TTL_SECONDS: int = 600
    COOKIE_SECURE: bool = False
    COOKIE_DOMAIN: str | None = None

    # External Services
    OASIS_BLOG_URL: str = "https://www.oasis.security"
    ATLASSIAN_API_BASE_URL: str = "https://api.atlassian.com"
    ATLASSIAN_DEFAULT_SITE_URL: str = "https://atlassian.net"

    # Automated Jobs Settings
    AUTO_BLOG_DIGEST_ENABLED: bool = True
    AUTO_BLOG_DIGEST_USER: str = "testuser"
    AUTO_BLOG_DIGEST_PROJECT_KEY: str = "NHI" # Default project key for automated tickets
    AUTO_BLOG_DIGEST_INTERVAL_SECONDS: int = 3600 # 1 hour

    # Jira Retry Settings
    JIRA_RETRY_ATTEMPTS: int = 3
    JIRA_RETRY_WAIT_MIN: int = 2 # seconds
    JIRA_RETRY_WAIT_MAX: int = 10 # seconds

    # Jira Cache Settings
    JIRA_CACHE_TTL: int = 300 # seconds (5 minutes)

# Global settings instance
settings = Settings()
