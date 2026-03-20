"""
Main entry point for the Oasis NHI Ticket System FastAPI Backend.
This module initializes the FastAPI application, configures middleware,
and includes the specialized API routers.
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.api.auth.router import router as auth_router
from app.api.endpoints.jira import router as jira_router
from app.api.jobs.router import router as jobs_router
from app.api.jobs.router import run_automated_blog_digest
from app.models.models import HealthResponse

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event manager that handles startup and shutdown logic.
    Starts the automated background job for blog digests.
    """
    # Create the background task for the automated blog digest job
    background_task = asyncio.create_task(run_automated_blog_digest())
    
    yield
    
    # Clean up the background task on shutdown
    background_task.cancel()
    try:
        await background_task
    except asyncio.CancelledError:
        pass

# Initialize the FastAPI application
app = FastAPI(
    title="Oasis NHI Ticket System API",
    description="Backend API for managing Non-Human Identity (NHI) findings and Jira integration.",
    version="1.0.0",
    lifespan=lifespan
)

# Configure Cross-Origin Resource Sharing (CORS)
# Allows the React frontend running on port 5173 to communicate with this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include sub-routers for different logical parts of the application
app.include_router(auth_router)
app.include_router(jira_router)
app.include_router(jobs_router)

@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """
    Simple health check endpoint to verify that the API is running.

    Returns:
        HealthResponse: A response with the status 'ok'.
    """
    return HealthResponse(status="ok")

def main() -> None:
    """
    Main entry point for running the application using uvicorn.
    Configures host, port, and enables auto-reload for development.
    """
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()
