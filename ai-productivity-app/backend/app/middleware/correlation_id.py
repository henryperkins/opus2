"""Correlation ID middleware for request tracing."""

import uuid
from contextvars import ContextVar
from typing import Optional

# Starlette is a transitive dependency of FastAPI, but some lightweight test
# environments ship a *stub* FastAPI package without the full Starlette stack.
# To keep the middleware importable we fall back to a minimal shim when the
# real dependency is absent.

try:
    from starlette.middleware.base import BaseHTTPMiddleware  # type: ignore
    from starlette.requests import Request  # type: ignore

    _HAS_STARLETTE = True
except ModuleNotFoundError:  # pragma: no cover – stub fallback for CI

    _HAS_STARLETTE = False

    class BaseHTTPMiddleware:  # type: ignore
        """No-op replacement providing identical constructor signature."""

        def __init__(self, app, **_kwargs):  # noqa: D401
            self.app = app

        async def __call__(self, scope, receive, send):  # noqa: D401
            await self.app(scope, receive, send)

    class _DummyRequest:  # type: ignore
        headers = {}
        state = type("state", (), {})()

    Request = _DummyRequest  # type: ignore


# Context variable to store request ID across async boundaries
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)

# Header name for correlation ID
REQUEST_ID_HEADER = "X-Request-ID"


def get_request_id() -> Optional[str]:
    """Get current request ID from context."""
    return request_id_var.get()


def set_request_id(request_id: str) -> None:
    """Set request ID in context."""
    request_id_var.set(request_id)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to handle correlation IDs for request tracing."""

    def __init__(
        self, app, header_name: str = REQUEST_ID_HEADER, disabled: bool = False
    ):
        super().__init__(app)
        self.header_name = header_name
        self.disabled = disabled

    async def dispatch(self, request: Request, call_next):
        if self.disabled:
            return await call_next(request)

        # Extract or generate request ID
        request_id = request.headers.get(self.header_name)
        if not request_id:
            request_id = f"req_{uuid.uuid4().hex[:12]}"

        # Set in context for logging and downstream use
        set_request_id(request_id)

        # Add to request state for easy access
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers[self.header_name] = request_id

        return response
