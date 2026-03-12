import urllib.parse
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta

from app.models.models import User, Token, JiraConfig
from app.core.config import settings
from app.core.auth import (
    authenticate_user, 
    create_access_token, 
    get_current_user, 
    ACCESS_TOKEN_EXPIRE_MINUTES,
    USERS_DB
)

router = APIRouter()

@router.post("/token", response_model=Token, tags=["auth"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> dict[str, str]:
    """
    Login endpoint to obtain a JWT access token.
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/api/v1/users/me", response_model=User, tags=["users"])
async def read_users_me(current_user: User = Depends(get_current_user)) -> User:
    """
    Returns the currently authenticated user's profile.
    """
    return current_user

@router.get("/api/v1/jira/auth/url", tags=["jira-auth"])
async def get_jira_auth_url(current_user: User = Depends(get_current_user)) -> dict[str, str]:
    """
    Generates the Atlassian OAuth 2.0 authorization URL.
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
    return {"url": url}

@router.post("/api/v1/jira/auth/callback", tags=["jira-auth"])
async def jira_auth_callback(
    code: str, 
    current_user: User = Depends(get_current_user)
) -> dict[str, str]:
    """
    Handles the redirect from Atlassian, exchanges the code for tokens,
    and fetches the accessible Jira resources (sites).
    """
    async with httpx.AsyncClient() as client:
        # 1. Exchange code for access token
        token_response = await client.post(
            settings.ATLASSIAN_TOKEN_URL,
            json={
                "grant_type": "authorization_code",
                "client_id": settings.JIRA_CLIENT_ID,
                "client_secret": settings.JIRA_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.JIRA_REDIRECT_URI
            }
        )
        if token_response.is_error:
            raise HTTPException(status_code=400, detail=f"Failed to exchange token: {token_response.text}")
        
        token_data = token_response.json()
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")

        # 2. Fetch accessible resources (cloud_id)
        resources_response = await client.get(
            "https://api.atlassian.com/oauth/token/accessible-resources",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        resources = resources_response.json()
        if not resources:
            raise HTTPException(status_code=400, detail="No accessible Jira resources found")
        
        # Look specifically for resources that have Jira scopes
        jira_resource = next(
            (r for r in resources if any("jira" in s for s in r.get("scopes", []))), 
            resources[0]
        )
        
        # 3. Store in USERS_DB
        jira_config = JiraConfig(
            access_token=access_token,
            refresh_token=refresh_token,
            cloud_id=jira_resource["id"],
            site_url=jira_resource["url"]
        )
        
        if current_user.username in USERS_DB:
            USERS_DB[current_user.username]["jira_config"] = jira_config.model_dump()
            return {"status": "success", "site_name": jira_resource["name"]}
            
    raise HTTPException(status_code=404, detail="User not found")
