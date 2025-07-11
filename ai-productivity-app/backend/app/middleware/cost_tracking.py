"""Cost tracking middleware for automatic LLM usage monitoring."""

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint

from app.services.cost_tracking import CostTrackingService, UsageEvent
from app.database import SessionLocal
from app.models.user import User

logger = logging.getLogger(__name__)


class CostTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically track LLM usage and costs across the application."""

    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
        self._excluded_paths = {
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/favicon.ico",
            "/static",
        }

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process request and track LLM usage if applicable."""

        if not self.enabled:
            return await call_next(request)

        # Skip tracking for excluded paths
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self._excluded_paths):
            return await call_next(request)

        # Initialize tracking context
        start_time = time.time()
        tracking_context = {
            "path": path,
            "method": request.method,
            "user_id": None,
            "session_id": None,
            "feature": self._extract_feature_from_path(path),
            "start_time": start_time,
            "request_id": self._generate_request_id(request),
        }

        # Extract user information if available
        user_id = await self._extract_user_id(request)
        if user_id:
            tracking_context["user_id"] = user_id

        # Extract session information if available
        session_id = await self._extract_session_id(request)
        if session_id:
            tracking_context["session_id"] = session_id

        # Store tracking context in request state
        request.state.cost_tracking = tracking_context

        try:
            response = await call_next(request)

            # Record successful request metrics
            await self._record_request_metrics(
                request, response, tracking_context, success=True
            )

            return response

        except Exception as e:
            # Record failed request metrics
            await self._record_request_metrics(
                request, None, tracking_context, success=False, error=str(e)
            )
            raise

    def _extract_feature_from_path(self, path: str) -> str:
        """Extract feature name from request path."""
        # Map API paths to features
        feature_map = {
            "/api/chat": "chat",
            "/api/search": "search",
            "/api/copilot": "copilot",
            "/api/code": "code_analysis",
            "/api/projects": "project_management",
            "/api/knowledge": "knowledge_base",
            "/api/analytics": "analytics",
            "/api/prompt": "prompt_templates",
            "/ws/sessions": "websocket_chat",
        }

        for path_prefix, feature in feature_map.items():
            if path.startswith(path_prefix):
                return feature

        return "unknown"

    async def _extract_user_id(self, request: Request) -> Optional[int]:
        """Extract user ID from request context."""
        try:
            # Check if user is attached to request (from auth middleware)
            if hasattr(request.state, "user"):
                user = request.state.user
                if hasattr(user, "id"):
                    return user.id

            # Check for user ID in headers (for API clients)
            user_id_header = request.headers.get("X-User-ID")
            if user_id_header:
                return int(user_id_header)

            # Check for user ID in query parameters
            user_id_param = request.query_params.get("user_id")
            if user_id_param:
                return int(user_id_param)

        except (ValueError, AttributeError) as e:
            logger.debug(f"Failed to extract user ID: {e}")

        return None

    async def _extract_session_id(self, request: Request) -> Optional[str]:
        """Extract session ID from request context."""
        try:
            # Check for session ID in headers
            session_id_header = request.headers.get("X-Session-ID")
            if session_id_header:
                return session_id_header

            # Check for session ID in query parameters
            session_id_param = request.query_params.get("session_id")
            if session_id_param:
                return session_id_param

            # Extract from WebSocket path
            path = request.url.path
            if "/ws/sessions/" in path:
                return path.split("/ws/sessions/")[1].split("/")[0]

        except (ValueError, AttributeError) as e:
            logger.debug(f"Failed to extract session ID: {e}")

        return None

    def _generate_request_id(self, request: Request) -> str:
        """Generate a unique request ID for tracking."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"req_{timestamp}_{hash(request.url.path + str(time.time()))}"

    async def _record_request_metrics(
        self,
        request: Request,
        response: Optional[Response],
        tracking_context: Dict[str, Any],
        success: bool = True,
        error: Optional[str] = None,
    ):
        """Record request metrics for cost tracking."""
        try:
            # Only record metrics for LLM-related endpoints
            if tracking_context["feature"] in ["unknown", "analytics"]:
                return

            # Calculate request duration
            duration_ms = (time.time() - tracking_context["start_time"]) * 1000

            # Check if this request involved LLM usage
            llm_usage = await self._detect_llm_usage(request, response)
            if not llm_usage:
                return

            # Create usage event for request-level tracking
            db = SessionLocal()
            cost_tracking_service = CostTrackingService(db)

            try:
                # Extract model information if available
                model_info = await self._extract_model_info(request, response)

                # Create a request-level usage event
                usage_event = UsageEvent(
                    model_id=model_info.get("model_id", "unknown"),
                    provider=model_info.get("provider", "unknown"),
                    user_id=tracking_context["user_id"],
                    session_id=tracking_context["session_id"],
                    input_tokens=model_info.get("input_tokens", 0),
                    output_tokens=model_info.get("output_tokens", 0),
                    response_time_ms=duration_ms,
                    success=success,
                    feature=tracking_context["feature"],
                    metadata={
                        "request_id": tracking_context["request_id"],
                        "path": tracking_context["path"],
                        "method": tracking_context["method"],
                        "status_code": response.status_code if response else None,
                        "error": error,
                        "user_agent": request.headers.get("user-agent"),
                    },
                    timestamp=datetime.now(timezone.utc),
                )

                # Record the usage
                await cost_tracking_service.record_usage(usage_event)

                logger.debug(
                    f"Recorded request metrics: {tracking_context['feature']} - {duration_ms:.2f}ms - "
                    f"User: {tracking_context['user_id']} - Success: {success}"
                )

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Failed to record request metrics: {e}", exc_info=True)

    async def _detect_llm_usage(
        self, request: Request, response: Optional[Response]
    ) -> bool:
        """Detect if the request involved LLM usage."""
        # Check request path for LLM-related endpoints
        llm_paths = [
            "/api/chat",
            "/api/copilot",
            "/api/code/analyze",
            "/api/search/semantic",
            "/api/prompt/execute",
            "/ws/sessions",
        ]

        path = request.url.path
        if any(path.startswith(llm_path) for llm_path in llm_paths):
            return True

        # Check request body for LLM-related content
        if hasattr(request.state, "body"):
            body = request.state.body
            if isinstance(body, dict):
                # Look for model-related fields
                if any(
                    key in body for key in ["model", "model_id", "prompt", "messages"]
                ):
                    return True

        # Check response headers for LLM usage indicators
        if response and hasattr(response, "headers"):
            if "X-LLM-Usage" in response.headers:
                return True

        return False

    async def _extract_model_info(
        self, request: Request, response: Optional[Response]
    ) -> Dict[str, Any]:
        """Extract model information from request/response."""
        model_info = {
            "model_id": "unknown",
            "provider": "unknown",
            "input_tokens": 0,
            "output_tokens": 0,
        }

        try:
            # Check request body for model information
            if hasattr(request.state, "body"):
                body = request.state.body
                if isinstance(body, dict):
                    model_info["model_id"] = body.get(
                        "model", body.get("model_id", "unknown")
                    )
                    model_info["provider"] = body.get("provider", "unknown")

            # Check response headers for token usage
            if response and hasattr(response, "headers"):
                headers = response.headers
                if "X-Input-Tokens" in headers:
                    model_info["input_tokens"] = int(headers["X-Input-Tokens"])
                if "X-Output-Tokens" in headers:
                    model_info["output_tokens"] = int(headers["X-Output-Tokens"])
                if "X-Model-ID" in headers:
                    model_info["model_id"] = headers["X-Model-ID"]
                if "X-Provider" in headers:
                    model_info["provider"] = headers["X-Provider"]

            # Check response body for usage information
            if response and hasattr(response, "body"):
                # This would need to be implemented based on actual response formats
                pass

        except (ValueError, AttributeError) as e:
            logger.debug(f"Failed to extract model info: {e}")

        return model_info


class CostTrackingContextMiddleware(BaseHTTPMiddleware):
    """Lightweight middleware to inject cost tracking context into requests."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Inject cost tracking context into request state."""

        # Initialize cost tracking context
        request.state.cost_tracking_context = {
            "enabled": True,
            "track_usage": True,
            "user_id": None,
            "session_id": None,
            "feature": None,
            "metadata": {},
        }

        # Extract user and session information
        user_id = await self._extract_user_id(request)
        session_id = await self._extract_session_id(request)

        if user_id:
            request.state.cost_tracking_context["user_id"] = user_id
        if session_id:
            request.state.cost_tracking_context["session_id"] = session_id

        # Set feature based on path
        feature = self._extract_feature_from_path(request.url.path)
        request.state.cost_tracking_context["feature"] = feature

        response = await call_next(request)

        return response

    async def _extract_user_id(self, request: Request) -> Optional[int]:
        """Extract user ID from request."""
        try:
            if hasattr(request.state, "user") and hasattr(request.state.user, "id"):
                return request.state.user.id

            user_id_header = request.headers.get("X-User-ID")
            if user_id_header:
                return int(user_id_header)

        except (ValueError, AttributeError):
            pass

        return None

    async def _extract_session_id(self, request: Request) -> Optional[str]:
        """Extract session ID from request."""
        try:
            session_id_header = request.headers.get("X-Session-ID")
            if session_id_header:
                return session_id_header

            # Extract from WebSocket path
            path = request.url.path
            if "/ws/sessions/" in path:
                return path.split("/ws/sessions/")[1].split("/")[0]

        except (ValueError, AttributeError):
            pass

        return None

    def _extract_feature_from_path(self, path: str) -> str:
        """Extract feature name from request path."""
        feature_map = {
            "/api/chat": "chat",
            "/api/search": "search",
            "/api/copilot": "copilot",
            "/api/code": "code_analysis",
            "/api/projects": "project_management",
            "/api/knowledge": "knowledge_base",
            "/api/prompt": "prompt_templates",
            "/ws/sessions": "websocket_chat",
        }

        for path_prefix, feature in feature_map.items():
            if path.startswith(path_prefix):
                return feature

        return "unknown"


def get_cost_tracking_context(request: Request) -> Dict[str, Any]:
    """Helper function to get cost tracking context from request state."""
    if hasattr(request.state, "cost_tracking_context"):
        return request.state.cost_tracking_context

    return {
        "enabled": False,
        "track_usage": False,
        "user_id": None,
        "session_id": None,
        "feature": None,
        "metadata": {},
    }


def set_cost_tracking_context(request: Request, **kwargs):
    """Helper function to update cost tracking context."""
    if hasattr(request.state, "cost_tracking_context"):
        request.state.cost_tracking_context.update(kwargs)
    else:
        request.state.cost_tracking_context = {
            "enabled": True,
            "track_usage": True,
            "user_id": None,
            "session_id": None,
            "feature": None,
            "metadata": {},
            **kwargs,
        }
