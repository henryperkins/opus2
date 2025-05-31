"""
Security middleware for Phase 2.

Features
--------
• Integrates SlowAPI rate-limiting middleware (limiter is defined in `app.auth.security`).
• Adds secure HTTP headers (HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy).
• Performs CSRF validation on state-changing requests (POST, PUT, PATCH, DELETE).
"""
from __future__ import annotations

from typing import Awaitable, Callable

from fastapi import FastAPI, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.auth import security


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach security headers and enforce CSRF validation."""

    def __init__(self, app: ASGIApp) -> None:  # noqa: D401
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:  # type: ignore[override]
        # CSRF protection: validate token on state-changing verbs
        if request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
            security.validate_csrf(request)

        response = await call_next(request)

        # Add security headers
        response.headers[
            "Strict-Transport-Security"
        ] = "max-age=63072000; includeSubDomains; preload"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"

        return response


def _rate_limit_handler(request: Request, exc: RateLimitExceeded):  # noqa: D401
    """Return 429 JSON when rate limit is exceeded."""
    return Response(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content='{"detail":"Rate limit exceeded"}',
        media_type="application/json",
        headers=exc.headers,  # include Retry-After, etc.
    )


def register_security_middleware(app: FastAPI) -> None:
    """
    Register SlowAPI rate-limiting + security headers middleware on the given app.
    """
    # SlowAPI rate-limiter (uses limiter defined in `app.auth.security`)
    app.state.limiter = security.limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
    app.add_middleware(SlowAPIMiddleware)

    # Security headers & CSRF
    app.add_middleware(SecurityHeadersMiddleware)
