# backend/app/services/rendering_client.py
"""External rendering micro-service client with retry + circuit-breaker."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

import logging

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Circuit-Breaker
# --------------------------------------------------------------------------- #


class CircuitBreaker:
    """Thread-safe, async-compatible circuit breaker."""

    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type[Exception] = Exception,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self._fail_count = 0
        self._last_failure: datetime | None = None
        self._state = "closed"
        self._lock = asyncio.Lock()

    async def run(self, func: Callable, *args, **kwargs):  # noqa: D401
        """Execute *func* with CB protection."""
        async with self._lock:
            if self._state == "open" and not self._cool_off_passed():
                raise RuntimeError("Circuit-breaker is OPEN")

            if self._state == "open":
                self._state = "half-open"

        try:
            result = await func(*args, **kwargs)
        except self.expected_exception as exc:
            await self._record_failure()
            raise exc
        else:
            await self._record_success()
            return result

    # ---------------- Internal helpers ---------------- #

    async def _record_success(self) -> None:
        async with self._lock:
            self._state, self._fail_count, self._last_failure = "closed", 0, None

    async def _record_failure(self) -> None:
        async with self._lock:
            self._fail_count += 1
            self._last_failure = datetime.now()
            if self._fail_count >= self.failure_threshold:
                self._state = "open"
                logger.warning("Circuit-breaker OPEN (failures=%s)", self._fail_count)

    def _cool_off_passed(self) -> bool:
        if not self._last_failure:
            return True
        return (datetime.now() - self._last_failure) > timedelta(
            seconds=self.recovery_timeout
        )


# --------------------------------------------------------------------------- #
# Rendering-service client
# --------------------------------------------------------------------------- #

_DEFAULT_TIMEOUT = float(os.getenv("RENDER_TIMEOUT", "5"))
# Connection pool = keepalive N (env override)
_LIMITS = httpx.Limits(max_keepalive_connections=int(os.getenv("RENDER_CONN", "10")))

# One global client instance
_http_client: httpx.AsyncClient | None = None


def _get_client(base_url: str) -> httpx.AsyncClient:
    global _http_client  # noqa: PLW0603

    if _http_client is None:
        _http_client = httpx.AsyncClient(base_url=base_url, timeout=_DEFAULT_TIMEOUT, limits=_LIMITS)
    return _http_client


class RenderingServiceClient:
    """High-level helper with retry + CB + graceful fallbacks."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        breaker: CircuitBreaker | None = None,
    ) -> None:
        self.base_url = base_url or os.getenv("RENDER_SERVICE_URL", "")
        self.enabled = bool(self.base_url)
        self._breaker = breaker or CircuitBreaker(
            failure_threshold=int(os.getenv("RENDER_CB_THRESHOLD", "3")),
            recovery_timeout=int(os.getenv("RENDER_CB_TIMEOUT", "30")),
            expected_exception=httpx.HTTPError,
        )

    # ------------ Internal HTTP --------------- #
    @retry(
        stop=stop_after_attempt(int(os.getenv("RENDER_RETRIES", "3"))),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.TransportError),
        reraise=True,
    )
    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        if not self.enabled:
            raise RuntimeError("Rendering service disabled")
        client = _get_client(self.base_url)
        response: httpx.Response = await client.request(method, path, **kwargs)

        # Treat 5xx as failures for the circuit-breaker.
        if response.status_code >= 500:
            raise httpx.HTTPStatusError(
                f"Server error {response.status_code}",
                request=response.request,
                response=response,
            )
        return response

    # ------------ Public rendering helpers ------------- #
    async def render_markdown(self, content: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.enabled:
            return self._fallback_markdown(content, options)

        try:
            resp = await self._breaker.run(
                self._request,
                "POST",
                "/render/markdown",
                json={"content": content, "options": options or {}},
            )
            return resp.json()
        except Exception as exc:
            logger.warning("Markdown render failed – fallback (%s)", exc)
            return self._fallback_markdown(content, options)

    async def render_code(self, code: str, language: str, theme: str = "github") -> Dict[str, Any]:
        if not self.enabled:
            return self._fallback_code(code, language, theme)
        try:
            resp = await self._breaker.run(
                self._request,
                "POST",
                "/render/code",
                json={"code": code, "language": language, "theme": theme},
            )
            return resp.json()
        except Exception as exc:
            logger.warning("Code render failed – fallback (%s)", exc)
            return self._fallback_code(code, language, theme)

    async def render_math(self, expression: str, renderer: str = "katex") -> Dict[str, Any]:
        if not self.enabled:
            return self._fallback_math(expression, renderer)
        try:
            resp = await self._breaker.run(
                self._request,
                "POST",
                "/render/math",
                json={"expression": expression, "renderer": renderer},
            )
            return resp.json()
        except Exception as exc:
            logger.warning("Math render failed – fallback (%s)", exc)
            return self._fallback_math(expression, renderer)

    async def render_diagram(self, code: str, diagram_type: str = "mermaid") -> Dict[str, Any]:
        if not self.enabled:
            return self._fallback_diagram(code, diagram_type)
        try:
            resp = await self._breaker.run(
                self._request,
                "POST",
                "/render/diagram",
                json={"code": code, "type": diagram_type},
            )
            return resp.json()
        except Exception as exc:
            logger.warning("Diagram render failed – fallback (%s)", exc)
            return self._fallback_diagram(code, diagram_type)

    # ---------------- Fallbacks ---------------- #
    @staticmethod
    def _fallback_markdown(content: str, options: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            import markdown

            html = markdown.markdown(content, extensions=["tables", "fenced_code", "codehilite"])
            return {"html": html, "format": "markdown", "fallback": True}
        except ImportError:
            import html as _html

            return {"html": f"<pre>{_html.escape(content)}</pre>", "format": "text", "fallback": True}

    @staticmethod
    def _fallback_code(code: str, language: str, theme: str) -> Dict[str, Any]:
        import html as _html

        escaped = _html.escape(code)
        return {
            "html": f'<pre><code class="language-{language}">{escaped}</code></pre>',
            "language": language,
            "theme": theme,
            "fallback": True,
        }

    @staticmethod
    def _fallback_math(expression: str, renderer: str) -> Dict[str, Any]:
        import html as _html

        escaped = _html.escape(expression)
        return {"html": f'<span class="math-{renderer}">{escaped}</span>', "renderer": renderer, "fallback": True}

    @staticmethod
    def _fallback_diagram(code: str, diagram_type: str) -> Dict[str, Any]:
        return {"svg": '<svg><text>Diagram rendering unavailable</text></svg>', "type": diagram_type, "fallback": True}


# --------------------------------------------------------------------------- #
# Graceful shutdown helper (FastAPI lifespan)
# --------------------------------------------------------------------------- #
async def close_rendering_client() -> None:
    global _http_client  # noqa: PLW0603
    if _http_client:
        await _http_client.aclose()
        _http_client = None
