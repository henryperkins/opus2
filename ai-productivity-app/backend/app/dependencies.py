"""Project-wide FastAPI dependencies.

Provides:
• DatabaseDep              – SQLAlchemy session
• CurrentUserOptional      – Authenticated user if present, else None
• CurrentUserRequired      – Authenticated user enforced by HTTP 401
• verify_api_key           – Placeholder for future LLM integration
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, get_async_db
from app.auth.utils import get_current_user
from app.models.user import User
from app.config import settings

###############################################################################
# Database session dependency
###############################################################################

DatabaseDep = Annotated[Session, Depends(get_db)]
AsyncDatabaseDep = Annotated[AsyncSession, Depends(get_async_db)]

###############################################################################
# Authentication dependencies
###############################################################################


def _current_user_optional(
    user: Annotated[User, Depends(get_current_user)],
) -> User | None:
    """
    Return currently authenticated user or None.

    The underlying `get_current_user` will already raise 401 if no credentials;
    therefore we catch that and swallow the exception to make it optional.
    """
    from fastapi import HTTPException as _HTTPException

    try:
        return user
    except _HTTPException:
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
# API-key verification placeholder (Phase 3 feature)
###############################################################################


def verify_api_key() -> None:  # noqa: D401
    """No-op for now – will check request headers for X-API-Key in future."""
    return None


###############################################################################
# CSRF protection (Phase 2 feature)
###############################################################################

# TODO: Uncomment and configure the following lines once CSRF protection is implemented.

# from fastapi_csrf_protect import CsrfProtect
#
# csrf_protect = CsrfProtect()
#
# def verify_csrf_token(x_csrf_token: str = Header(...)):
#     if not csrf_protect.validate_csrf_token(x_csrf_token):
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Invalid or missing CSRF token",
#         )


###############################################################################
# CSRF protection dependency
###############################################################################


def enforce_csrf(
    csrf_token: str | None = Header(None, alias="X-CSRF-Token")
) -> None:
    """Enforce CSRF protection for state-changing endpoints."""
    # For now, we'll implement a simple CSRF check
    # In production, you'd want to implement proper CSRF token validation
    if hasattr(settings, 'csrf_protection') and settings.csrf_protection:
        csrf_secret = getattr(settings, 'csrf_secret', None)
        if csrf_secret and csrf_token != csrf_secret:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token missing or invalid",
                headers={"X-Error-Code": "CSRF_FAILED"},
            )
