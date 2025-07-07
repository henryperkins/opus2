"""Anthropic Claude provider implementation."""

from typing import Any, AsyncIterator, Dict, List, Optional
import logging
from anthropic import AsyncAnthropic

from .base import LLMProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider implementation."""

    def _initialize_client(self) -> None:
        """Initialize Anthropic client."""
        api_key = self.config.get("api_key")
        if not api_key:
            raise ValueError("Anthropic API key is required")

        self.client = AsyncAnthropic(
            api_key=api_key,
            timeout=self.config.get("timeout", 300),
            max_retries=0
        )

    async def complete(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str | Dict[str, Any]] = None,
        thinking: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """Execute Anthropic completion."""

        # Extract system message
        system_message = None
        filtered_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                filtered_messages.append(msg)

        # Build request
        params = {
            "model": model,
            "messages": filtered_messages,
            "max_tokens": max_tokens or 1024,
            "temperature": temperature,
            "stream": stream
        }

        if system_message:
            params["system"] = system_message

        if thinking and self._supports_thinking(model):
            params["thinking"] = thinking

        if tools:
            params["tools"] = self.validate_tools(tools)

        params.update(kwargs)
        params = {k: v for k, v in params.items() if v is not None}

        logger.debug(f"Anthropic request: model={model}, stream={stream}, thinking={thinking is not None}")

        return await self.client.messages.create(**params)

    async def stream(self, response: Any) -> AsyncIterator[str]:
        """Stream Anthropic response."""
        async for chunk in response:
            if hasattr(chunk, "delta") and hasattr(chunk.delta, "text"):
                yield chunk.delta.text
            elif hasattr(chunk, "content"):
                for block in chunk.content:
                    if hasattr(block, "text"):
                        yield block.text

    def validate_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert tools to Anthropic format."""
        anthropic_tools = []

        for tool in tools:
            if "function" in tool:
                # Convert from OpenAI format
                func = tool["function"]
                anthropic_tools.append({
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {})
                })
            else:
                # Already in Anthropic format
                anthropic_tools.append(tool)

        return anthropic_tools

    def extract_content(self, response: Any) -> str:
        """Extract content from Anthropic response."""
        if hasattr(response, "content"):
            if isinstance(response.content, str):
                return response.content
            elif isinstance(response.content, list):
                text_parts = []
                for block in response.content:
                    if hasattr(block, "text"):
                        text_parts.append(block.text)
                return "\n".join(text_parts)
        return ""

    def extract_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """Extract tool calls from Anthropic response."""
        tool_calls = []

        if hasattr(response, "content") and isinstance(response.content, list):
            for block in response.content:
                if getattr(block, "type", None) == "tool_use":
                    tool_calls.append({
                        "id": block.id,
                        "name": block.name,
                        "arguments": block.input
                    })

        return tool_calls

    def format_tool_result(
        self,
        tool_call_id: str,
        tool_name: str,
        result: str
    ) -> Dict[str, Any]:
        """Format tool result for Anthropic."""
        return {
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": tool_call_id,
                "content": result
            }]
        }

    def _supports_thinking(self, model: str) -> bool:
        """Check if model supports extended thinking."""
        thinking_models = {
            "claude-opus-4-20250514",
            "claude-sonnet-4-20250514",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-sonnet-latest"
        }
        return model.lower() in {m.lower() for m in thinking_models}

    def get_supported_features(self) -> set[str]:
        """Anthropic supports additional features."""
        features = super().get_supported_features()
        features.add("thinking")
        features.add("vision")
        return features