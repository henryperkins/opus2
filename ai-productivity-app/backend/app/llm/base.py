"""Common interface for Large-Language-Model providers.

This abstraction allows the rest of the code-base to stay provider-agnostic.  A
concrete implementation only needs to override the *generate* and *stream*
methods and can optionally hook into the *telemetry* helpers for tracing /
metrics.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Any, List


class BaseLLMProvider(ABC):
    """Abstract base-class every LLM provider implementation must inherit from."""

    name: str = "base"

    # ---------------------------------------------------------------------
    # Concrete providers MUST implement *generate* and *stream*.
    # ---------------------------------------------------------------------

    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> str:  # noqa: D401
        """Return a single completion for *prompt*.

        Implementations should honour common arguments such as ``temperature``
        or ``max_tokens`` if supplied via **kwargs.
        """

    @abstractmethod
    async def stream(self, prompt: str, **kwargs: Any) -> AsyncIterator[str]:  # noqa: D401,E501
        """Yield completion tokens as they are produced by the provider."""

    # ------------------------------------------------------------------
    # Optional telemetry hooks – default implementations are no-ops.  Backends
    # can override these to emit metrics / tracing spans.
    # ------------------------------------------------------------------

    def on_request_start(self, prompt: str, params: Dict[str, Any] | None = None) -> None:  # noqa: D401,E501
        """Called right before a provider request is issued."""

    def on_request_end(self, prompt: str, response: str | List[str]) -> None:  # noqa: D401
        """Called when the provider returns a response without error."""

    def on_request_error(self, prompt: str, exc: Exception) -> None:  # noqa: D401
        """Called when the provider raises an exception."""
