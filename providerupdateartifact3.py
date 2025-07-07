# Complete implementation of Provider Strategy Pattern for LLM Client
# This creates a clean separation of concerns and makes adding new providers easy

# ========== app/llm/providers/base.py ==========

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


# ========== app/llm/providers/openai_provider.py ==========

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


# ========== app/llm/providers/azure_provider.py ==========

from typing import Any, AsyncIterator, Dict, List, Optional
import logging
from openai import AsyncAzureOpenAI

from .base import LLMProvider

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


# ========== app/llm/providers/anthropic_provider.py ==========

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


# ========== app/llm/client.py - Refactored client ==========

from typing import Any, AsyncIterator, Dict, List, Optional, Sequence
import logging
import time
from datetime import datetime

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.llm.providers.base import LLMProvider
from app.llm.providers.openai_provider import OpenAIProvider
from app.llm.providers.azure_provider import AzureOpenAIProvider
from app.llm.providers.anthropic_provider import AnthropicProvider

logger = logging.getLogger(__name__)


class LLMClient:
    """Unified LLM client with provider strategy pattern."""

    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {}
        self.active_provider_name: str = settings.llm_provider.lower()
        self.active_model: str = settings.llm_default_model or settings.llm_model or "gpt-3.5-turbo"

        self._initialize_providers()
        self._metrics_hooks = []

    def _initialize_providers(self) -> None:
        """Initialize all configured providers."""

        # OpenAI
        if settings.openai_api_key:
            try:
                self.providers["openai"] = OpenAIProvider(
                    api_key=settings.openai_api_key,
                    timeout=getattr(settings, "llm_timeout_seconds", 300)
                )
                logger.info("OpenAI provider initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI provider: {e}")

        # Azure OpenAI
        if settings.azure_openai_endpoint:
            try:
                azure_config = {
                    "endpoint": settings.azure_openai_endpoint,
                    "api_key": settings.azure_openai_api_key,
                    "auth_method": getattr(settings, "azure_auth_method", "api_key"),
                    "api_version": getattr(settings, "azure_openai_api_version", "2025-04-01-preview"),
                    "timeout": getattr(settings, "llm_timeout_seconds", 300)
                }

                # Check if we should use Responses API
                if hasattr(settings, "azure_use_responses_api"):
                    azure_config["use_responses_api"] = settings.azure_use_responses_api

                self.providers["azure"] = AzureOpenAIProvider(**azure_config)
                logger.info("Azure OpenAI provider initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Azure provider: {e}")

        # Anthropic
        if settings.anthropic_api_key:
            try:
                self.providers["anthropic"] = AnthropicProvider(
                    api_key=settings.anthropic_api_key,
                    timeout=getattr(settings, "llm_timeout_seconds", 300)
                )
                logger.info("Anthropic provider initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic provider: {e}")

    @property
    def active_provider(self) -> LLMProvider:
        """Get the currently active provider."""
        provider = self.providers.get(self.active_provider_name)
        if not provider:
            raise RuntimeError(f"Provider '{self.active_provider_name}' not initialized")
        return provider

    async def reconfigure(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> None:
        """Dynamically reconfigure the client."""
        if provider and provider in self.providers:
            self.active_provider_name = provider
            logger.info(f"Switched to provider: {provider}")

        if model:
            self.active_model = model
            logger.info(f"Switched to model: {model}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((Exception,)),  # Retry on any exception
        reraise=True
    )
    async def complete(
        self,
        messages: Sequence[Dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str | Dict[str, Any]] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> Any:
        """Execute completion with automatic retry and metrics."""

        start_time = time.time()
        active_model = model or self.active_model

        try:
            # Get runtime config
            runtime_config = self._get_runtime_config()

            # Apply defaults
            temperature = temperature if temperature is not None else runtime_config.get("temperature", 0.7)
            max_tokens = max_tokens or runtime_config.get("max_tokens")

            # Execute completion
            response = await self.active_provider.complete(
                messages=list(messages),
                model=active_model,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                tools=tools,
                tool_choice=tool_choice,
                **kwargs
            )

            # Record metrics
            duration_ms = (time.time() - start_time) * 1000
            await self._record_metrics(
                "success",
                active_model,
                messages,
                response,
                duration_ms
            )

            return response

        except Exception as e:
            # Record failure metrics
            duration_ms = (time.time() - start_time) * 1000
            await self._record_metrics(
                "failure",
                active_model,
                messages,
                None,
                duration_ms,
                error=str(e)
            )
            raise

    async def generate_response(self, prompt: str, **kwargs) -> Any:
        """Simple interface for single prompts."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
        return await self.complete(messages, **kwargs)

    def prepare_code_context(self, chunks: Sequence[Dict[str, Any]]) -> str:
        """Format code chunks for context."""
        if not chunks:
            return "No code context available."

        parts = []
        for chunk in chunks:
            path = chunk.get("file_path", "<unknown>")
            start = chunk.get("start_line", "?")
            end = chunk.get("end_line", "?")
            content = chunk.get("content", "").strip()
            parts.append(
                f"File: {path} lines {start}-{end}\n"
                + "-" * 20 + f"\n{content}\n"
            )
        return "\n\n".join(parts)

    def _get_runtime_config(self) -> Dict[str, Any]:
        """Get runtime configuration."""
        try:
            from app.services.config_cache import get_config
            return get_config()
        except Exception:
            return {
                "temperature": 0.7,
                "max_tokens": None
            }

    async def _record_metrics(
        self,
        status: str,
        model: str,
        messages: Sequence[Dict[str, Any]],
        response: Optional[Any],
        duration_ms: float,
        error: Optional[str] = None
    ) -> None:
        """Record metrics for the completion."""
        for hook in self._metrics_hooks:
            try:
                await hook(status, model, messages, response, duration_ms, error)
            except Exception as e:
                logger.error(f"Metrics hook failed: {e}")

    def add_metrics_hook(self, hook) -> None:
        """Add a metrics recording hook."""
        self._metrics_hooks.append(hook)

    # Compatibility methods
    def _is_reasoning_model(self, model: str) -> bool:
        """Check if model is a reasoning model."""
        reasoning_models = {"o1", "o1-mini", "o1-preview", "o3", "o3-mini", "o4-mini"}
        return model.lower() in reasoning_models

    def _has_tool_calls(self, response: Any) -> bool:
        """Check if response has tool calls."""
        return len(self.active_provider.extract_tool_calls(response)) > 0

    def _extract_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """Extract tool calls from response."""
        return self.active_provider.extract_tool_calls(response)

    @property
    def provider(self) -> str:
        """Get current provider name for compatibility."""
        return self.active_provider_name

    @property
    def use_responses_api(self) -> bool:
        """Check if using Azure Responses API."""
        if self.active_provider_name == "azure":
            azure_provider = self.active_provider
            return getattr(azure_provider, "use_responses_api", False)
        return False


# Global singleton
llm_client = LLMClient()
