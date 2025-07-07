"""Azure OpenAI provider implementation."""

from typing import Any, AsyncIterator, Dict, List, Optional
import logging
from openai import AsyncAzureOpenAI

from .base import LLMProvider
from .openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI provider implementation."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.use_responses_api = kwargs.get("use_responses_api", False)
        self.api_version = kwargs.get("api_version", "2025-04-01-preview")

    def _initialize_client(self) -> None:
        """Initialize Azure OpenAI client."""
        endpoint = self.config.get("endpoint")
        if not endpoint:
            raise ValueError("Azure OpenAI endpoint is required")

        auth_method = self.config.get("auth_method", "api_key")

        client_kwargs = {
            "azure_endpoint": endpoint,
            "api_version": self.api_version,
            "timeout": self.config.get("timeout", 300),
            "max_retries": 0
        }

        if auth_method == "api_key":
            api_key = self.config.get("api_key")
            if not api_key:
                raise ValueError("Azure OpenAI API key is required")
            client_kwargs["api_key"] = api_key
        else:
            # Entra ID authentication
            token_provider = self.config.get("token_provider")
            if not token_provider:
                raise ValueError("Token provider required for Entra ID auth")
            client_kwargs["azure_ad_token_provider"] = token_provider

        self.client = AsyncAzureOpenAI(**client_kwargs)

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
        reasoning: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """Execute Azure OpenAI completion."""

        if self.use_responses_api:
            return await self._complete_responses_api(
                messages, model, temperature, max_tokens, stream,
                tools, tool_choice, reasoning, **kwargs
            )
        else:
            return await self._complete_chat_api(
                messages, model, temperature, max_tokens, stream,
                tools, tool_choice, parallel_tool_calls, **kwargs
            )

    async def _complete_chat_api(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        temperature: float,
        max_tokens: Optional[int],
        stream: bool,
        tools: Optional[List[Dict[str, Any]]],
        tool_choice: Optional[str | Dict[str, Any]],
        parallel_tool_calls: bool,
        **kwargs
    ) -> Any:
        """Use standard Chat Completions API."""
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

        params.update(kwargs)
        params = {k: v for k, v in params.items() if v is not None}

        return await self.client.chat.completions.create(**params)

    async def _complete_responses_api(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        temperature: float,
        max_tokens: Optional[int],
        stream: bool,
        tools: Optional[List[Dict[str, Any]]],
        tool_choice: Optional[str | Dict[str, Any]],
        reasoning: Optional[Dict[str, Any]],
        **kwargs
    ) -> Any:
        """Use Azure Responses API."""

        # Convert messages to Responses API format
        input_messages = []
        instructions = None

        for msg in messages:
            if msg["role"] == "system":
                if instructions:
                    instructions += "\n\n" + msg["content"]
                else:
                    instructions = msg["content"]
            else:
                input_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                    "type": "message"
                })

        params = {
            "model": model,
            "input": input_messages,
            "temperature": temperature,
            "stream": stream
        }

        if instructions:
            params["instructions"] = instructions

        if max_tokens:
            params["max_output_tokens"] = max_tokens

        if tools:
            params["tools"] = self.validate_tools(tools)
            if tool_choice:
                params["tool_choice"] = tool_choice

        if reasoning:
            params["reasoning"] = reasoning

        params.update(kwargs)
        params = {k: v for k, v in params.items() if v is not None}

        return await self.client.responses.create(**params)

    async def stream(self, response: Any) -> AsyncIterator[str]:
        """Stream response content."""
        if self.use_responses_api:
            async for chunk in response:
                if hasattr(chunk, "delta") and chunk.delta:
                    yield chunk.delta
                elif hasattr(chunk, "output"):
                    for item in chunk.output:
                        if hasattr(item, "content"):
                            yield item.content
        else:
            # Standard Chat API streaming
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

    def validate_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate tools for Azure."""
        # Azure uses same format as OpenAI
        return OpenAIProvider.validate_tools(self, tools)

    def extract_content(self, response: Any) -> str:
        """Extract content from Azure response."""
        if self.use_responses_api:
            if hasattr(response, "output") and response.output:
                for item in response.output:
                    if hasattr(item, "content"):
                        return item.content
            return ""
        else:
            return OpenAIProvider.extract_content(self, response)

    def extract_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """Extract tool calls from Azure response."""
        if self.use_responses_api:
            tool_calls = []
            if hasattr(response, "output") and response.output:
                for item in response.output:
                    if getattr(item, "type", None) == "function_call":
                        tool_calls.append({
                            "id": item.call_id,
                            "name": item.name,
                            "arguments": item.arguments
                        })
            return tool_calls
        else:
            return OpenAIProvider.extract_tool_calls(self, response)

    def format_tool_result(
        self,
        tool_call_id: str,
        tool_name: str,
        result: str
    ) -> Dict[str, Any]:
        """Format tool result for Azure."""
        if self.use_responses_api:
            return {
                "type": "function_call_output",
                "call_id": tool_call_id,
                "output": result
            }
        else:
            return OpenAIProvider.format_tool_result(self, tool_call_id, tool_name, result)

    def get_supported_features(self) -> set[str]:
        """Azure supports additional features."""
        features = super().get_supported_features()
        if self.use_responses_api:
            features.add("reasoning")
            features.add("stateful_conversations")
        return features