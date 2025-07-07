"""Base provider interface for LLM implementations."""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional, Literal, Sequence
import logging

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Base class for all LLM providers."""

    def __init__(self, **kwargs):
        """Initialize provider with configuration."""
        self.config = kwargs
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
    async def stream(
        self,
        response: Any
    ) -> AsyncIterator[str]:
        """Convert provider response to unified streaming format."""
        pass

    @abstractmethod
    def validate_tools(
        self,
        tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Validate and format tools for this provider."""
        pass

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
        self,
        tool_call_id: str,
        tool_name: str,
        result: str
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
            "supports_json_mode": False
        }