"""Compatibility stub for legacy `app.routers.models` import path.

The unified configuration router supersedes this module.  We keep an **empty**
``APIRouter`` instance so that old `from app.routers import models` imports
continue to work until the call-sites are updated or removed.
"""

from fastapi import APIRouter

# Empty router – no endpoints
router = APIRouter()

__all__: list[str] = ["router"]
