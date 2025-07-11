"""OpenAI provider implementation."""

from typing import Any, AsyncIterator, Dict, List, Optional
import logging
from openai import AsyncOpenAI

from .base import LLMProvider

# Helper for parameter construction
# Shared helpers for parameter construction **and** response parsing
from .utils import (
    build_openai_chat_params,
    extract_content_openai,
    extract_tool_calls_openai,
    format_tool_result_openai,
)

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
            max_retries=0,  # We handle retries at a higher level
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
        **kwargs,
    ) -> Any:
        """Execute OpenAI completion."""

        params = build_openai_chat_params(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            tools=tools,
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls,
            **kwargs,
        )

        logger.debug(
            f"OpenAI request: model={model}, stream={stream}, tools={len(tools or [])}"
        )

        return await self.client.chat.completions.create(**params)

    async def stream(self, response: Any) -> AsyncIterator[str]:
        """Stream response content and tool calls."""
        tool_call_buffer = {}  # Buffer for accumulating tool call deltas

        async for chunk in response:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            # Handle content streaming
            if delta.content:
                yield delta.content

            # Handle tool call streaming
            if delta.tool_calls:
                for tool_call_delta in delta.tool_calls:
                    index = tool_call_delta.index

                    # Initialize tool call buffer for this index if needed
                    if index not in tool_call_buffer:
                        tool_call_buffer[index] = {
                            "id": "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""},
                        }

                    # Accumulate deltas
                    if tool_call_delta.id:
                        tool_call_buffer[index]["id"] += tool_call_delta.id

                    if tool_call_delta.function:
                        if tool_call_delta.function.name:
                            tool_call_buffer[index]["function"][
                                "name"
                            ] += tool_call_delta.function.name
                        if tool_call_delta.function.arguments:
                            tool_call_buffer[index]["function"][
                                "arguments"
                            ] += tool_call_delta.function.arguments

                    # Yield tool call updates as formatted text
                    tool_call = tool_call_buffer[index]
                    if (
                        tool_call["function"]["name"]
                        and tool_call["function"]["arguments"]
                    ):
                        # Only yield when we have complete function info
                        function_name = tool_call["function"]["name"]
                        try:
                            import json

                            args = json.loads(tool_call["function"]["arguments"])
                            tool_text = f"\n[Calling {function_name} with {args}]\n"
                        except json.JSONDecodeError:
                            # Arguments still being streamed
                            tool_text = f"\n[Calling {function_name}...]\n"

                        yield tool_text

            # Handle finish reason for tool calls
            if (
                hasattr(chunk.choices[0], "finish_reason")
                and chunk.choices[0].finish_reason == "tool_calls"
            ):
                if tool_call_buffer:
                    yield "\n[Tool calls completed]\n"

    def extract_content(self, response: Any) -> str:
        """Extract text content from OpenAI response."""
        return extract_content_openai(response)

    def extract_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """Extract tool calls from OpenAI response."""
        return extract_tool_calls_openai(response)

    # ------------------------------------------------------------------
    # Capability descriptor ---------------------------------------------
    # ------------------------------------------------------------------

    def get_model_info(
        self, model: str
    ) -> Dict[str, Any]:  # noqa: D401 – simple description
        """Return capability flags for the given *model*.

        We assume that *all* current OpenAI Chat Completion models support
        the following features:

        • JSON mode via ``response_format={type: 'json_object'}``
        • Parallel tool execution (beta) when ``parallel_tool_calls=True``
        • Streaming token deltas
        """

        base = super().get_model_info(model)
        base.update(
            supports_json_mode=True,
            supports_parallel_tools=True,
            supports_streaming=True,
        )

        # Adjust max context window for well-known models when the value can
        # be inferred locally – this avoids a blocking API call.  Fallback to
        # previous default when the model is unknown.
        context_sizes = {
            "gpt-4o": 128000,
            "gpt-4o-mini": 128000,
            "gpt-4o-max": 128000,
            "gpt-4.1": 128000,
            "gpt-4-turbo": 128000,
            "gpt-4o-preview": 128000,
            "gpt-4": 8192,
            "gpt-4-turbo-preview": 128000,
            "gpt-3.5-turbo": 16385,
        }

        lowered = model.lower()
        for prefix, size in context_sizes.items():
            if lowered.startswith(prefix):
                base["max_tokens"] = size
                break

        return base

    def format_tool_result(
        self,
        tool_call_id: str,
        tool_name: str,
        result: str,
    ) -> Dict[str, Any]:
        """Format tool result for OpenAI."""
        return format_tool_result_openai(tool_call_id, tool_name, result)
