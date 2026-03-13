"""
Core authentication and authorization module for the Oasis NHI Ticket System.
This module handles JWT token generation, user authentication, and dependency injection
for retrieving the current authenticated user.
"""

import jwt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.models.models import User, UserInDB
from app.core.security import verify_password
from app.core.config import settings
from typing import Any

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
        jira_config=None
    ),
    "testuser2": UserInDB(
        username="testuser2",
        email="test2@example.com",
        password_hash="$2b$12$HcznasTTRG6YHJS7wN8WvO7G60tuPKEPcp8jCq5PL8UhEgzxmbgHC", # 'notpass'
        jira_config=None
    )
}

# OAuth2 scheme for token retrieval
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

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
    
    return User(
        username=user.username, 
        email=user.email, 
        jira_config=user.jira_config
    )

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
    
    return User(username=user.username, email=user.email, jira_config=user.jira_config)
