# Router package exports
# ---------------------------------------------------------------------------
# Public router exports
# ---------------------------------------------------------------------------

from .monitoring import router as monitoring_router
from .auth import router as auth_router

# Unified AI configuration router (replaces legacy config/models routers)
from .projects import router as projects_router
from .unified_config import router as config_router  # Unified configuration endpoints

# Analytics router (MVP)
# Keep import optional to avoid breaking deployments that do not yet require
# analytics.  The router itself has zero external deps so it is safe.
from .project_search import router as project_search_router
from .analytics import router as analytics_router

__all__ = [
    "monitoring_router",
    "auth_router",
    "projects_router",
    "config_router",
    "project_search_router",
    "analytics_router",
]
