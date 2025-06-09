# Router package exports
# ---------------------------------------------------------------------------
# Public router exports
# ---------------------------------------------------------------------------

from .monitoring import router as monitoring_router
from .auth import router as auth_router
from .projects import router as projects_router
from .config import router as config_router  # new – exposes provider metadata

__all__ = [
    "monitoring_router",
    "auth_router",
    "projects_router",
    "config_router",
]
