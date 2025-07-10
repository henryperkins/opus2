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

        params = build_openai_chat_params(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            tools=tools,
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls,
            **kwargs
        )

        logger.debug(f"OpenAI request: model={model}, stream={stream}, tools={len(tools or [])}")

        return await self.client.chat.completions.create(**params)

    async def stream(self, response: Any) -> AsyncIterator[str]:
        """Stream response content."""
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def extract_content(self, response: Any) -> str:
        """Extract text content from OpenAI response."""
        return extract_content_openai(response)

    def extract_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """Extract tool calls from OpenAI response."""
        return extract_tool_calls_openai(response)

    def format_tool_result(
        self,
        tool_call_id: str,
        tool_name: str,
        result: str,
    ) -> Dict[str, Any]:
        """Format tool result for OpenAI."""
        return format_tool_result_openai(tool_call_id, tool_name, result)