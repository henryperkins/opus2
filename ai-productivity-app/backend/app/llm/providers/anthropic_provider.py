"""Anthropic Claude provider implementation."""

from typing import Any, AsyncIterator, Dict, List, Optional
import logging
from anthropic import AsyncAnthropic

from app.config import settings
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
            # Build comprehensive thinking configuration
            thinking_params = {
                "type": thinking.get("type", "enabled"),
                "budget_tokens": thinking.get("budget_tokens", 16384)
            }
            
            # Add optional thinking parameters if specified
            if "show_thinking" in thinking:
                thinking_params["show_thinking"] = thinking["show_thinking"]
            if "max_budget_tokens" in thinking:
                thinking_params["max_budget_tokens"] = thinking["max_budget_tokens"]
            if "adaptive_budget" in thinking:
                thinking_params["adaptive_budget"] = thinking["adaptive_budget"]
                
            params["thinking"] = thinking_params

        if tools:
            params["tools"] = self.validate_tools(tools)

        params.update(kwargs)
        params = {k: v for k, v in params.items() if v is not None}

        logger.debug(f"Anthropic request: model={model}, stream={stream}, thinking={thinking is not None}")

        return await self.client.messages.create(**params)

    async def stream(self, response: Any) -> AsyncIterator[str]:
        """Stream Anthropic response."""
        thinking_started = False
        
        async for chunk in response:
            # Handle thinking content in streaming
            if hasattr(chunk, "thinking") and chunk.thinking:
                if not thinking_started:
                    yield "<thinking>\n"
                    thinking_started = True
                
                thinking_text = getattr(chunk.thinking, "delta", "") or getattr(chunk.thinking, "text", "")
                if thinking_text:
                    yield thinking_text
            
            # Handle main content deltas
            elif hasattr(chunk, "delta") and hasattr(chunk.delta, "text"):
                if thinking_started:
                    yield "\n</thinking>\n"
                    thinking_started = False
                yield chunk.delta.text
                
            elif hasattr(chunk, "content"):
                if thinking_started:
                    yield "\n</thinking>\n"
                    thinking_started = False
                    
                for block in chunk.content:
                    if hasattr(block, "text"):
                        yield block.text
                    elif hasattr(block, "thinking") and block.thinking:
                        if not thinking_started:
                            yield "<thinking>\n"
                            thinking_started = True
                        thinking_text = getattr(block.thinking, "text", "")
                        if thinking_text:
                            yield thinking_text
                            
            # Older streaming versions populated *chunk.text* directly.
            elif hasattr(chunk, "text"):
                if thinking_started:
                    yield "\n</thinking>\n"
                    thinking_started = False
                yield chunk.text
        
        # Close thinking tag if still open
        if thinking_started:
            yield "\n</thinking>"

    def validate_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert tools to Anthropic format."""
        from .utils import validate_tools as base_validate_tools
        
        # First apply base validation to ensure consistent format
        validated_tools = base_validate_tools(tools)
        
        # Then convert to Anthropic format
        anthropic_tools = []
        for tool in validated_tools:
            if "function" in tool:
                # Convert from OpenAI format to Anthropic format
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
        content_parts = []
        
        # Extract thinking process if present and enabled
        if hasattr(response, "thinking") and response.thinking:
            thinking_content = getattr(response.thinking, "content", "") or getattr(response.thinking, "text", "")
            if thinking_content:
                content_parts.append(f"<thinking>\n{thinking_content}\n</thinking>")
        
        # Extract main response content
        if hasattr(response, "content"):
            if isinstance(response.content, str):
                content_parts.append(response.content)
            elif isinstance(response.content, list):
                for block in response.content:
                    if hasattr(block, "text"):
                        content_parts.append(block.text)
                    elif hasattr(block, "thinking") and block.thinking:
                        # Handle thinking blocks in content
                        thinking_text = getattr(block.thinking, "content", "") or getattr(block.thinking, "text", "")
                        if thinking_text:
                            content_parts.append(f"<thinking>\n{thinking_text}\n</thinking>")
        
        return "\n".join(content_parts) if content_parts else ""

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
        thinking_models = {m.strip().lower() for m in settings.claude_thinking_models.split(',')}
        return model.lower() in thinking_models

    def get_supported_features(self) -> set[str]:
        """Anthropic supports additional features."""
        features = super().get_supported_features()
        features.add("thinking")
        features.add("vision")
        return features