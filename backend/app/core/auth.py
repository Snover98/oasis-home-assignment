import jwt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.models.models import TokenData, User, JiraConfig
from app.core.security import verify_password
from typing import Any

# In-memory user store for demonstration
USERS_DB = {
    "testuser": {
        "username": "testuser",
        "email": "test@example.com",
        "password_hash": "$2b$12$MAaylIRAuacc/pfH.cuEoO7NV57ru17Yjs1xo2CPEiOujauO238l2", # 'password'
        "jira_config": None
    },
    "testuser2": {
        "username": "testuser2",
        "email": "test2@example.com",
        "password_hash": "$2b$12$HcznasTTRG6YHJS7wN8WvO7G60tuPKEPcp8jCq5PL8UhEgzxmbgHC", # 'notpass'
        "jira_config": None
    }
}

SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def authenticate_user(username: str, password: str) -> User | bool:
    """
    Authenticates a user based on username and password.
    :param username: The username.
    :param password: The password.
    :return: User object if authenticated, False otherwise.
    """
    user_dict = USERS_DB.get(username)
    if not user_dict:
        return False
    if not verify_password(password, user_dict["password_hash"]):
        return False
    return User(
        username=user_dict["username"], 
        email=user_dict["email"], 
        jira_config=JiraConfig(**user_dict["jira_config"]) if user_dict.get("jira_config") else None
    )

def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    Creates a JWT access token.
    :param data: Data to encode in the token.
    :param expires_delta: Optional expiration time delta.
    :return: The encoded JWT token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Retrieves the current user from the JWT token.
    :param token: The JWT token.
    :return: The authenticated User.
    :raises HTTPException: If token is invalid or user not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except jwt.PyJWTError:
        raise credentials_exception
    
    user_dict = USERS_DB.get(token_data.username) if token_data.username else None
    if user_dict is None:
        raise credentials_exception
    
    # Construct User object
    jira_config = JiraConfig(**user_dict["jira_config"]) if user_dict.get("jira_config") else None
    return User(username=user_dict["username"], email=user_dict["email"], jira_config=jira_config)
