"""
Core authentication and authorization module for the Oasis NHI Ticket System.
This module handles JWT token generation, user authentication, and dependency injection
for retrieving the current authenticated user.
"""

import jwt
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import APIKeyHeader
from app.models.models import User, UserInDB, UserCreate, APIKey, StoredAPIKey
from app.core.security import verify_password, get_password_hash, get_secret_hash
from app.core.config import settings
from typing import Any, Optional
from app.core.user_store import RedisUserStore

class _UserStoreContainer:
    def __init__(self):
        self.instance: RedisUserStore | None = None

_user_store_container = _UserStoreContainer()

# API Key scheme for programmatic access
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def _to_public_api_key(api_key: StoredAPIKey) -> APIKey:
    return APIKey(
        id=api_key.id,
        name=api_key.name,
        created_at=api_key.created_at,
    )

def _to_public_user(user: UserInDB) -> User:
    return User(
        username=user.username,
        email=user.email,
        jira_config=user.jira_config,
        api_keys=[_to_public_api_key(api_key) for api_key in user.api_keys],
    )

def configure_user_store(user_store: RedisUserStore) -> None:
    _user_store_container.instance = user_store


def get_user_store() -> RedisUserStore:
    if _user_store_container.instance is None:
        raise RuntimeError("RedisUserStore not initialized. Ensure it's configured during app lifespan.")
    return _user_store_container.instance


async def close_user_store() -> None:
    if _user_store_container.instance is not None:
        await _user_store_container.instance.close()
        _user_store_container.instance = None


async def authenticate_user(username: str, password: str) -> User | None:
    """
    Authenticates a user based on username and password.

    Args:
        username (str): The user's username.
        password (str): The user's plain-text password.

    Returns:
        User | None: Returns a User model if authentication is successful, None otherwise.
    """
    user = await get_user_store().get_user(username)
    if user is None or not verify_password(password, user.password_hash):
        return None
    
    return _to_public_user(user)

async def register_user(user_data: UserCreate) -> User:
    """
    Registers a new user in the system.

    Args:
        user_data (UserCreate): The user's registration details.

    Returns:
        User: The newly created User model.

    Raises:
        ValueError: If the username already exists.
    """
    if await get_user_store().user_exists(user_data.username):
        raise ValueError(f"Username {user_data.username} already exists")

    new_user = await get_user_store().create_user(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
    )

    return _to_public_user(new_user)

def create_access_token(data: dict[str, Any], expires_delta: timedelta) -> str:
    """
    Creates a JWT access token for a user.

    Args:
        data (dict[str, Any]): Data to be encoded into the JWT (claims).
        expires_delta (timedelta): expiration time delta. 

    Returns:
        str: The encoded JWT access token.
    """
    expire = datetime.now(timezone.utc) + expires_delta

    to_encode = data.copy()
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict[str, Any], expires_delta: timedelta) -> str:
    """
    Creates a JWT refresh token for a user.
    """
    return create_access_token(data=data, expires_delta=expires_delta)

def create_csrf_token() -> str:
    """
    Creates a CSRF token to be sent as a readable cookie.
    """
    return secrets.token_urlsafe(32)

def _decode_token(token: str, expected_type: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError as e:
        raise __credentials_exception(reason=str(e))

    token_type = payload.get("type")
    if token_type != expected_type:
        raise __credentials_exception(reason=f"Invalid token type: expected {expected_type}")

    return payload

def _get_bearer_token_from_request(request: Request) -> str | None:
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None

    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None

    return token

def set_auth_cookies(response: Response, access_token: str, refresh_token: str, csrf_token: str) -> None:
    cookie_kwargs = {
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": "lax",
        "path": "/",
        "domain": settings.COOKIE_DOMAIN,
    }
    response.set_cookie(
        key=settings.ACCESS_COOKIE_NAME,
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **cookie_kwargs,
    )
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        **cookie_kwargs,
    )
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
        domain=settings.COOKIE_DOMAIN,
    )

