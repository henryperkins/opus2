"""Project-wide FastAPI dependencies.

Provides:
• DatabaseDep              – SQLAlchemy session
• CurrentUserOptional      – Authenticated user if present, else None
• CurrentUserRequired      – Authenticated user enforced by HTTP 401
• verify_api_key           – Placeholder for future LLM integration
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.utils import get_current_user
from app.models.user import User

###############################################################################
# Database session dependency
###############################################################################

DatabaseDep = Annotated[Session, Depends(get_db)]

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
