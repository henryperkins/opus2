"""
FastAPI application entry point with middleware and lifespan management.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import auth, projects, monitoring, config as config_router
from app.routers import code as code_router
from app.routers import email as email_router
from app.routers import notifications as notify_router
from app.routers import import_git as import_git_router
from app.routers import chat as chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    init_db()
    yield
    # Shutdown
    pass


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(monitoring.router)
app.include_router(code_router.router)
app.include_router(chat_router.router)
app.include_router(config_router.router)
app.include_router(email_router.router)
app.include_router(notify_router.router)
app.include_router(import_git_router.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
