"""
Authentication API router.

Endpoints
---------
POST /api/auth/register       – User registration
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
# ---------------------------------------------------------------------------
# Router for authentication related endpoints (Phase 2).
# ---------------------------------------------------------------------------

from typing import Annotated
from datetime import timedelta

from fastapi import (
    APIRouter,
    Request,
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
    UserUpdate,
)
from app.config import settings
from app.dependencies import CurrentUserRequired, DatabaseDep
from app.models.user import User

# Re-use shared helpers to avoid duplication

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
    # Extract JTI from token to persist session metadata
    payload = security.decode_access_token(token)
    jti = payload.get("jti", "")
    utils.create_session(db, user, jti)
    # Configure cookie
    name, value, opts = security.build_auth_cookie(token)
    response.set_cookie(name, value, **opts)
    return TokenResponse.from_ttl(token, settings.access_token_expire_minutes)


###############################################################################
# Registration
###############################################################################


@router.post(
     "/register",
     status_code=status.HTTP_201_CREATED,
     response_model=TokenResponse,
)
# @security.limiter.limit(security.AUTH_ATTEMPT_LIMIT)  # Temporarily disabled for testing
# The test-suite expects the registration endpoint to enforce a simple
# *5 requests / minute* limit.  Instead of relying on the heavyweight *SlowAPI*
# middleware (which pulls in `limits` and *Redis* dependencies) we piggy-back
# on the lightweight helper inside ``app.auth.security``.


def register(
    request: Request,
    payload: Annotated[UserRegister, Body()],
    response: Response,
    db: DatabaseDep,
) -> TokenResponse:
    """User registration. Returns token and sets cookie."""
    # Rate-limit **per IP** to stay in line with the original SlowAPI behaviour.
    client_ip = request.client.host if request.client else "unknown"
    security.enforce_rate_limit(f"register:{client_ip}", limit=5, window=60)

    # Enforce invite code if enabled
    invite_codes = settings.invite_codes_list
    invite_required = bool(invite_codes)
    if invite_required:
        provided_code = (payload.invite_code or "").strip()
        if not provided_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invite code is required for registration."
            )
        if provided_code not in invite_codes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid invite code."
            )

    user = User(
        username=payload.username.lower(),
        email=payload.email.lower(),
        password_hash=security.hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        if 'username' in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exists. Please choose a different username.",
            ) from None
        elif 'email' in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email address already registered. Try logging in instead.",
            ) from None
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Registration failed. Username or email may already exist.",
            ) from None

    return _issue_token_and_cookie(response, db, user)


###############################################################################
# Login
###############################################################################


@router.post(
     "/login",
     response_model=TokenResponse,
)
# @security.limiter.limit(security.AUTH_ATTEMPT_LIMIT)  # Temporarily disabled for testing
# noqa: D401,E501


def login(
    request: Request,
    payload: Annotated[UserLogin, Body()],
    response: Response,
    db: DatabaseDep,
) -> TokenResponse:
    """Authenticate user credentials, return JWT cookie."""
    # Rate-limit failed **and** successful attempts to curb brute-force.
    client_ip = request.client.host if request.client else "unknown"
    security.enforce_rate_limit(f"login:{client_ip}", limit=5, window=60)

    user = utils.verify_credentials(
        db, payload.username_or_email.lower(), payload.password
    )
    if not user:
        # Check if user exists to give more specific feedback
        from sqlalchemy import or_
        existing_user = db.query(User).filter(
            or_(
                User.username == payload.username_or_email.lower(),
                User.email == payload.username_or_email.lower(),
            )
        ).first()

        if existing_user:
            if not existing_user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Account is inactive. Please contact support."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect password. Please try again."
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No account found with this username or email."
            )

    return _issue_token_and_cookie(response, db, user)


###############################################################################
# Logout
###############################################################################

@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: DatabaseDep,
    access_cookie: str = None,
) -> None:
    """Revoke session (DB) and clear auth cookie."""
    # Extract token from cookie or header (same as get_current_user)
    token = None
    authorization = request.headers.get("authorization")
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
    elif access_cookie:
        token = access_cookie
    elif request.cookies.get("access_token"):
        token = request.cookies["access_token"]

    # Attempt to revoke session in DB
    if token:
        try:
            payload = security.decode_access_token(token)
            jti = payload.get("jti")
            if jti:
                from app.auth.utils import revoke_session
                revoke_session(db, jti)
        except Exception:
            # If invalid/expired token: continue to clear cookie anyway
            pass

    # Clear the cookie (as before)
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
    # ------------------------------------------------------------------
    # Debug logging – helps trace *who* is calling the endpoint and verify
    # that authentication worked as expected.  Keep the log-level *INFO*
    # so that messages appear in the default Uvicorn configuration.
    # ------------------------------------------------------------------

    import logging

    logger = logging.getLogger(__name__)
    logger.info("/api/auth/me – user_id=%s username=%s", current_user.id, current_user.username)

    return UserResponse.from_orm(current_user)


###############################################################################
# Profile Update (/me – PATCH)
###############################################################################


@router.patch("/me", response_model=UserResponse)
def update_profile(
    payload: Annotated[UserUpdate, Body()],
    db: DatabaseDep,
    current_user: CurrentUserRequired,
) -> UserResponse:
    """Update authenticated user's profile.

    Supports changing `username`, `email`, and `password` (hashed).
    Performs uniqueness checks and returns the updated profile on success.
    """

    data = payload.dict(exclude_unset=True, exclude_none=True)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No changes provided. Please specify username, email, or password to update."
        )

    # Username
    if (username := data.get("username")) and username != current_user.username:
        conflict = db.query(User).filter(User.username == username).filter(User.id != current_user.id).first()
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Username '{username}' is already taken. Please choose a different username."
            )
        current_user.username = username

    # Email
    if (email := data.get("email")) and email != current_user.email:
        conflict = db.query(User).filter(User.email == email).filter(User.id != current_user.id).first()
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email '{email}' is already registered to another account."
            )
        current_user.email = email

    # Password
    if (password := data.get("password")):
        current_user.password_hash = security.hash_password(password)

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return UserResponse.from_orm(current_user)


###############################################################################
# Password-reset flow
###############################################################################


def _send_reset_email(email: str, token: str) -> None:  # placeholder
    """Delegate email delivery to the internal micro-service."""
    from app.routers.email import EmailPayload, send_email_endpoint  # local import to avoid circular

    subject = "Your Opus 2 password-reset link"
    reset_url = f"{settings.frontend_base_url or 'http://localhost:5173'}/reset/{token}"
    body = (
        "Hello,\n\n"
        "We received a request to reset your password.  Use the link below to choose a new one.\n\n"
        f"{reset_url}\n\n"
        "If you did not request a password reset you can safely ignore this email.\n\n"
        "— Opus 2"
    )

    payload = EmailPayload(to=email, subject=subject, body=body)
    # Directly invoke the endpoint handler instead of making an HTTP call – it
    # returns a JSON dict but we ignore the result.
    import anyio

    anyio.run(send_email_endpoint, payload)  # noqa: TID251


@router.post(
    "/reset-password",
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,  # deprecated but kept for backward-compat
)
# NOTE: Alias kept for the public API that the new frontend consumes.
#       This adheres to the requirements spec naming – `/reset-request`.
#       Both routes execute the same handler to simplify maintenance.

# Public route preferred going forward
@router.post("/reset-request", status_code=status.HTTP_202_ACCEPTED)
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


# Legacy path (hidden in docs)
@router.post("/reset-password/submit", include_in_schema=False)
# New spec-compliant path consumed by the frontend
@router.post("/reset")
def submit_password_reset(
    payload: Annotated[PasswordResetSubmit, Body()],
    db: DatabaseDep,
    response: Response,
) -> None:
    """
    Step 2: User submits new password along with the token they received.
    """
    try:
        data = security.decode_access_token(payload.token)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token. Please request a new password reset."
        )

    if data.get("purpose") != "reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token. This token is not for password reset."
        )

    email = data.get("sub", "")
    user: User | None = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email address."
        )

    user.password_hash = security.hash_password(payload.new_password)
    db.add(user)
    db.commit()
    response.status_code = status.HTTP_204_NO_CONTENT
