"""
Purpose: Helper utilities and dependencies used by Phase 2 authentication
workflows.

Contains:
• verify_credentials – check username/email + password against DB
• create_session      – update last_login timestamp (sessions table later)
• get_current_user    – FastAPI dependency to retrieve authenticated user
"""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models.user import User
from . import security

###############################################################################
# Password / credential helpers
###############################################################################


def verify_credentials(
    db: Session,
    username_or_email: str,
    password: str,
) -> Optional[User]:
    """
    Return user instance if credentials are valid, else None.

    Accepts either username or email for convenience.
    """
    query = db.query(User).filter(
        or_(
            User.username == username_or_email.lower(),
            User.email == username_or_email.lower(),
        )
    )
    user: User | None = query.first()
    if not user or not security.verify_password(password, user.password_hash):
        return None
    return user


###############################################################################
# Session management (placeholder; full table arrives via migration)
###############################################################################


def create_session(db: Session, user: User) -> None:
    """
    Record user's last_login timestamp and commit.

    Later, the sessions table will store active JWT identifiers.
    """
    from datetime import datetime, timezone

    user.last_login = datetime.now(
        tz=timezone.utc
    )  # type: ignore[attr-defined]
    db.add(user)
    db.commit()


###############################################################################
# Dependency: retrieve current user from JWT (cookie or Bearer header)
###############################################################################


def get_current_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
    access_cookie: Annotated[str | None, Cookie(alias="access_token")] = None,
) -> User:
    """
    Attempt to locate & validate JWT from Authorization header or access_token
    cookie, returning the associated active User instance.

    Raises HTTP 401 if no valid token or user.
    """
    token: str | None = None

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
    elif access_cookie:
        token = access_cookie

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = security.decode_access_token(token)
    user_id = security.token_sub_identity(payload)

    user: User | None = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User inactive or not found",
        )

    # In future we can verify jti against sessions table here
    return user
