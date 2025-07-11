"""Minimal stub of the ``anthropic`` SDK used in tests.

The real *anthropic* package is not available in the execution environment.
Only a handful of symbols that the code-base imports are provided – enough
for import statements and basic mocking in unit tests to work.

If the real library is installed at runtime this stub will be shadowed by the
actual implementation thanks to Python's normal import-resolution order.
"""

from __future__ import annotations

import types
from typing import Any, Dict

__all__ = [
    "AsyncAnthropic",
    "Anthropic",
    "AnthropicBedrock",
    "AnthropicVertex",
]


class _MessageManager:
    """Very small placeholder that mimics the ``messages`` namespace."""

    async def create(self, *args: Any, **kwargs: Any) -> Any:  # noqa: D401
        """Async no-op – returns an empty ``types.SimpleNamespace`` object."""

        return types.SimpleNamespace()


class _BaseAnthropicClient:
    """Base functionality shared by the fake sync/async clients."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401
        # Expose a minimal ``messages`` helper so that
        # ``client.messages.create(...)`` does not explode.
        self.messages = _MessageManager()


class AsyncAnthropic(_BaseAnthropicClient):
    """Stub for the most commonly imported SDK class."""


# The synchronous variant is rarely used but include for completeness
class Anthropic(_BaseAnthropicClient):
    pass


# Additional aliases referenced in the markdown docs – map to the same stub.
AnthropicBedrock = Anthropic
AnthropicVertex = Anthropic
