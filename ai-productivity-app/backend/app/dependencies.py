# Common dependencies for dependency injection
from typing import Annotated
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from .database import get_db


# Type alias for database dependency
DatabaseDep = Annotated[Session, Depends(get_db)]


# Placeholder for future auth dependencies
def get_current_user_optional():
    """Optional user authentication for future phases"""
    return None


def get_current_user_required():
    """Required user authentication for future phases"""
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required - coming in Phase 2",
    )


# Type aliases for auth dependencies (future use)
CurrentUserOptional = Annotated[dict, Depends(get_current_user_optional)]
CurrentUserRequired = Annotated[dict, Depends(get_current_user_required)]
