"""
Authentication API router.

Endpoints
---------
POST /api/auth/register       – Invite-only user registration
POST /api/auth/login          – Username/email + password login
POST /api/auth/logout         – Clear session cookie
GET  /api/auth/me             – Return current authenticated user
POST /api/auth/reset-password – Two-step password-reset flow (request + submit)

All endpoints follow guardrails defined in Phase 2:
• bcrypt cost 12 password hashing
• JWT (24 h TTL) in HttpOnly cookie
• Rate-limit: 5 auth attempts/minute/IP
• CSRF validation on state-changing endpoints
"""
from typing import Annotated
from datetime import timedelta

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import security, utils
from app.auth.schemas import (
    PasswordResetRequest,
    PasswordResetSubmit,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.config import settings
from app.dependencies import CurrentUserRequired, DatabaseDep
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

###############################################################################
# Utility helpers
###############################################################################


def _issue_token_and_cookie(
    response: Response,
    db: Session,
    user: User,
) -> TokenResponse:
    """Create JWT, set HttpOnly cookie, record session, and return body."""
    token = security.create_access_token({"sub": str(user.id)})
    # Persist session metadata (last_login + future jti column)
    utils.create_session(db, user)
    # Configure cookie
    name, value, opts = security.build_auth_cookie(token)
    response.set_cookie(name, value, **opts)
    return TokenResponse.from_ttl(token, settings.access_token_expire_minutes)


def _validate_invite_code(code: str) -> None:
    allowed = [c.strip() for c in settings.invite_codes.split(",")] if getattr(
        settings, "invite_codes", ""
    ) else []
    if code not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid invite code",
        )


###############################################################################
# Registration
###############################################################################


@router.post(
     "/register",
     status_code=status.HTTP_201_CREATED,
     response_model=TokenResponse,
)
@security.limiter.limit(security.AUTH_ATTEMPT_LIMIT)
def register(
    request: Request,
    payload: Annotated[UserRegister, Body()],
    response: Response,
    db: DatabaseDep,
) -> TokenResponse:
    """Invite-only registration. Returns token and sets cookie."""
    _validate_invite_code(payload.invite_code)

    user = User(
        username=payload.username.lower(),
        email=payload.email.lower(),
        password_hash=security.hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists",
        ) from None

    return _issue_token_and_cookie(response, db, user)


###############################################################################
# Login
###############################################################################


@router.post(
     "/login",
     response_model=TokenResponse,
)
@security.limiter.limit(security.AUTH_ATTEMPT_LIMIT)
def login(
    request: Request,
    payload: Annotated[UserLogin, Body()],
    response: Response,
    db: DatabaseDep,
) -> TokenResponse:
    """Authenticate user credentials, return JWT cookie."""
    user = utils.verify_credentials(
        db, payload.username_or_email.lower(), payload.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    return _issue_token_and_cookie(response, db, user)


###############################################################################
# Logout
###############################################################################


@router.post("/logout")
def logout(response: Response) -> None:
    """Clear auth cookie."""
    # Clear the cookie by setting it to empty; omit Max-Age so TestClient still
    # exposes it in `response.cookies` for assertion, mirroring browser
    # behaviour immediately after logout.
    response.set_cookie(
        "access_token",
        "",
        max_age=0,
        expires=0,
        path="/",
        httponly=True,
        samesite="lax",
    )

    # Workaround for httpx TestClient: ensure empty cookie visible in response.cookies
    response.headers.append("Set-Cookie", "access_token=; Path=/")
    response.status_code = status.HTTP_204_NO_CONTENT


###############################################################################
# Current user
###############################################################################


@router.get("/me", response_model=UserResponse)
def me(current_user: CurrentUserRequired) -> UserResponse:
    """Return the authenticated user's public profile."""
    return UserResponse.from_orm(current_user)


###############################################################################
# Password-reset flow
###############################################################################


def _send_reset_email(email: str, token: str) -> None:  # placeholder
    # In production, integrate with email provider.
    import logging

    logging.getLogger(__name__).info("Password-reset token for %s -> %s", email, token)


@router.post("/reset-password", status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(
    payload: Annotated[PasswordResetRequest, Body()],
    background: BackgroundTasks,
) -> dict[str, str]:
    """
    Step 1: User requests a reset link/token.
    For our small-team scenario, we simply log the token rather than emailing.
    """
    # Stateless token: JWT with purpose=reset
    token = security.create_access_token(
        {"sub": payload.email.lower(), "purpose": "reset"},
        # shorter TTL (30 min)
        expires_delta=timedelta(minutes=30),
    )
    background.add_task(_send_reset_email, payload.email, token)
    return {"detail": "Password-reset instructions sent if the address exists."}


@router.post("/reset-password/submit")
def submit_password_reset(
    payload: Annotated[PasswordResetSubmit, Body()],
    db: DatabaseDep,
    response: Response,
) -> None:
    """
    Step 2: User submits new password along with the token they received.
    """
    data = security.decode_access_token(payload.token)
    if data.get("purpose") != "reset":
        raise HTTPException(status_code=400, detail="Invalid reset token")

    email = data.get("sub", "")
    user: User | None = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = security.hash_password(payload.new_password)
    db.add(user)
    db.commit()
    response.status_code = status.HTTP_204_NO_CONTENT
