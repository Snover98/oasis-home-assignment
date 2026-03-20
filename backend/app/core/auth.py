"""
Core authentication and authorization module for the Oasis NHI Ticket System.
This module handles JWT token generation, user authentication, and dependency injection
for retrieving the current authenticated user.
"""

import jwt
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from app.models.models import User, UserInDB, UserCreate, APIKey, StoredAPIKey
from app.core.security import verify_password, get_password_hash, get_secret_hash, verify_secret
from app.core.config import settings
from typing import Any, Optional

"""
In-memory user store for demonstration.

For an actual implementation, this should be a secret store or a database which is accessed.

Currently I also don't lock the user when modifying it due to this being a single instance backend,
but for scale it will be needed.
"""
USERS_DB: dict[str, UserInDB] = {
    "testuser": UserInDB(
        username="testuser",
        email="test@example.com",
        password_hash="$2b$12$MAaylIRAuacc/pfH.cuEoO7NV57ru17Yjs1xo2CPEiOujauO238l2", # 'password'
        jira_config=None,
        api_keys=[
            StoredAPIKey(
                id=str(uuid.uuid4()),
                name="Default Key",
                key_hash=get_secret_hash("oasis_test_key_1"),
                created_at=datetime.now(timezone.utc)
            )
        ]
    ),
    "testuser2": UserInDB(
        username="testuser2",
        email="test2@example.com",
        password_hash="$2b$12$HcznasTTRG6YHJS7wN8WvO7G60tuPKEPcp8jCq5PL8UhEgzxmbgHC", # 'notpass'
        jira_config=None,
        api_keys=[
            StoredAPIKey(
                id=str(uuid.uuid4()),
                name="Default Key",
                key_hash=get_secret_hash("oasis_test_key_2"),
                created_at=datetime.now(timezone.utc)
            )
        ]
    )
}

# OAuth2 scheme for token retrieval
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)
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

def authenticate_user(username: str, password: str) -> User | None:
    """
    Authenticates a user based on username and password.

    Args:
        username (str): The user's username.
        password (str): The user's plain-text password.

    Returns:
        User | None: Returns a User model if authentication is successful, None otherwise.
    """
    if (user := USERS_DB.get(username)) is None or not verify_password(password, user.password_hash):
        return None
    
    return _to_public_user(user)

def register_user(user_data: UserCreate) -> User:
    """
    Registers a new user in the system.

    Args:
        user_data (UserCreate): The user's registration details.

    Returns:
        User: The newly created User model.

    Raises:
        ValueError: If the username already exists.
    """
    if user_data.username in USERS_DB:
        raise ValueError(f"Username {user_data.username} already exists")

    new_user = UserInDB(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        jira_config=None,
        api_keys=[
            StoredAPIKey(
                id=str(uuid.uuid4()),
                name="Default Key",
                key_hash=get_secret_hash(f"oasis_key_{secrets.token_urlsafe(16)}"),
                created_at=datetime.now(timezone.utc)
            )
        ]
    )
    USERS_DB[user_data.username] = new_user
    
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

def __credentials_exception(reason: str = '') -> HTTPException:
    detail = "Could not validate credentials"
    if reason:
        detail = f"{detail}: {reason}"
    
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Dependency injection function to retrieve the currently authenticated user
    from a JWT token.

    Args:
        token (str): The JWT access token from the request header.

    Returns:
        User: The authenticated User model.

    Raises:
        HTTPException: If the token is invalid or the user is not found.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise __credentials_exception(reason="Invalid username in payload")
    except jwt.PyJWTError as e:
        raise __credentials_exception(reason=str(e))
    
    user = USERS_DB.get(username)
    if user is None:
        raise __credentials_exception(reason=f"User {username} not found")
    
    return _to_public_user(user)

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
    for user in USERS_DB.values():
        for ak in user.api_keys:
            if verify_secret(api_key, ak.key_hash):
                return _to_public_user(user)
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API Key",
    )

async def get_any_user(
    token: Optional[str] = Depends(oauth2_scheme),
    api_key: Optional[str] = Depends(api_key_header)
) -> User:
    """
    Dependency that allows authentication via either JWT token OR API Key.
    Useful for endpoints that are accessed by both the UI and external systems.
    """
    if token:
        try:
            return await get_current_user(token)
        except HTTPException:
            if not api_key:
                raise
    
    if api_key:
        return await get_user_from_api_key(api_key)
    
    raise __credentials_exception(reason="No valid authentication provided (Token or API Key)")
