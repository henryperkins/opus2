"""External rendering service client with circuit breaker."""
import os
import httpx
from typing import Dict, Any, Optional
# ---------------------------------------------------------------------------
# Tenacity is optional in the constrained execution sandbox.  Provide a *very
# small* stub when the real package is unavailable so that the rendering
# service client can still be imported and unit-tested (fallback path only).
# ---------------------------------------------------------------------------

try:
    from tenacity import (  # type: ignore
        retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    )

except ModuleNotFoundError:  # pragma: no cover – stub fallback for CI

    import functools

    def retry(*dargs, **dkwargs):  # noqa: D401 – decorator replacement
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)

            return wrapper

        # If used without args (@retry)
        if dargs and callable(dargs[0]):
            return decorator(dargs[0])

        return decorator

    def stop_after_attempt(_n):  # noqa: D401
        return None

    def wait_exponential(**_):  # noqa: D401
        return None

    def retry_if_exception_type(_):  # noqa: D401
        return None
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Simple circuit breaker implementation."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half-open

    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == 'open':
            if self._should_attempt_reset():
                self.state = 'half-open'
            else:
                raise Exception("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if we should try to reset the circuit."""
        return (
            self.last_failure_time and
            datetime.now() - self.last_failure_time >
            timedelta(seconds=self.recovery_timeout)
        )

    def _on_success(self):
        """Reset circuit breaker on success."""
        self.failure_count = 0
        self.state = 'closed'
        self.last_failure_time = None

    def _on_failure(self):
        """Record failure and potentially open circuit."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = 'open'
            logger.warning(
                "Circuit breaker opened after %d failures",
                self.failure_count
            )


class RenderingServiceClient:
    """Client for external rendering microservice."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv("RENDER_SERVICE_URL", "")
        self.enabled = bool(self.base_url)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=30,
            expected_exception=httpx.HTTPError
        )
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=5.0,
            limits=httpx.Limits(max_keepalive_connections=5)
        ) if self.enabled else None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.TransportError),
        reraise=True
    )
    async def _make_request(
        self, method: str, path: str, **kwargs
    ) -> httpx.Response:
        """Make HTTP request with retries."""
        if not self.client:
            raise RuntimeError("Rendering service not configured")

        return await self.client.request(method, path, **kwargs)

    async def render_markdown(
        self,
        content: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Render markdown content."""
        if not self.enabled:
            return self._fallback_markdown_render(content, options)

        try:
            result = await self.circuit_breaker.call(
                self._make_request,
                "POST",
                "/render/markdown",
                json={
                    "content": content,
                    "options": options or {}
                }
            )
            result.raise_for_status()
            return result.json()
        except Exception as e:
            logger.warning(f"Rendering service failed, using fallback: {e}")
            return self._fallback_markdown_render(content, options)

    async def render_code(
        self,
        code: str,
        language: str,
        theme: str = "github"
    ) -> Dict[str, Any]:
        """Render code with syntax highlighting."""
        if not self.enabled:
            return self._fallback_code_render(code, language, theme)

        try:
            result = await self.circuit_breaker.call(
                self._make_request,
                "POST",
                "/render/code",
                json={
                    "code": code,
                    "language": language,
                    "theme": theme
                }
            )
            result.raise_for_status()
            return result.json()
        except Exception as e:
            logger.warning(f"Code rendering failed, using fallback: {e}")
            return self._fallback_code_render(code, language, theme)

    async def render_math(
        self,
        expression: str,
        renderer: str = "katex"
    ) -> Dict[str, Any]:
        """Render mathematical expressions."""
        if not self.enabled:
            return self._fallback_math_render(expression, renderer)

        try:
            result = await self.circuit_breaker.call(
                self._make_request,
                "POST",
                "/render/math",
                json={
                    "expression": expression,
                    "renderer": renderer
                }
            )
            result.raise_for_status()
            return result.json()
        except Exception as e:
            logger.warning(f"Math rendering failed, using fallback: {e}")
            return self._fallback_math_render(expression, renderer)

    async def render_diagram(
        self,
        code: str,
        diagram_type: str = "mermaid"
    ) -> Dict[str, Any]:
        """Render diagrams."""
        if not self.enabled:
            return self._fallback_diagram_render(code, diagram_type)

        try:
            result = await self.circuit_breaker.call(
                self._make_request,
                "POST",
                "/render/diagram",
                json={
                    "code": code,
                    "type": diagram_type
                }
            )
            result.raise_for_status()
            return result.json()
        except Exception as e:
            logger.warning(f"Diagram rendering failed, using fallback: {e}")
            return self._fallback_diagram_render(code, diagram_type)

    # Fallback implementations
    def _fallback_markdown_render(
        self, content: str, options: Optional[Dict]
    ) -> Dict[str, Any]:
        """Simple markdown fallback."""
        try:
            import markdown
            html = markdown.markdown(
                content,
                extensions=['tables', 'fenced_code', 'codehilite']
            )
            return {
                "html": html,
                "format": "markdown",
                "fallback": True
            }
        except ImportError:
            # If markdown is not available, return plain text
            return {
                "html": f"<pre>{content}</pre>",
                "format": "text",
                "fallback": True
            }

    def _fallback_code_render(
        self, code: str, language: str, theme: str
    ) -> Dict[str, Any]:
        """Simple code fallback with HTML escaping."""
        import html
        escaped = html.escape(code)
        return {
            "html": f'<pre><code class="language-{language}">'
                    f'{escaped}</code></pre>',
            "language": language,
            "theme": theme,
            "fallback": True
        }

    def _fallback_math_render(
        self, expression: str, renderer: str
    ) -> Dict[str, Any]:
        """Math expression fallback."""
        import html
        escaped = html.escape(expression)
        return {
            "html": f'<span class="math-{renderer}">{escaped}</span>',
            "renderer": renderer,
            "fallback": True
        }

    def _fallback_diagram_render(
        self, code: str, diagram_type: str
    ) -> Dict[str, Any]:
        """Diagram fallback."""
        return {
            "svg": '<svg><text>Diagram rendering unavailable</text></svg>',
            "type": diagram_type,
            "fallback": True
        }
