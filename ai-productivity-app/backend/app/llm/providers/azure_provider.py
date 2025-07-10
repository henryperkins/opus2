"""Azure OpenAI provider implementation."""

from typing import Any, AsyncIterator, Dict, List, Optional
import logging
from openai import AsyncAzureOpenAI

from .base import LLMProvider
from .utils import build_openai_chat_params
from .openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI provider implementation."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.use_responses_api = kwargs.get("use_responses_api", False)
        from app.config import settings
        self.api_version = kwargs.get(
            "api_version",
            settings.azure_openai_api_version
        )

    # ------------------------------------------------------------------
    # Helper shortcuts – kept for backward compatibility only
    # ------------------------------------------------------------------
    #
    # Earlier versions of *AzureOpenAIProvider* exposed their own
    # ``_is_reasoning_model`` / ``_requires_responses_api`` wrappers.  The
    # logic is now centralised in :pymeth:`app.services.model_service.ModelService`
    # static helpers.  We therefore alias the new single source of truth to
    # avoid large-scale refactors elsewhere in the provider implementation.

    from app.services.model_service import ModelService as _MS  # type: ignore

    _is_reasoning_model = staticmethod(_MS.is_reasoning_model_static)  # type: ignore
    _requires_responses_api = staticmethod(_MS.requires_responses_api_static)  # type: ignore

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

        # Decide API variant.  *use_responses_api* can be forced by
        # constructor kwargs but we also auto-enable it when the selected
        # *model* requires the Responses API (o3/o4 or GPT-4o family).  This
        # avoids silent 400 errors when callers forgot to set the flag.

        auto_responses = self._is_reasoning_model(model) or self._requires_responses_api(model)

        # Auto-enable Responses API mode when the selected *model* mandates it
        # (e.g. GPT-4o or reasoning family).  Persist the decision so that
        # subsequent helper methods (*stream*, *extract_content*, …) see the
        # correct flag.
        if auto_responses and not self.use_responses_api:
            self.use_responses_api = True

        if self.use_responses_api:
            return await self._complete_responses_api(
                messages,
                model,
                temperature,
                max_tokens,
                stream,
                tools,
                tool_choice,
                reasoning,
                **kwargs,
            )

        # Fallback to Chat Completions API
        return await self._complete_chat_api(
            messages,
            model,
            temperature,
            max_tokens,
            stream,
            tools,
            tool_choice,
            parallel_tool_calls,
            **kwargs,
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
        is_reasoning = self._is_reasoning_model(model)
        
        # Convert system messages to developer messages for reasoning models
        processed_messages = []
        for msg in messages:
            if is_reasoning and msg.get("role") == "system":
                processed_messages.append({
                    "role": "developer",
                    "content": msg["content"]
                })
            else:
                processed_messages.append(msg)
        
        if is_reasoning:
            params = {
                "model": model,
                "messages": processed_messages,
                "stream": False,
            }
            if max_tokens:
                params["max_completion_tokens"] = max_tokens
        # Do *not* set temperature for reasoning models
        else:
            # Regular models support all features
            params = build_openai_chat_params(
                model=model,
                messages=processed_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                tools=tools,
                tool_choice=tool_choice,
                parallel_tool_calls=parallel_tool_calls,
                **kwargs
            )
        
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
        is_reasoning = self._is_reasoning_model(model)

        # Convert messages to Responses API format
        input_messages = []
        instructions = None

        for msg in messages:
            if msg["role"] == "system":
                if instructions:
                    instructions += "\n\n" + msg["content"]
                else:
                    instructions = msg["content"]
            elif msg["role"] == "developer" or (is_reasoning and msg["role"] == "system"):
                # For reasoning models, handle developer messages properly
                input_messages.append({
                    "role": "developer",
                    "content": msg["content"],
                    "type": "message"
                })
            else:
                input_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                    "type": "message"
                })

        # For reasoning models, use simple input format as shown in the docs
        if is_reasoning and len(input_messages) == 1 and input_messages[0]["role"] == "user":
            # Use simple string input format for single user messages
            params = {
                "model": model,
                "input": input_messages[0]["content"]
            }
        else:
            # Use message array format for complex conversations
            params = {
                "model": model,
                "input": input_messages
            }
            
        # Reasoning models don't support temperature or streaming
        if not is_reasoning:
            params["temperature"] = temperature
            params["stream"] = stream
        else:
            params["stream"] = False

        if instructions and not is_reasoning:
            params["instructions"] = instructions

        if max_tokens:
            params["max_output_tokens"] = max_tokens

        # Reasoning models don't support tools
        # Attach *tools* and *tool_choice* for normal chat models (the Azure
        # *reasoning* family ignores both).  We purposely *do not* require
        # that a non-empty *tools* list accompanies *tool_choice* because the
        # SDK accepts the latter on its own when the tool definitions were
        # provided earlier in the conversation.
        if not is_reasoning:
            if tools:
                params["tools"] = self.validate_tools(tools)
            if tool_choice is not None:
                params["tool_choice"] = tool_choice
        # The Responses API *does* support tool_choice in the same way as the
        # Chat Completions endpoint.  Earlier versions of this provider left
        # the parameter un-used which meant that callers could *request* a
        # specific tool call but the model kept choosing tools automatically.
        #
        # We therefore forward *tool_choice* unconditionally when it is
        # supplied (and the model is not a reasoning model which would ignore
        # the field anyway).  The conditional above already ensures we do not
        # attach the argument when *tool_choice* is *None* or when the model
        # doesn’t allow tools in the first place.

        # Add reasoning configuration for reasoning models
        if reasoning and is_reasoning:
            # Ensure proper reasoning format: {"effort": "medium", "summary": "detailed"}
            reasoning_config = {}
            if isinstance(reasoning, dict):
                reasoning_config["effort"] = reasoning.get("effort", "medium")
                # summary is only supported for o3 and o4-mini models
                if model.lower() in ["o3", "o3-mini", "o3-pro", "o4-mini"]:
                    reasoning_config["summary"] = reasoning.get("summary", "detailed")
            else:
                reasoning_config["effort"] = "medium"
            params["reasoning"] = reasoning_config

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
            # Flush remaining output when stream closed
            if self.use_responses_api and hasattr(response, "output"):
                for item in response.output:
                    if getattr(item, "content", None):
                        yield item.content
        else:
            # Standard Chat API streaming
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

    

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
                            "id": getattr(item, "id", getattr(item, "call_id", None)),
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
        # Add reasoning model support
        features.add("reasoning_models")
        features.add("developer_messages")
        return features

    def get_model_info(self, model: str) -> Dict[str, Any]:
        """Get information about a specific model."""
        is_reasoning = self._is_reasoning_model(model)
        
        if is_reasoning:
            return {
                "supports_tools": False,
                "supports_streaming": False,
                "supports_temperature": False,
                "max_tokens": 200000,  # Large context window for reasoning models
                "supports_reasoning": True,
                "supports_json_mode": False,
                "model_type": "reasoning"
            }
        else:
            return {
                "supports_tools": True,
                "supports_streaming": True,
                "supports_temperature": True,
                "max_tokens": 128000,
                "supports_reasoning": False,
                "supports_json_mode": True,
                "model_type": "chat"
            }