def clear_auth_cookies(response: Response) -> None:
    for cookie_name in (
        settings.ACCESS_COOKIE_NAME,
        settings.REFRESH_COOKIE_NAME,
        settings.CSRF_COOKIE_NAME,
    ):
        response.delete_cookie(
            key=cookie_name,
            path="/",
            domain=settings.COOKIE_DOMAIN,
        )

def issue_auth_cookies(response: Response, username: str) -> None:
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": username, "type": "access"},
        expires_delta=access_token_expires,
    )
    refresh_token = create_refresh_token(
        data={"sub": username, "type": "refresh"},
        expires_delta=refresh_token_expires,
    )
    set_auth_cookies(
        response=response,
        access_token=access_token,
        refresh_token=refresh_token,
        csrf_token=create_csrf_token(),
    )

async def _user_from_access_token(token: str) -> User:
    payload = _decode_token(token, expected_type="access")
    username: str | None = payload.get("sub")
    if username is None:
        raise __credentials_exception(reason="Invalid username in payload")

    user = await get_user_store().get_user(username)
    if user is None:
        raise __credentials_exception(reason=f"User {username} not found")

    return _to_public_user(user)


async def get_user_record(username: str) -> UserInDB | None:
    return await get_user_store().get_user(username)


async def update_user_jira_config(username: str, jira_config: Any) -> UserInDB | None:
    return await get_user_store().set_jira_config(username, jira_config)


async def append_user_api_key(username: str, api_key: StoredAPIKey) -> UserInDB | None:
    return await get_user_store().add_api_key(username, api_key)


async def revoke_user_api_key(username: str, key_id: str) -> bool:
    return await get_user_store().revoke_api_key(username, key_id)

def get_refresh_token_subject(token: str) -> str:
    payload = _decode_token(token, expected_type="refresh")
    username: str | None = payload.get("sub")
    if username is None:
        raise __credentials_exception(reason="Invalid username in payload")

    return username

def __credentials_exception(reason: str = '') -> HTTPException:
    detail = "Could not validate credentials"
    if reason:
        detail = f"{detail}: {reason}"
    
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )

async def get_current_user(request: Request) -> User:
    """
    Dependency injection function to retrieve the currently authenticated user
    from a JWT token.

    Args:
        request (Request): The incoming request containing either auth cookies or a bearer header.

    Returns:
        User: The authenticated User model.

    Raises:
        HTTPException: If the token is invalid or the user is not found.
    """
    token = request.cookies.get(settings.ACCESS_COOKIE_NAME) or _get_bearer_token_from_request(request)
    if not token:
        raise __credentials_exception(reason="No access token provided")

    return await _user_from_access_token(token)

async def get_user_from_api_key(api_key: Optional[str] = Depends(api_key_header)) -> User:
    """
    Dependency injection function to retrieve the user associated with an API key.

    Args:
        api_key (str): The API key from the X-API-Key header.

    Returns:
        User: The authenticated User model.

    Raises:
        HTTPException: If the API key is missing or invalid.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key is missing",
        )
    
    # Simple lookup in our in-memory DB
    user = await get_user_store().find_user_by_api_key(api_key)
    if user is not None:
        return _to_public_user(user)
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API Key",
    )

async def get_any_user(
    request: Request,
    api_key: Optional[str] = Depends(api_key_header)
) -> User:
    """
    Dependency that allows authentication via either JWT token OR API Key.
    Useful for endpoints that are accessed by both the UI and external systems.
    """
    token = request.cookies.get(settings.ACCESS_COOKIE_NAME) or _get_bearer_token_from_request(request)
    if token:
        try:
            return await _user_from_access_token(token)
        except HTTPException:
            if not api_key:
                raise
    
    if api_key:
        return await get_user_from_api_key(api_key)
    
    raise __credentials_exception(reason="No valid authentication provided (Token or API Key)")

async def require_csrf_for_cookie_auth(request: Request) -> None:
    """
    Requires a matching CSRF header when a browser session cookie is used.
    """
    if settings.ACCESS_COOKIE_NAME not in request.cookies:
        return

    csrf_cookie = request.cookies.get(settings.CSRF_COOKIE_NAME)
    csrf_header = request.headers.get(settings.CSRF_HEADER_NAME)
    if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF validation failed",
        )
