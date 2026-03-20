"""
API Router for authentication and user-related endpoints in the Oasis NHI Ticket System.
Handles JWT token generation, user profile retrieval, and Atlassian OAuth 2.0 flow.
"""

import urllib.parse
import secrets
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta, datetime, timezone

from pydantic_client import get, post
from pydantic_client.async_client import HttpxWebClient
from app.models.models import (
    User, Token, JiraConfig, AtlassianTokenResponse, AtlassianResourceResponse,
    AtlassianTokenExchangeRequest, AuthUrlResponse, AuthCallbackResponse, UserCreate,
    APIKey, APIKeyCreate
)
from app.core.config import settings
from app.core.auth import (
    authenticate_user, 
    create_access_token, 
    get_current_user, 
    register_user,
    USERS_DB
)

router = APIRouter()

class AtlassianAuthClient(HttpxWebClient):
    """
    Declarative client for Atlassian's OAuth 2.0 token endpoints.
    """
    @post("/oauth/token")
    async def exchange_token(self, json: AtlassianTokenExchangeRequest) -> AtlassianTokenResponse: 
        """Exchanges an authorization code for access and refresh tokens."""
        ...

class AtlassianAPIClient(HttpxWebClient):
    """
    Declarative client for Atlassian's accessible-resources endpoint.
    """
    @get("/oauth/token/accessible-resources")
    async def get_accessible_resources(self) -> list[AtlassianResourceResponse]: 
        """Retrieves the list of Jira sites accessible with the current access token."""
        ...

@router.post("/api/v1/auth/register", response_model=Token, tags=["auth"])
async def register(user_data: UserCreate) -> dict[str, str]:
    """
    Register endpoint to create a new user and obtain a JWT access token.

    Args:
        user_data (UserCreate): The registration details (username, email, password).

    Returns:
        dict[str, str]: The generated JWT access token and token type.

    Raises:
        HTTPException: If the username already exists.
    """
    try:
        register_user(user_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/token", response_model=Token, tags=["auth"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> dict[str, str]:
    """
    Login endpoint to obtain a JWT access token using username and password.

    Args:
        form_data (OAuth2PasswordRequestForm): Standard OAuth2 form containing 'username' and 'password'.

    Returns:
        dict[str, str]: The generated JWT access token and token type.

    Raises:
        HTTPException: If authentication fails.
    """
    user = authenticate_user(form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/api/v1/users/me", response_model=User, tags=["users"])
async def read_users_me(current_user: User = Depends(get_current_user)) -> User:
    """
    Returns the profile of the currently authenticated user.

    Args:
        current_user (User): The authenticated user (from dependency).

    Returns:
        User: The user profile including any existing Jira configuration.
    """
    return current_user

@router.get("/api/v1/jira/auth/url", response_model=AuthUrlResponse, tags=["jira-auth"])
async def get_jira_auth_url(current_user: User = Depends(get_current_user)) -> AuthUrlResponse:
    """
    Generates the Atlassian OAuth 2.0 authorization URL for the user to initiate the connection.

    Args:
        current_user (User): The authenticated user (from dependency).

    Returns:
        AuthUrlResponse: The URL to which the frontend should redirect the user.
    """
    params = {
        "audience": "api.atlassian.com",
        "client_id": settings.JIRA_CLIENT_ID,
        "scope": settings.JIRA_SCOPES,
        "redirect_uri": settings.JIRA_REDIRECT_URI,
        "state": current_user.username,
        "response_type": "code",
        "prompt": "consent"
    }
    url = f"{settings.ATLASSIAN_AUTH_URL}?{urllib.parse.urlencode(params, quote_via=urllib.parse.quote)}"
    return AuthUrlResponse(url=url)

@router.post("/api/v1/jira/auth/callback", response_model=AuthCallbackResponse, tags=["jira-auth"])
async def jira_auth_callback(
    code: str, 
    current_user: User = Depends(get_current_user)
) -> AuthCallbackResponse:
    """
    OAuth 2.0 callback endpoint. Exchanges the authorization code for tokens,
    identifies the accessible Jira site, and stores the configuration for the user.

    Args:
        code (str): The authorization code returned by Atlassian.
        current_user (User): The authenticated user (from dependency).

    Returns:
        AuthCallbackResponse: A success message and the name of the connected site.

    Raises:
        HTTPException: If token exchange fails or no Jira sites are accessible or user does not exist
    """
    if current_user.username not in USERS_DB:
        raise HTTPException(status_code=404, detail=f"User {current_user.username} not found")

    # 1. Exchange code for access token
    auth_client = AtlassianAuthClient(base_url="https://auth.atlassian.com")
    try:
        exchange_request = AtlassianTokenExchangeRequest(
            client_id=settings.JIRA_CLIENT_ID,
            client_secret=settings.JIRA_CLIENT_SECRET,
            code=code,
            redirect_uri=settings.JIRA_REDIRECT_URI
        )
        token_data = await auth_client.exchange_token(json=exchange_request)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to exchange token: {str(e)}")
    
    # 2. Fetch accessible resources (cloud_id)
    api_client = AtlassianAPIClient(
        base_url="https://api.atlassian.com",
        headers={"Authorization": f"Bearer {token_data.access_token}"}
    )
    
    resources = await api_client.get_accessible_resources()
    if not resources:
        raise HTTPException(status_code=400, detail="No accessible Jira resources found")
    
    # Identify the correct Jira resource by checking for required scopes
    jira_resource = next(
        (r for r in resources if any("jira" in s for s in r.scopes)), 
        resources[0]
    )
    
    # 3. Store the Jira configuration in the user's database record
    USERS_DB[current_user.username].jira_config = JiraConfig(
        access_token=token_data.access_token,
        refresh_token=token_data.refresh_token,
        cloud_id=jira_resource.id,
        site_url=jira_resource.url
    )
    return AuthCallbackResponse(status="success", site_name=jira_resource.name)


@router.get("/api/v1/api-keys", response_model=list[APIKey], tags=["api-keys"])
async def get_api_keys(current_user: User = Depends(get_current_user)) -> list[APIKey]:
    """
    Retrieves the list of API keys for the current user.
    """
    return current_user.api_keys

@router.post("/api/v1/api-keys", response_model=APIKey, tags=["api-keys"])
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_user)
) -> APIKey:
    """
    Generates and stores a new API key for the user.
    """
    new_key = APIKey(
        id=str(uuid.uuid4()),
        name=key_data.name,
        key=f"oasis_key_{secrets.token_urlsafe(16)}",
        created_at=datetime.now(timezone.utc)
    )
    
    # Update the DB record
    user_in_db = USERS_DB[current_user.username]
    user_in_db.api_keys.append(new_key)
    
    return new_key

@router.delete("/api/v1/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["api-keys"])
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user)
) -> None:
    """
    Revokes (deletes) a specific API key for the user.
    """
    user_in_db = USERS_DB[current_user.username]
    original_length = len(user_in_db.api_keys)
    
    user_in_db.api_keys = [k for k in user_in_db.api_keys if k.id != key_id]
    
    if len(user_in_db.api_keys) == original_length:
        raise HTTPException(status_code=404, detail="API Key not found")
