# backend/app/auth/security.py
# flake8: noqa: E501  -- deliberate: long strings & URLs are acceptable here
"""Authentication and security utilities.

This module bundles password hashing, JWT handling, CSRF helpers and a tiny
in-memory rate-limiter.  Heavy dependencies (*passlib*, *python-jose*) are
loaded lazily; lightweight stubs keep unit-tests running inside restricted
sandboxes that lack wheels.

The code is framework-agnostic except where it raises ``HTTPException`` for
FastAPI consumers.  All helpers are pure functions and avoid mutating caller
state.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

# -----------------------------------------------------------------------------
# Optional dependency: SlowAPI rate-limiter (wrapper around limits)
# -----------------------------------------------------------------------------
# The real *slowapi* package is preferred but may be missing in the restricted
# execution environment.  We therefore attempt to import it and fall back to a
# minimal shim that exposes the subset used by the application:
#     • Limiter – constructor accepts *enabled* / *key_func*
#     • decorator limit() returning identity wrapper
#     • util.get_remote_address – returns "127.0.0.1" for stubs
#
# This keeps FastAPI router definitions importable and unit-tests runnable even
# when the optional dependency is absent.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# SlowAPI import & dynamic enable/disable flag
# -----------------------------------------------------------------------------
import os


try:
    from slowapi import Limiter  # type: ignore
    from slowapi.util import get_remote_address  # type: ignore

    # Honour global opt-out (tests/dev) via DISABLE_RATE_LIMITER.
    _HAS_SLOWAPI = os.getenv("DISABLE_RATE_LIMITER", "false").lower() != "true"

except ModuleNotFoundError:  # pragma: no cover – fallback stubs

    _HAS_SLOWAPI = False

    class Limiter:  # type: ignore  # pylint: disable=too-few-public-methods
        """Stub Limiter replicating public API used by this app."""

        def __init__(self, *_, **__):  # noqa: D401 – any signature
            self.enabled = False

        # Decorator `.limit("5/minute")`
        def limit(self, *_d_args, **_d_kwargs):  # noqa: D401
            def _decorator(func):  # noqa: D401
                return func

            return _decorator

    def get_remote_address(request):  # noqa: D401, W0613
        return "127.0.0.1"


from fastapi import HTTPException, status
# SlowAPI limiter will use Redis so that limits are shared across gunicorn
# workers.  We dynamically derive the connection URL from the same helper that
# the rest of the application uses to talk to Redis to avoid configuration
# drift.

from app.config import settings  # type: ignore  # pylint: disable=import-error
from app.utils.redis_client import _redis_url  # type: ignore

__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "token_sub_identity",
    "build_auth_cookie",
    "generate_csrf_token",
    "build_csrf_cookie",
    "validate_csrf",
    "enforce_rate_limit",
    "limiter",
]

# -----------------------------------------------------------------------------
# Optional dependency: passlib
# -----------------------------------------------------------------------------
try:
    from passlib.context import CryptContext  # type: ignore
except ModuleNotFoundError as e:  # pragma: no cover
    raise ImportError(
        "Passlib (with bcrypt) must be installed for password hashing. Insecure fallback is forbidden."
    ) from e

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# -----------------------------------------------------------------------------
# Optional dependency: python-jose
# -----------------------------------------------------------------------------
try:
    from jose import JWTError, jwt  # type: ignore

    _HAS_JOSE = True
except ModuleNotFoundError:  # pragma: no cover
    _HAS_JOSE = False

    class JWTError(Exception):
        """Fallback JWT error raised by the stub implementation."""

    class _FakeJWTModule:
        """Extremely small subset of python-jose needed by this project."""

        @staticmethod
        def _b64url_encode(data: bytes) -> str:  # noqa: D401
            return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

        @staticmethod
        def _b64url_decode(data: str) -> bytes:  # noqa: D401
            padding = "=" * (-len(data) % 4)
            return base64.urlsafe_b64decode(data + padding)

        @staticmethod
        def encode(payload: Dict[str, Any], secret: str, algorithm: str = "HS256") -> str:  # noqa: D401
            header = {"alg": algorithm, "typ": "JWT"}
            segments = [
                _FakeJWTModule._b64url_encode(json.dumps(header).encode()),
                _FakeJWTModule._b64url_encode(json.dumps(payload).encode()),
            ]
            signing_input = ".".join(segments).encode()
            signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
            segments.append(_FakeJWTModule._b64url_encode(signature))
            return ".".join(segments)


        # Accept *algorithms* kwarg for compatibility with python-jose API
        @staticmethod
        def decode(
            token: str,
            secret: str,
            _algorithms: Optional[list[str]] = None,
            algorithms: Optional[list[str]] = None,  # type: ignore[override]
            **__kwargs,
        ):
            try:
                header_b64, payload_b64, signature_b64 = token.split(".")

            except ValueError as exc:
                raise JWTError("Invalid token structure") from exc

            signing_input = f"{header_b64}.{payload_b64}".encode()
            expected_sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
            actual_sig = _FakeJWTModule._b64url_decode(signature_b64)
            if not hmac.compare_digest(expected_sig, actual_sig):
                raise JWTError("Signature verification failed")

            payload_json = _FakeJWTModule._b64url_decode(payload_b64)
            payload = json.loads(payload_json)

            exp = payload.get("exp")
            if exp and time.time() > exp:
                raise JWTError("Token expired")

            return payload

    jwt = _FakeJWTModule()  # type: ignore

# -----------------------------------------------------------------------------
# Rate-limiting (simple in-memory token bucket for unit-tests)
# -----------------------------------------------------------------------------
_AUTH_RATE_LIMIT: Dict[str, list[float]] = {}
_RATE_WINDOW_SECONDS = 60.0
_RATE_MAX_ATTEMPTS = 5


def enforce_rate_limit(key: str, *, limit: int = _RATE_MAX_ATTEMPTS, window: float = _RATE_WINDOW_SECONDS) -> None:
    """Raise 429 if *key* exceeds *limit* hits in the preceding *window* seconds."""
    now = time.time()
    bucket = _AUTH_RATE_LIMIT.setdefault(key, [])
    bucket[:] = [ts for ts in bucket if now - ts < window]  # purge old entries
    if len(bucket) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many attempts. Please wait {int(window/60)} minute(s) before trying again.",
        )
    bucket.append(now)

# -----------------------------------------------------------------------------
# SlowAPI Limiter instance (used by middleware/security.py)
# -----------------------------------------------------------------------------

# A single Limiter instance is attached to the FastAPI application in
# ``middleware/security.register_security_middleware``.  When SlowAPI is
# available we back it with Redis so that counters are shared across multiple
# processes / pods.  When either SlowAPI or the Redis client is missing the
# stub Limiter defined above becomes a no-op keeping the import graph intact.

limiter: "Limiter" = Limiter(  # type: ignore[name-defined]
    enabled=_HAS_SLOWAPI,
    key_func=get_remote_address,
    storage_uri=_redis_url() if _HAS_SLOWAPI else None,
)



# -----------------------------------------------------------------------------
# CSRF helpers
# -----------------------------------------------------------------------------
CSRF_COOKIE_NAME = "csrftoken"
CSRF_HEADER_NAME = "x-csrftoken"


def generate_csrf_token() -> str:
    """Return a fresh CSRF token (32 random bytes, URL-safe)."""
    return secrets.token_urlsafe(32)


def build_csrf_cookie(token: str) -> tuple[str, str, dict[str, Any]]:
    """Return ``response.set_cookie`` parameters for the CSRF token."""
    return (
        CSRF_COOKIE_NAME,
        token,
        {
            "httponly": False,  # must be readable by JS so header can be set
            "samesite": "lax",
            "secure": not settings.insecure_cookies,
            "max_age": 60 * 60 * 24 * 7,  # 1 week
            "path": "/",
        },
    )


def _extract_csrf(request) -> tuple[Optional[str], Optional[str]]:
    cookie_token: Optional[str] = request.cookies.get(CSRF_COOKIE_NAME)
    header_token: Optional[str] = next(
        (v for k, v in request.headers.items() if k.lower() == CSRF_HEADER_NAME), None
    )
    return cookie_token, header_token


def validate_csrf(request) -> None:
    """Double-submit CSRF defence — compares header & cookie tokens."""
    cookie_token, header_token = _extract_csrf(request)
    if not cookie_token or not header_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF protection failed. Please refresh the page and try again."
        )
    if not hmac.compare_digest(cookie_token, header_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed. Please refresh the page and try again."
        )


# -----------------------------------------------------------------------------
# Password hashing
# -----------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Return a bcrypt (or SHA-256 stub) hash of *password*."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify *plain_password* matches *hashed_password*."""
    return pwd_context.verify(plain_password, hashed_password)


