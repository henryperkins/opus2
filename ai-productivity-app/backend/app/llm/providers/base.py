"""Base provider interface for LLM implementations."""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional, Sequence

# Utility helper for tool validation in the canonical OpenAI format.  By
# importing *locally* we avoid a potential circular import when the utils
# module itself tries to import the provider base.
from .utils import validate_tools as _validate_tools
import logging

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Base class for all LLM providers."""

    def __init__(self, *args, **kwargs):
        """Initialize provider with configuration.

        Historical test-suites sometimes instantiated providers with a single
        *dict* positional argument instead of keyword parameters, e.g.::

            AnthropicProvider({"api_key": "key"})

        To remain backward-compatible we accept this calling style and merge
        it with any additional keyword arguments.  When *args* contains more
        than one positional value we raise *TypeError* – there is no sensible
        interpretation for that.
        """

        if len(args) > 1:
            raise TypeError(
                "LLMProvider() accepts at most one positional argument (the config dict)"
            )

        # Merge positional config dict with kwargs – kwargs win on conflict so
        # callers can conveniently override individual keys while passing a
        # pre-assembled base config as the first argument.
        cfg_from_positional = args[0] if args else {}
        if cfg_from_positional and not isinstance(cfg_from_positional, dict):
            raise TypeError(
                "Positional argument to LLMProvider() must be a dict of configuration options"
            )

        merged_cfg = {**cfg_from_positional, **kwargs}

        self.config = merged_cfg
        self.client = None
        self._initialize_client()

    @abstractmethod
    def _initialize_client(self) -> None:
        """Initialize the provider's client."""
        pass

    @abstractmethod
    async def complete(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str | Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """Execute a completion request."""
        pass

    @abstractmethod
    async def stream(self, response: Any) -> AsyncIterator[str]:
        """Convert provider response to unified streaming format."""
        pass

    # NOTE: The majority of providers accept the *OpenAI* tool calling
    # schema.  The shared helper in :pymod:`app.llm.providers.utils`
    # converts *bare* ``{"name": ..., "parameters": ...}`` objects to the
    # fully-qualified format expected by the SDK.  Providers that require a
    # **different** representation (e.g. Anthropic Claude) can still
    # override this method – but everyone else now automatically inherits a
    # robust implementation and we avoid the previous code duplication.

    def validate_tools(
        self, tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:  # noqa: D401 – simple description
        """Return *tools* converted to the canonical OpenAI format.

        This default implementation acts as a thin wrapper around
        :pyfunc:`app.llm.providers.utils.validate_tools`.  It is adequate for
        all providers that understand the OpenAI schema.  Providers with a
        custom format should override the method and *first* delegate to
        ``super().validate_tools`` (or call the helper directly) to benefit
        from the conversion logic.
        """

        # Quick exit for *None* or empty input – helps callers that forward
        # optional arguments without additional checks.
        if not tools:
            return []

        return _validate_tools(tools)

    @abstractmethod
    def extract_content(self, response: Any) -> str:
        """Extract text content from provider response."""
        pass

    @abstractmethod
    def extract_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """Extract tool calls from provider response."""
        pass

    @abstractmethod
    def format_tool_result(
        self, tool_call_id: str, tool_name: str, result: str
    ) -> Dict[str, Any]:
        """Format tool result for provider."""
        pass

    def supports_feature(self, feature: str) -> bool:
        """Check if provider supports a specific feature."""
        return feature in self.get_supported_features()

    def get_supported_features(self) -> set[str]:
        """Return set of supported features."""
        return {"completion", "streaming", "tools"}

    def get_model_info(self, model: str) -> Dict[str, Any]:
        """Get information about a specific model."""
        return {
            "supports_tools": True,
            "supports_streaming": True,
            "max_tokens": 4096,
            "supports_json_mode": False,
        }
