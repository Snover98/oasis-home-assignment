"""
API Router for authentication and user-related endpoints in the Oasis NHI Ticket System.
Handles cookie-based browser authentication, user profile retrieval, and Atlassian OAuth 2.0 flow.
"""

import secrets
import sys
import urllib.parse
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_limiter.depends import RateLimiter
from pydantic_client import get, post
from pydantic_client.async_client import HttpxWebClient
from pyrate_limiter import Duration, Limiter, Rate

from app.core.auth import (
    USERS_DB,
    _to_public_api_key,
    authenticate_user,
    clear_auth_cookies,
    get_current_user,
    get_refresh_token_subject,
    issue_auth_cookies,
    register_user,
    require_csrf_for_cookie_auth,
)
from app.core.config import settings
from app.core.security import get_secret_hash
from app.models.models import (
    APIKey,
    APIKeyCreate,
    APIKeyWithSecret,
    AtlassianResourceResponse,
    AtlassianTokenExchangeRequest,
    AtlassianTokenResponse,
    AuthCallbackResponse,
    AuthUrlResponse,
    JiraConfig,
    StoredAPIKey,
    User,
    UserCreate,
)

router = APIRouter()


async def rate_limit_exceeded_callback(request: Request, response: Response):
    """
    Custom callback for when a rate limit is exceeded.
    Returns a 429 HTTP error with a Retry-After header.
    """
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please try again later.",
            "endpoint": request.url.path,
        },
    )


auth_rate_limiter = RateLimiter(
    limiter=Limiter(Rate(5, Duration.MINUTE)),
    callback=rate_limit_exceeded_callback,
)
auth_rate_limit_dependencies = [] if "pytest" in sys.modules else [Depends(auth_rate_limiter)]


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


@router.post(
    "/api/v1/auth/register",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["auth"],
    dependencies=auth_rate_limit_dependencies,
)
async def register(user_data: UserCreate, response: Response) -> Response:
    """
    Register endpoint to create a new user and issue cookie-based browser auth.
    """
    try:
        register_user(user_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    issue_auth_cookies(response, user_data.username)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post(
    "/token",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["auth"],
    dependencies=auth_rate_limit_dependencies,
)
async def login_for_access_token(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Response:
    """
    Login endpoint to issue cookie-based browser auth using username and password.
    """
    user = authenticate_user(form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    issue_auth_cookies(response, form_data.username)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post("/api/v1/auth/refresh", status_code=status.HTTP_204_NO_CONTENT, tags=["auth"])
async def refresh_auth_session(request: Request, response: Response) -> Response:
    """
    Refreshes browser auth cookies using the refresh token cookie.
    """
    refresh_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if refresh_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is missing")

    username = get_refresh_token_subject(refresh_token)
    if username not in USERS_DB:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    issue_auth_cookies(response, username)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post("/api/v1/auth/logout", status_code=status.HTTP_204_NO_CONTENT, tags=["auth"])
async def logout(
    response: Response,
    _: None = Depends(require_csrf_for_cookie_auth),
) -> Response:
    """
    Clears browser auth cookies.
    """
    clear_auth_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/api/v1/users/me", response_model=User, tags=["users"])
async def read_users_me(current_user: User = Depends(get_current_user)) -> User:
    """
    Returns the profile of the currently authenticated user.
    """
    return current_user


@router.get("/api/v1/jira/auth/url", response_model=AuthUrlResponse, tags=["jira-auth"])
async def get_jira_auth_url(current_user: User = Depends(get_current_user)) -> AuthUrlResponse:
    """
    Generates the Atlassian OAuth 2.0 authorization URL for the user to initiate the connection.
    """
    params = {
        "audience": "api.atlassian.com",
        "client_id": settings.JIRA_CLIENT_ID,
        "scope": settings.JIRA_SCOPES,
        "redirect_uri": settings.JIRA_REDIRECT_URI,
        "state": current_user.username,
        "response_type": "code",
        "prompt": "consent",
    }
    url = f"{settings.ATLASSIAN_AUTH_URL}?{urllib.parse.urlencode(params, quote_via=urllib.parse.quote)}"
    return AuthUrlResponse(url=url)


@router.post("/api/v1/jira/auth/callback", response_model=AuthCallbackResponse, tags=["jira-auth"])
async def jira_auth_callback(
    code: str,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf_for_cookie_auth),
) -> AuthCallbackResponse:
    """
    OAuth 2.0 callback endpoint. Exchanges the authorization code for tokens,
    identifies the accessible Jira site, and stores the configuration for the user.
    """
    if current_user.username not in USERS_DB:
        raise HTTPException(status_code=404, detail=f"User {current_user.username} not found")

    auth_client = AtlassianAuthClient(base_url="https://auth.atlassian.com")
    try:
        exchange_request = AtlassianTokenExchangeRequest(
            client_id=settings.JIRA_CLIENT_ID,
            client_secret=settings.JIRA_CLIENT_SECRET,
            code=code,
            redirect_uri=settings.JIRA_REDIRECT_URI,
        )
        token_data = await auth_client.exchange_token(json=exchange_request)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to exchange token: {str(e)}")

    api_client = AtlassianAPIClient(
        base_url=settings.ATLASSIAN_API_BASE_URL,
        headers={"Authorization": f"Bearer {token_data.access_token}"},
    )

    resources = await api_client.get_accessible_resources()
    if not resources:
        raise HTTPException(status_code=400, detail="No accessible Jira resources found")

    jira_resource = next((r for r in resources if any("jira" in s for s in r.scopes)), resources[0])

    USERS_DB[current_user.username].jira_config = JiraConfig(
        access_token=token_data.access_token,
        refresh_token=token_data.refresh_token,
        cloud_id=jira_resource.id,
        site_url=jira_resource.url,
    )
    return AuthCallbackResponse(status="success", site_name=jira_resource.name)


@router.get("/api/v1/api-keys", response_model=list[APIKey], tags=["api-keys"])
async def get_api_keys(current_user: User = Depends(get_current_user)) -> list[APIKey]:
    """
    Retrieves the list of API keys for the current user.
    """
    return current_user.api_keys


@router.post("/api/v1/api-keys", response_model=APIKeyWithSecret, tags=["api-keys"])
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf_for_cookie_auth),
) -> APIKeyWithSecret:
    """
    Generates and stores a new API key for the user.
    The plain-text key is only returned once at creation time.
    """
    plain_text_key = f"oasis_key_{secrets.token_urlsafe(16)}"
    stored_key = StoredAPIKey(
        id=str(uuid.uuid4()),
        name=key_data.name,
        key_hash=get_secret_hash(plain_text_key),
        created_at=datetime.now(timezone.utc),
    )

    user_in_db = USERS_DB[current_user.username]
    user_in_db.api_keys.append(stored_key)

    public_key = _to_public_api_key(stored_key)
    return APIKeyWithSecret(
        id=public_key.id,
        name=public_key.name,
        created_at=public_key.created_at,
        key=plain_text_key,
    )


@router.delete("/api/v1/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["api-keys"])
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf_for_cookie_auth),
) -> None:
    """
    Revokes (deletes) a specific API key for the user.
    """
    user_in_db = USERS_DB[current_user.username]
    original_length = len(user_in_db.api_keys)

    user_in_db.api_keys = [k for k in user_in_db.api_keys if k.id != key_id]

    if len(user_in_db.api_keys) == original_length:
        raise HTTPException(status_code=404, detail="API Key not found")
