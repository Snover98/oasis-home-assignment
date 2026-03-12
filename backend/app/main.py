from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.api.auth.router import router as auth_router
from app.api.endpoints.jira import router as jira_router
from app.api.jobs.router import router as jobs_router

app = FastAPI(
    title="Oasis NHI Ticket System API",
    description="Backend API for managing NHI findings and Jira integration.",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React frontend dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth_router)
app.include_router(jira_router)
app.include_router(jobs_router)

@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """
    Simple health check endpoint.
    :return: A dictionary indicating the status of the API.
    """
    return {"status": "ok"}

def main() -> None:
    """
    Main entry point for running the application.
    """
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()
