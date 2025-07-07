"""OpenAI provider implementation."""

from typing import Any, AsyncIterator, Dict, List, Optional
import logging
from openai import AsyncOpenAI, RateLimitError, APITimeoutError

from .base import LLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI API provider implementation."""

    def _initialize_client(self) -> None:
        """Initialize OpenAI client."""
        api_key = self.config.get("api_key")
        if not api_key:
            raise ValueError("OpenAI API key is required")

        self.client = AsyncOpenAI(
            api_key=api_key,
            timeout=self.config.get("timeout", 300),
            max_retries=0  # We handle retries at a higher level
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
        parallel_tool_calls: bool = True,
        **kwargs
    ) -> Any:
        """Execute OpenAI completion."""

        # Build request parameters
        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream
        }

        if max_tokens:
            params["max_tokens"] = max_tokens

        if tools:
            params["tools"] = self.validate_tools(tools)
            if tool_choice:
                params["tool_choice"] = tool_choice
            params["parallel_tool_calls"] = parallel_tool_calls

        # Add any additional parameters
        params.update(kwargs)

        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        logger.debug(f"OpenAI request: model={model}, stream={stream}, tools={len(tools or [])}")

        return await self.client.chat.completions.create(**params)

    async def stream(self, response: Any) -> AsyncIterator[str]:
        """Stream response content."""
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def validate_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate tools are in OpenAI format."""
        validated = []
        for tool in tools:
            if "function" in tool:
                # Already in correct format
                validated.append(tool)
            else:
                # Convert from legacy format
                validated.append({
                    "type": "function",
                    "function": {
                        "name": tool.get("name"),
                        "description": tool.get("description"),
                        "parameters": tool.get("parameters", {})
                    }
                })
        return validated

    def extract_content(self, response: Any) -> str:
        """Extract text content from OpenAI response."""
        if hasattr(response, "choices") and response.choices:
            return response.choices[0].message.content or ""
        return ""

    def extract_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """Extract tool calls from OpenAI response."""
        tool_calls = []

        if hasattr(response, "choices") and response.choices:
            message = response.choices[0].message
            if hasattr(message, "tool_calls") and message.tool_calls:
                for call in message.tool_calls:
                    tool_calls.append({
                        "id": call.id,
                        "name": call.function.name,
                        "arguments": call.function.arguments
                    })

        return tool_calls

    def format_tool_result(
        self,
        tool_call_id: str,
        tool_name: str,
        result: str
    ) -> Dict[str, Any]:
        """Format tool result for OpenAI."""
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": result
        }