"""Project-wide FastAPI dependencies.

Provides:
• DatabaseDep              – SQLAlchemy session
• CurrentUserOptional      – Authenticated user if present, else None
• CurrentUserRequired      – Authenticated user enforced by HTTP 401
• verify_api_key           – Placeholder for future LLM integration
• VectorServiceDep         – Dependency for the vector service
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status, Request, Cookie
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, get_async_db
from app.auth.utils import get_current_user
from app.models.user import User
from app.config import settings
from app.services.vector_service import VectorService, get_vector_service

###############################################################################
# Database session dependency
###############################################################################

DatabaseDep = Annotated[Session, Depends(get_db)]
AsyncDatabaseDep = Annotated[AsyncSession, Depends(get_async_db)]

###############################################################################
# Authentication dependencies
###############################################################################


def _current_user_optional(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
    access_cookie: Annotated[str | None, Cookie(alias="access_token")] = None,
) -> User | None:
    """
    Return currently authenticated user or None.

    This implementation doesn't raise exceptions, instead returning None
    when authentication fails or no credentials are provided.
    """
    try:
        return get_current_user(request, db, authorization, access_cookie)
    except HTTPException:
        return None


def _current_user_required(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Ensure request is authenticated; propagate original 401 if not.
    """
    return user


CurrentUserOptional = Annotated[User | None, Depends(_current_user_optional)]
CurrentUserRequired = Annotated[User, Depends(_current_user_required)]

###############################################################################
# Vector Service Dependency
###############################################################################

VectorServiceDep = Annotated[VectorService, Depends(get_vector_service)]


###############################################################################
# API-key verification placeholder (Phase 3 feature)
###############################################################################


def verify_api_key(x_api_key: str = Header(None)) -> None:
    """Verify the API key provided in the request headers."""
    if settings.openai_api_key and x_api_key != settings.openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )


###############################################################################
# CSRF protection (Phase 2 feature)
###############################################################################

def enforce_csrf(
    csrf_token: str | None = Header(None, alias="X-CSRF-Token")
) -> None:
    """Enforce CSRF protection for state-changing endpoints."""
    if settings.csrf_protection:
        if not csrf_token or csrf_token != settings.csrf_secret:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token missing or invalid",
                headers={"X-Error-Code": "CSRF_FAILED"},
            )
