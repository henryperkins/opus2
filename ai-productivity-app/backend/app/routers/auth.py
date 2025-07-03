"""
Authentication API router with Redis-based rate limiting.

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
import logging

# ---------------------------------------------------------------------------
# Rate limiting via SlowAPI – use the shared *limiter* instance defined in
# app.auth.security.  When SlowAPI is unavailable or explicitly disabled via
# the ``DISABLE_RATE_LIMITER`` environment variable the decorator becomes a
# no-op so that the routes continue to work inside unit-tests and restricted
# CI sandboxes.
# ---------------------------------------------------------------------------

from app.auth.security import limiter

# FastAPI & dependencies
from fastapi import (
    APIRouter,
    Request,
    BackgroundTasks,
    Body,
    Cookie,
    Depends,
    HTTPException,
    Response,
    status,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.utils.redis_client import rate_limit
from app.utils.request_helpers import real_ip
from app.dependencies import enforce_csrf

from app.auth import security, utils
from app.auth.schemas import (
    PasswordResetRequest,
    PasswordResetSubmit,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
    UserUpdate,
    PreferencesUpdate,
)
from app.config import settings
from app.dependencies import CurrentUserRequired, DatabaseDep
from app.models.user import User

# Re-use shared helpers to avoid duplication

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------
AUTH_RATE_LIMIT = 5                     # attempts
AUTH_RATE_WINDOW = 60                   # seconds
ACCESS_TOKEN_TTL_MINUTES = 60 * 24      # 24 h

# Rate-limiting spec string understood by SlowAPI (@limiter.limit decorator)
# Example: "5/minute" (matches AUTH_RATE_LIMIT/AUTH_RATE_WINDOW above).
# Keeping the string here avoids accidental drift if the numeric constants
# change.

_LIMIT_DECORATOR_SPEC = "5/minute"

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
    return TokenResponse.from_ttl(token, ACCESS_TOKEN_TTL_MINUTES)


###############################################################################
# Registration
###############################################################################


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=TokenResponse,
)
@limiter.limit(_LIMIT_DECORATOR_SPEC)
async def register(
    request: Request,
    response: Response,
    payload: UserRegister,
    background_tasks: BackgroundTasks,
    db: DatabaseDep,
) -> TokenResponse:
    """User registration with distributed rate limiting."""
    # Rate limit by IP address
    client_ip = real_ip(request)
    headers = await rate_limit(
        key=f"register:{client_ip}",
        limit=AUTH_RATE_LIMIT,
        window=AUTH_RATE_WINDOW,
        error_detail="Too many registration attempts. Please try again later."
    )
    response.headers.update(headers)

    # Validate invite code if required
    invite_code = (payload.invite_code or "").strip()
    if settings.registration_invite_only and not invite_code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration requires an invite code",
            headers={"X-Error-Code": "INVITE_REQUIRED"}
        )

    # Check username/email uniqueness
    existing = db.query(User).filter(
        or_(
            User.username == payload.username.lower(),
            User.email == payload.email.lower()
        )
    ).first()

    if existing:
        if existing.username == payload.username.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken",
                headers={"X-Error-Code": "USERNAME_EXISTS"}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
                headers={"X-Error-Code": "EMAIL_EXISTS"}
            )

    try:
        # Create user
        user = utils.create_user(
            db,
            username=payload.username,
            email=payload.email,
            password=payload.password
        )

        # Send welcome email asynchronously
        if not settings.debug:
            background_tasks.add_task(
                utils.send_welcome_email,
                user.email,
                user.username
            )

        # Issue token and set cookie
        return _issue_token_and_cookie(response, db, user)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Registration failed due to conflict",
            headers={"X-Error-Code": "REGISTRATION_CONFLICT"}
        )



###############################################################################
# Login
###############################################################################


@router.post("/login", response_model=TokenResponse)
@limiter.limit(_LIMIT_DECORATOR_SPEC)
async def login(
    request: Request,
    response: Response,
    payload: UserLogin,
    db: DatabaseDep,
) -> TokenResponse:
    """User login with enhanced error codes and rate limiting."""
    # Distributed rate limiting by IP
    client_ip = real_ip(request)
    headers = await rate_limit(
        key=f"login:{client_ip}",
        limit=AUTH_RATE_LIMIT,
        window=AUTH_RATE_WINDOW,
        error_detail="Too many login attempts. Please try again later."
    )
    response.headers.update(headers)

    # Also rate limit by username/email to prevent targeted attacks
    account_headers = await rate_limit(
        key=f"login:account:{payload.username_or_email.lower()}",
        limit=AUTH_RATE_LIMIT * 2,  # Slightly more lenient per-account
        window=AUTH_RATE_WINDOW * 5,  # Longer window for account-specific
        error_detail="Too many login attempts for this account."
    )
    response.headers.update(account_headers)

    # Verify credentials
    user = utils.verify_credentials(
        db, payload.username_or_email.lower(), payload.password
    )

    if not user:
        # Check if user exists to provide better error codes
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
                    detail="Account is inactive. Please contact support.",
                    headers={"X-Error-Code": "INACTIVE_ACCOUNT"}
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials",
                    headers={"X-Error-Code": "BAD_CREDENTIALS"}
                )
        else:
            # Same error as bad password to prevent enumeration
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"X-Error-Code": "BAD_CREDENTIALS"}
            )

    # Issue token and cookie
    return _issue_token_and_cookie(response, db, user)


###############################################################################
# Logout
###############################################################################

@router.post("/logout", dependencies=[Depends(enforce_csrf)])
@limiter.limit("10/minute")  # less restrictive – session clearing
def logout(
    request: Request,
    response: Response,
    db: DatabaseDep,
    access_cookie: Annotated[str | None, Cookie(alias="access_token")] = None,
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
        samesite="strict",
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


@router.patch("/preferences", response_model=UserResponse)
def update_preferences(
    payload: PreferencesUpdate,
    db: DatabaseDep,
    current_user: CurrentUserRequired,
) -> UserResponse:
    """Update user preferences (e.g., quality settings)."""
    if payload.quality_settings is not None:
        # Merge with existing preferences to avoid overwriting other settings
        existing_prefs = current_user.preferences or {}
        existing_prefs.update({"quality_settings": payload.quality_settings})
        current_user.preferences = existing_prefs

        # Mark as modified for SQLAlchemy to pick up the change in JSONB
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(current_user, "preferences")

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return UserResponse.from_orm(current_user)


###############################################################################
# Password-reset flow
###############################################################################


def _send_reset_email(email: str, token: str) -> None:  # placeholder
    """Background stub that **logs** the reset link instead of sending email.

    The full email service is outside the scope of unit-tests and attempting
    to spin up an event-loop from within Starlette's *background tasks* leads
    to a *"Cannot run the event loop while another loop is running"* runtime
    error under ``TestClient``.  For test-purposes we therefore fall back to a
    lightweight logger statement.  Production deployments should replace this
    stub with the real integration (SendGrid, SES, Mailgun…).
    """
    logger = logging.getLogger(__name__)
    reset_url = f"{settings.frontend_base_url or 'http://localhost:5173'}/reset/{token}"
    logger.info("Password reset requested for %s – link: %s", email, reset_url)


@router.post(
    "/reset-password",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(enforce_csrf)],
    include_in_schema=False,  # deprecated but kept for backward-compat
)
# Note: password reset is unauthenticated but still needs brute-force
# protection.  We set a per-IP limit separate from the global auth bucket.
@limiter.limit(_LIMIT_DECORATOR_SPEC)
# NOTE: Alias kept for the public API that the new frontend consumes.
#       This adheres to the requirements spec naming – `/reset-request`.
#       Both routes execute the same handler to simplify maintenance.

# Public route preferred going forward
@router.post(
    "/reset-request",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(enforce_csrf)]
)
async def request_password_reset(
    request: Request,
    payload: Annotated[PasswordResetRequest, Body()],
    background: BackgroundTasks,
    response: Response,
) -> dict[str, str]:
    """
    Step 1: User requests a reset link/token.
    For our small-team scenario, we simply log the token rather than emailing.
    """
    headers = await rate_limit(
        key=f"pwreset:{payload.email.lower()}",
        limit=AUTH_RATE_LIMIT,
        window=AUTH_RATE_WINDOW * 10,  # 10-minute window
    )
    response.headers.update(headers)

    # Stateless token: JWT with purpose=reset
    token = security.create_access_token(
        {"sub": payload.email.lower(), "purpose": "reset"},
        # shorter TTL (30 min)
        expires_delta=timedelta(minutes=30),
    )
    background.add_task(_send_reset_email, payload.email, token)
    return {"detail": "Password-reset instructions sent if address exists."}


# Legacy path (hidden in docs)
@router.post(
    "/reset-password/submit",
    include_in_schema=False,
    dependencies=[Depends(enforce_csrf)]
)
# New spec-compliant path consumed by the frontend
@router.post("/reset", dependencies=[Depends(enforce_csrf)])
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
    except HTTPException:  # token invalid or expired
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
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
