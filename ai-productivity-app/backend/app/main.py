"""
FastAPI application entry point with middleware and lifespan management.
"""
# Standard library
import logging
from contextlib import asynccontextmanager

# ---------------------------------------------------------------------------
# Ensure noisy 3rd-party libraries are set to INFO in production before any of
# them emit log records.
# ---------------------------------------------------------------------------

from .logging_config import configure_library_loggers  # noqa: E402 – after sys path setup

configure_library_loggers()

# Third-party
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Local packages
from .config import settings
from .database import init_db

logger = logging.getLogger(__name__)
from .utils.redis_client import close_redis
from .middleware.correlation_id import CorrelationIdMiddleware
from .middleware.security import register_security_middleware
from .routers import auth, projects, monitoring
from .routers import code as code_router
from .routers import email as email_router
from .routers import notifications as notify_router
from .routers import import_git as import_git_router
from .routers import chat as chat_router
from .routers import timeline as timeline_router
from .routers import search as search_router
from .routers import analytics as analytics_router
from .routers import knowledge as knowledge_router
from .routers import rendering as rendering_router
from .routers import copilot as copilot_router
from .routers import prompts as prompts_router
from .routers import repositories as repositories_router
from .routers import project_search as project_search_router
from .routers import feedback as feedback_router
from .chat import admin_routes as admin_router
from .chat import confidence_routes as confidence_router

# Import unified config router
from .routers import unified_config as ai_config_router


@asynccontextmanager
async def lifespan(_app: FastAPI):  # pylint: disable=unused-argument
    """Application lifespan manager.

    The parameter is required by the FastAPI lifespan hook but
    is not used directly within this function.
    """
    # Startup
    init_db()

    # Start embedding worker background loop
    from app.embeddings.worker import start_background_loop
    start_background_loop()

    # Initialize vector store based on configuration
    from app.services.vector_service import vector_service
    try:
        await vector_service.initialize()
        logger.info("Vector store (%s) initialized successfully", settings.vector_store_type)
    except Exception as exc:
        logger.error("Failed to initialize vector store (%s): %s", settings.vector_store_type, exc)

    # Initialize unified configuration
    from app.services.unified_config_service import UnifiedConfigService
    from app.database import SessionLocal
    with SessionLocal() as db:
        service = UnifiedConfigService(db)
        service.initialize_defaults()

    # Seed model catalogue if empty (quick-win – avoids empty dropdown)
    try:
        from app.cli.seed_models import seed_models  # local import to avoid heavy deps
        import asyncio

        await seed_models()  # noqa: SLF001 – util coroutine
    except Exception as exc:  # pragma: no cover – non-critical
        logger.warning("Model seeding skipped: %s", exc)

    yield
    # Shutdown
    await close_redis()  # Close Redis connection pool

    # Stop embedding worker
    from app.embeddings.worker import stop_background_loop
    await stop_background_loop()


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
    # Add WebSocket origins support for cross-origin connections
    # This is needed for WebSocket connections from frontend to backend
    websocket_origins=settings.cors_origins_list + [
        "ws://localhost:5173",
        "ws://localhost:8000",
        "wss://lakefrontdigital.io"
    ]
)

# ---------------------------------------------------------------------------
# Middleware stack
#   1. CORS – must run first so that OPTIONS pre-flights are answered quickly.
#   2. Correlation ID – attaches X-Request-ID header and contextvar.
#   3. Security / SlowAPI – rate-limiting, security headers, CSRF.
# ---------------------------------------------------------------------------

# 1. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list + [
        "http://localhost:5173",
        "https://lakefrontdigital.io"
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Correlation IDs (skip when explicitly disabled)
if not settings.disable_correlation_id:
    app.add_middleware(CorrelationIdMiddleware)

# 3. Security headers & SlowAPI rate-limiter
register_security_middleware(app)

# Include routers
app.include_router(auth.router)
# Note: the "models_router" shim may be missing when unified config is enabled
# Include only when present to avoid FastAPI errors.
app.include_router(projects.router)
app.include_router(monitoring.router)
app.include_router(code_router.router)
app.include_router(chat_router.router)
app.include_router(email_router.router)
app.include_router(notify_router.router)
app.include_router(import_git_router.router)
app.include_router(timeline_router.router)
app.include_router(search_router.router)
app.include_router(analytics_router.router)
app.include_router(knowledge_router.router)
app.include_router(rendering_router.router)
app.include_router(copilot_router.router)
app.include_router(prompts_router.router)
app.include_router(repositories_router.router)
app.include_router(project_search_router.router)
app.include_router(feedback_router.router)
app.include_router(admin_router.router, prefix="/admin", tags=["Admin"])
app.include_router(confidence_router.router, prefix="/confidence", tags=["Confidence"])

app.include_router(ai_config_router.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