# -----------------------------------------------------------------------------
# JWT helpers
# -----------------------------------------------------------------------------
ACCESS_COOKIE_NAME = "access_token"


def create_access_token(payload: Dict[str, Any], *, expires_delta: Optional[timedelta] = None) -> str:
    """Return a signed JWT (never mutates *payload*)."""
    now = datetime.now(timezone.utc)
    exp_delta = expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    to_encode: Dict[str, Any] = {
        **payload,
        "iat": int(now.timestamp()),
        "exp": int((now + exp_delta).timestamp()),
        "jti": payload.get("jti", secrets.token_urlsafe(32)),
    }
    return jwt.encode(to_encode, settings.effective_secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Return payload if *token* is valid, else raise 401."""
    try:
        return jwt.decode(token, settings.effective_secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def token_sub_identity(payload: Dict[str, Any]) -> int:
    """Extract integer user-ID from ``sub`` claim."""
    try:
        return int(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def build_auth_cookie(token: str) -> tuple[str, str, dict[str, Any]]:
    """Return ``response.set_cookie`` parameters for the auth token."""
    return (
        ACCESS_COOKIE_NAME,
        token,
        {
            "httponly": True,
            "samesite": "lax",
            "secure": not settings.insecure_cookies,
            "max_age": settings.access_token_expire_minutes * 60,
            "path": "/",
        },
    )
