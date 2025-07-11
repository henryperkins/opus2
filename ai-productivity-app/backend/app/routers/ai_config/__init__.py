"""
Combined router for AI configuration endpoints.

Usage in main.py:

    from app.routers.ai_config import ai_config_router
    app.include_router(ai_config_router)
"""
from fastapi import APIRouter

from .read import router as read_router
from .write import router as write_router

ai_config_router = APIRouter()
ai_config_router.include_router(read_router)
ai_config_router.include_router(write_router)

__all__ = ["ai_config_router"]
