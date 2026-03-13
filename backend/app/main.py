"""
Main entry point for the Oasis NHI Ticket System FastAPI Backend.
This module initializes the FastAPI application, configures middleware,
and includes the specialized API routers.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.api.auth.router import router as auth_router
from app.api.endpoints.jira import router as jira_router
from app.api.jobs.router import router as jobs_router

# Initialize the FastAPI application
app = FastAPI(
    title="Oasis NHI Ticket System API",
    description="Backend API for managing Non-Human Identity (NHI) findings and Jira integration.",
    version="1.0.0",
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

@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """
    Simple health check endpoint to verify that the API is running.

    Returns:
        dict[str, str]: A dictionary with the status 'ok'.
    """
    return {"status": "ok"}

def main() -> None:
    """
    Main entry point for running the application using uvicorn.
    Configures host, port, and enables auto-reload for development.
    """
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()
