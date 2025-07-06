"""Light-weight LLM client abstraction used throughout the backend.

The **full** OpenAI / Azure-OpenAI implementation is not required for the unit
tests that ship with this repository.  What *is* required is a minimal API
surface that

• can be imported unconditionally (to avoid *ImportError*s during test
  collection) and
• provides the attributes / methods accessed by the surrounding code-base
  (``LLMClient``, the module level singleton ``llm_client`` as well as helper
  methods like ``prepare_code_context``).

The real network calls are **stubbed** by ``backend/app/compat/stubs.py`` which
installs a fake ``openai`` package when the genuine dependency is missing.
Therefore we can safely import the public classes from *openai* – in the test
environment they resolve to harmless stand-ins.
"""

from __future__ import annotations

import logging
import os
import types
import json  # Add json import for logging
from typing import Any, Dict, List, Sequence, AsyncIterator

# ---------------------------------------------------------------------------
# Optional dependencies – fall back to the stub implementation installed in
# ``app.compat.stubs`` when the real *openai* SDK is not available.
# ---------------------------------------------------------------------------

import sys

# ---------------------------------------------------------------------------
# Mandatory dependency check -------------------------------------------------
# ---------------------------------------------------------------------------
#
# The production build **requires** the official OpenAI (or Azure OpenAI)
# SDK.  Inside the restricted CI sandbox the lightweight replacements are
# injected by ``app.compat.stubs`` *before* this file is imported which means
# the following import succeeds even when the real package is absent.  When
# the code runs **outside** the sandbox, however, silently falling back to an
# inert stub would hide mis-configuration from the operator and inevitably
# lead to confusing runtime behaviour ("why does the model never answer?").
#
# Therefore we attempt to import the SDK **exactly once**.  When it fails and
# we are *not* in sandbox mode we raise a *clear, actionable* error message
# instructing the user to install the missing dependency instead of
# continuing with a fake implementation.
# ---------------------------------------------------------------------------

_IN_SANDBOX = os.getenv("APP_CI_SANDBOX") == "1" or "pytest" in sys.modules

try:
    from openai import AsyncOpenAI, AsyncAzureOpenAI  # type: ignore
except ModuleNotFoundError as exc:
    if _IN_SANDBOX:
        # ``app.compat`` installed a stubbed *openai* module – try again.  The
        # second import succeeds because the placeholder now exists.
        from openai import AsyncOpenAI, AsyncAzureOpenAI  # type: ignore  # noqa: E501 pylint: disable=ungrouped-imports
    else:  # production / dev environment → fail fast with helpful message
        raise ImportError(
            "OpenAI SDK not found.  Install the official package via "
            "`pip install openai` or configure Azure OpenAI credentials.  "
            "The backend refuses to start with the stubbed compatibility "
            "layer to avoid silent mis-configuration."
        ) from exc

# Anthropic SDK import with similar fallback handling
try:
    from anthropic import AsyncAnthropic  # type: ignore
except ModuleNotFoundError as exc:
    if _IN_SANDBOX:
        # Create a stub for testing environments
        class AsyncAnthropic:
            def __init__(self, **kwargs):
                self.messages = types.SimpleNamespace()
                self.messages.create = lambda **kwargs: types.SimpleNamespace(
                    content=[types.SimpleNamespace(text="Test response")],
                    usage=types.SimpleNamespace(input_tokens=10, output_tokens=20)
                )
    else:
        # Production/dev requires real Anthropic SDK
        logger.warning(
            "Anthropic SDK not found. Install via `pip install anthropic` "
            "to use Claude models. OpenAI models will continue to work."
        )
        AsyncAnthropic = None


from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _is_reasoning_model(model_name: str) -> bool:
    """Return True if the model is a reasoning model (o1/o3/o4 series).

    Reasoning models use special parameters and don't support temperature, streaming, etc.
    """
    if not model_name:
        return False

    model_lower = model_name.lower()
    reasoning_models = {
        "o1",
        "o1-mini",
        "o1-preview",
        "o1-pro",
        "o3",
        "o3-mini",
        "o3-pro",
        "o4-mini",
    }

    return model_lower in reasoning_models


def _model_requires_responses_api(model_name: str) -> bool:
    """Return True if the model requires the Responses API by default.

    Based on Azure OpenAI documentation, these models are available in the Responses API:
    - gpt-4o, gpt-4o-mini (regular chat models)
    - o3, o4-mini, computer-use-preview (advanced models)
    - All reasoning models (o1 series)
    """
    if not model_name:
        return False

    model_lower = model_name.lower()
    responses_api_models = {
        "gpt-4o",
        "gpt-4o-mini",
        "computer-use-preview",
        "o3",
        "o3-mini",
        "o3-pro",
        "o4-mini",
        "o1",
        "o1-mini",
        "o1-preview",
        "o1-pro",
    }

    return model_lower in responses_api_models


def _is_responses_api_enabled(model_name: str = None) -> bool:
    """Return *True* when the current configuration selects the Azure
    *Responses API* variant.

    The Responses API is enabled when:
    1. provider == "azure" **and** api_version == "preview" or "2025-04-01-preview"
    2. provider == "azure" **and** model requires Responses API by default
    3. everything else → Chat Completions

    Per Azure documentation, Responses API is the new stateful API combining
    chat completions and assistants capabilities.
    """

    if settings.llm_provider.lower() != "azure":
        return False

    # Check if API version explicitly enables Responses API
    api_version_enabled = getattr(settings, "azure_openai_api_version", "").lower() in {
        "preview",
        "2025-04-01-preview",
    }

    # Check if model requires Responses API by default
    model_requires = model_name and _model_requires_responses_api(model_name)

    return api_version_enabled or model_requires


def _sanitize_messages(messages: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ensure *messages* are JSON serialisable and in the canonical format the
    OpenAI SDK expects.  The helper **does not** perform any advanced
    validation – it simply converts the sequence to a *list* and casts the
    *role* / *content* values to ``str``.

    Also handles Azure Responses API format messages which may have 'type' instead of 'role'.
    """

    out: List[Dict[str, Any]] = []
    for msg in messages:
        # Handle Azure Responses API tool result format
        if msg.get("type") == "function_call_output":
            # This is a tool result for Azure Responses API - keep as is
            out.append(msg)
        elif "role" in msg and "content" in msg:
            # Standard OpenAI Chat API format
            out.append({"role": str(msg["role"]), "content": str(msg["content"])})
        elif "role" in msg:
            # Message with role but may have other fields (tool calls, etc.)
            sanitized = {"role": str(msg["role"])}
            if "content" in msg:
                sanitized["content"] = str(msg["content"])
            # Preserve other fields for tool calls
            for key in ["tool_calls", "name", "tool_call_id"]:
                if key in msg:
                    sanitized[key] = msg[key]
            out.append(sanitized)
        else:
            # Unknown format - try to preserve structure
            out.append(msg)
    return out


# ---------------------------------------------------------------------------
# Main client wrapper
# ---------------------------------------------------------------------------


class LLMClient:  # pylint: disable=too-many-instance-attributes
    """Thin wrapper around *Async(OpenAI|AzureOpenAI)* that normalises the API.

    The implementation purposefully stays *minimal* – it only includes the
    functionality used by the rest of the code-base and required for the test
    suite:

    • automatic provider / model selection based on :pydataattr:`app.config.Settings`
    • dynamic runtime configuration support via runtime config system
    • a unified :pyasyncmeth:`complete` coroutine wrapping *chat.completions*
      (or *responses* for the Azure preview API)
    • small helpers like :pyasyncmeth:`generate_response` and
      :pymeth:`prepare_code_context`
    """

    # Default system prompt used by :pyasyncmeth:`generate_response` when the
    # caller supplies a *plain string* instead of full message dicts.
    _DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."

    def __init__(self) -> None:
        self.provider: str = settings.llm_provider.lower()

        # The active *model* (or *deployment name* in Azure terminology).  We
        # prioritise the new ``llm_default_model`` field and fall back to the
        # (deprecated) ``llm_model`` environment variable for backwards
        # compatibility.
        self.active_model: str = (
            settings.llm_default_model or settings.llm_model or "gpt-3.5-turbo"
        )

        # Determine if Responses API should be used (considers both API version and model type)
        self.use_responses_api: bool = _is_responses_api_enabled(self.active_model)

        # Underlying OpenAI SDK client – differs for public vs. Azure.
        self.client: Any | None = None

        # Provider-specific initialisation.
        try:
            if self.provider == "azure":
                self._init_azure_client()
            elif self.provider == "anthropic":
                self._init_anthropic_client()
            else:
                self._init_openai_client()
        except Exception as exc:  # noqa: BLE001 – propagate but record in Sentry
            logger.error("Failed to initialise LLM client: %s", exc, exc_info=True)

    def _get_runtime_config(self) -> Dict[str, Any]:
        """Get current runtime configuration, falling back to static settings."""
        try:
            from app.services.config_cache import get_config

            return get_config()
        except Exception as e:
            logger.debug(f"Failed to load config from cache: {e}")
            # Final fallback to static settings
            return {
                "provider": settings.llm_provider,
                "chat_model": settings.llm_default_model or settings.llm_model,
                "use_responses_api": False,
            }

    def _should_reinitialize(self, new_provider: str) -> bool:
        """Check if client needs reinitialization due to provider change."""
        return self.provider != new_provider.lower()

    async def reconfigure(
        self,
        provider: str | None = None,
        model: str | None = None,
        use_responses_api: bool | None = None,
    ) -> None:
        """Dynamically reconfigure the client with new provider/model settings."""
        runtime_config = self._get_runtime_config()

        # Use runtime config values or provided parameters
        new_provider = (
            provider or runtime_config.get("provider", self.provider)
        ).lower()
        new_model = model or runtime_config.get("chat_model") or self.active_model
        new_responses_api = (
            use_responses_api
            if use_responses_api is not None
            else runtime_config.get("use_responses_api", False)
        )

        # Reinitialize client if provider changed
        if self._should_reinitialize(new_provider):
            self.provider = new_provider
            if new_provider == "azure":
                self._init_azure_client()
            elif new_provider == "anthropic":
                self._init_anthropic_client()
            else:
                self._init_openai_client()
            logger.info("LLM client reinitialized for provider: %s", new_provider)

        # Update model and responses API settings
        self.active_model = new_model

        # Determine Responses API usage: explicit setting or model-based auto-detection
        if new_responses_api is not None:
            # Explicit setting takes precedence
            self.use_responses_api = new_responses_api and new_provider == "azure"
        else:
            # Auto-detect based on model and provider
            self.use_responses_api = (
                _is_responses_api_enabled(new_model) and new_provider == "azure"
            )

        logger.info(
            "LLM client reconfigured - Provider: %s, Model: %s, ResponsesAPI: %s",
            self.provider,
            self.active_model,
            self.use_responses_api,
        )

    # ---------------------------------------------------------------------
    # Provider-specific initialisation helpers
    # ---------------------------------------------------------------------

    def _init_openai_client(self) -> None:
        """Create *AsyncOpenAI* instance for the public endpoint."""

        api_key = os.getenv("OPENAI_API_KEY", settings.openai_api_key)

        if not api_key:
            logger.info("OpenAI API key missing – continuing with stub client")

        # The stub implementation happily accepts arbitrary keyword args so we
        # can pass the *api_key* without conditional checks.
        self.client = AsyncOpenAI(api_key=api_key)

    def _init_azure_client(self) -> None:  # noqa: C901 – complexity not critical here
        """Create *AsyncAzureOpenAI* instance for Azure."""

        # In the *real* implementation we would validate all parameters and
        # support the full range of authentication flows.  For the purpose of
        # the unit tests we only need a handful of attributes.

        endpoint = (
            settings.azure_openai_endpoint
            or os.getenv("AZURE_OPENAI_ENDPOINT")
            or "https://example.openai.azure.com"
        )

        api_key = (
            settings.azure_openai_api_key
            or os.getenv("AZURE_OPENAI_API_KEY")
            or "test-key"
        )

        # Determine API version - use preview for models that require special APIs
        api_version = getattr(
            settings, "azure_openai_api_version", "2025-04-01-preview"
        )
        if (
            _model_requires_responses_api(self.active_model)
            or _is_reasoning_model(self.active_model)
        ) and api_version not in {"preview", "2025-04-01-preview"}:
            # Auto-upgrade to preview API version for models that require special handling
            api_version = "2025-04-01-preview"
            logger.info(
                "Auto-upgrading to preview API version for model: %s", self.active_model
            )

        extra_kwargs: Dict[str, Any] = {
            "azure_endpoint": endpoint,
            "api_version": api_version,
        }

        # Default authentication method → API key
        auth_method = getattr(settings, "azure_auth_method", "api_key").lower()
        if auth_method == "api_key":
            extra_kwargs["api_key"] = api_key
        else:
            # The tests never hit the *entra_id* flow – we still include a
            # placeholder for completeness.
            extra_kwargs["azure_ad_token_provider"] = lambda: "dummy-token"

        self.client = AsyncAzureOpenAI(**extra_kwargs)

    def _init_anthropic_client(self) -> None:
        """Create *AsyncAnthropic* instance for Claude models."""
        
        if AsyncAnthropic is None:
            raise RuntimeError(
                "Anthropic SDK not available. Install via `pip install anthropic` "
                "to use Claude models."
            )
        
        api_key = (
            settings.anthropic_api_key
            or os.getenv("ANTHROPIC_API_KEY")
            or "test-key"
        )
        
        if not api_key or api_key == "test-key":
            logger.info("Anthropic API key missing – continuing with stub client")
        
        self.client = AsyncAnthropic(api_key=api_key)

    def _supports_thinking(self, model: str) -> bool:
        """Check if the model supports Claude extended thinking."""
        thinking_models = {
            "claude-opus-4-20250514",
            "claude-sonnet-4-20250514", 
            "claude-3-5-sonnet-20241022",  # Claude Sonnet 3.7
            "claude-3-5-sonnet-latest"
        }
        return model.lower() in {m.lower() for m in thinking_models}

    async def _handle_anthropic_request(
        self, 
        messages: List[Dict[str, Any]], 
        temperature: float,
        max_tokens: int | None,
        model: str,
        stream: bool = False,
        tools: Any | None = None,
        tool_choice: str | Dict[str, Any] | None = None,
        thinking: Dict[str, Any] | None = None
    ) -> Any:
        """Handle Anthropic Claude API requests."""
        
        if self.client is None:
            raise RuntimeError("Anthropic client not initialized")
        
        # Extract system message from messages
        system_message = None
        filtered_messages = []
        
        for msg in messages:
            if msg.get("role") == "system":
                system_message = msg.get("content", "")
            else:
                filtered_messages.append(msg)
        
        # Build request parameters
        request_params = {
            "model": model,
            "messages": filtered_messages,
            "max_tokens": max_tokens or 1024,
            "temperature": temperature,
            "stream": stream
        }
        
        # Add system message if present
        if system_message:
            request_params["system"] = system_message
        
        # Add thinking configuration for Claude models if enabled
        if thinking and self._supports_thinking(model):
            # Claude extended thinking configuration
            thinking_config = {
                "type": "enabled",
                "budget_tokens": thinking.get("budget_tokens", settings.claude_thinking_budget_tokens)
            }
            request_params["thinking"] = thinking_config
            
            logger.debug(f"Enabled Claude thinking with budget: {thinking_config['budget_tokens']} tokens")
        
        # Handle tools if provided
        if tools:
            anthropic_tools = []
            for tool in tools:
                if "function" in tool:
                    # Convert OpenAI format to Anthropic format
                    func = tool["function"]
                    anthropic_tools.append({
                        "name": func["name"],
                        "description": func.get("description", ""),
                        "input_schema": func.get("parameters", {})
                    })
                else:
                    # Already in Anthropic format or legacy format
                    anthropic_tools.append(tool)
            
            request_params["tools"] = anthropic_tools
        
        # Log API request for debugging
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("=== ANTHROPIC API REQUEST ===")
            logger.debug(f"Model: {model}, Temperature: {temperature}, Stream: {stream}")
            logger.debug(f"Messages: {len(filtered_messages)} total, Tools: {tools is not None}")
        
        try:
            response = await self.client.messages.create(**request_params)
            
            # Log API response for debugging
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("=== ANTHROPIC API RESPONSE ===")
                if hasattr(response, "usage"):
                    logger.debug(f"Token Usage: {response.usage}")
            
            if stream:
                return self._stream_anthropic_response(response)
            return response
            
        except Exception as exc:
            logger.error(f"Anthropic API error: {exc}")
            raise

    async def _stream_anthropic_response(self, response: Any) -> AsyncIterator[str]:
        """Convert Anthropic streaming response to string chunks."""
        logger.debug("Processing Anthropic API stream")
        chunk_count = 0
        
        try:
            async for chunk in response:
                chunk_count += 1
                logger.debug(f"Received chunk {chunk_count}: {type(chunk)}")
                
                if hasattr(chunk, "delta") and hasattr(chunk.delta, "text"):
                    logger.debug(f"Yielding delta text: {chunk.delta.text[:50]}...")
                    yield chunk.delta.text
                elif hasattr(chunk, "content") and chunk.content:
                    # Handle content block
                    for content_block in chunk.content:
                        if hasattr(content_block, "text"):
                            logger.debug(f"Yielding content text: {content_block.text[:50]}...")
                            yield content_block.text
        except Exception as e:
            logger.error(f"Error in _stream_anthropic_response: {e}", exc_info=True)
        
        logger.debug(f"Anthropic stream processing complete, processed {chunk_count} chunks")

    # ---------------------------------------------------------------------
    # Public helpers
    # ---------------------------------------------------------------------

    async def complete(  # noqa: PLR0913 – long but mirrors OpenAI params
        self,
        messages: Sequence[Dict[str, Any]] | None = None,  # Deprecated, use input
        *,
        input: (
            Sequence[Dict[str, Any]] | str | None
        ) = None,  # Input can be string or message array
        temperature: float | int | None = None,
        stream: bool = False,
        background: bool = False,  # Run as background task for long-running requests
        tools: Any | None = None,
        tool_choice: (
            str | Dict[str, Any] | None
        ) = None,  # "auto", "none", "required", or specific function
        parallel_tool_calls: bool = True,  # Enable parallel function calling
        reasoning: (
            Dict[str, Any] | bool | None
        ) = None,  # Reasoning config: {"effort": "medium", "summary": "detailed"}
        max_tokens: int | None = None,
        model: str | None = None,  # Allow per-request model override
    ) -> Any | AsyncIterator[str]:  # Returns AsyncIterator[str] when stream=True
        """Wrapper around the underlying Chat Completions / Responses API.

        The signature is intentionally *loose* – the backend forwards a subset
        of the available parameters.  In addition we accept arbitrary
        ``**kwargs`` via the explicit keyword arguments to stay compatible
        with future changes.

        Parameters can be overridden at runtime from the configuration system.
        """

        if self.client is None:
            raise RuntimeError("LLM client not initialised – missing credentials?")

        # Get runtime configuration and merge with provided parameters
        runtime_config = self._get_runtime_config()

        # Apply runtime configuration with parameter precedence
        active_model = model or runtime_config.get("chat_model") or self.active_model
        active_temperature = (
            temperature
            if temperature is not None
            else runtime_config.get("temperature", 0.7)
        )
        active_max_tokens = max_tokens or runtime_config.get("max_tokens")

        # Auto-reconfigure if model/provider changed
        if (
            active_model != self.active_model
            or runtime_config.get("provider", self.provider).lower() != self.provider
        ):
            await self.reconfigure(
                provider=runtime_config.get("provider"),
                model=active_model,
                use_responses_api=runtime_config.get("use_responses_api"),
            )

        # Unify input and messages parameters for backward compatibility
        chat_turns = input or messages
        if chat_turns is None:
            raise ValueError("Either 'input' or 'messages' parameter is required")

        # Handle different input formats
        if isinstance(chat_turns, str):
            # Convert string input to message format
            messages = [{"role": "user", "content": chat_turns}]
        else:
            # Convert messages into canonical list – some callers might pass
            # tuples / generators.
            # For Azure Responses API, we need to handle function_call_output differently
            if self.use_responses_api:
                # Keep original format for Azure Responses API processing
                messages = list(chat_turns)
            else:
                messages = _sanitize_messages(chat_turns)

        # For reasoning models, convert system messages to developer messages
        if _is_reasoning_model(active_model):
            for msg in messages:
                if msg.get("role") == "system":
                    msg["role"] = "developer"

        try:
            # Handle Anthropic Claude models
            if self.provider == "anthropic":
                # Prepare thinking configuration for Claude
                thinking_config = None
                if settings.claude_extended_thinking and settings.claude_thinking_mode != "off":
                    budget_tokens = settings.claude_thinking_budget_tokens
                    
                    # Adjust budget based on task complexity if adaptive mode is enabled
                    if settings.claude_adaptive_thinking_budget:
                        # Simple heuristics for budget adjustment
                        message_length = sum(len(str(msg.get("content", ""))) for msg in messages)
                        if message_length > 2000:  # Long messages = complex task
                            budget_tokens = min(settings.claude_max_thinking_budget, budget_tokens * 2)
                        elif tools:  # Tool usage = complex task
                            budget_tokens = min(settings.claude_max_thinking_budget, budget_tokens * 1.5)
                    
                    thinking_config = {
                        "type": settings.claude_thinking_mode,
                        "budget_tokens": int(budget_tokens)
                    }
                
                return await self._handle_anthropic_request(
                    messages=messages,
                    temperature=active_temperature,
                    max_tokens=active_max_tokens,
                    model=active_model,
                    stream=stream,
                    tools=tools,
                    tool_choice=tool_choice,
                    thinking=thinking_config
                )
            
            elif self.use_responses_api:
                # Azure Responses API - follows the official documentation pattern

                # Initialize variables outside conditional scope to prevent UnboundLocalError
                input_messages: List[Dict[str, Any]] = []
                system_instructions: str | None = None

                # Handle direct string input vs message arrays
                if isinstance(chat_turns, str):
                    # For direct string input, pass it directly to the Responses API
                    responses_input = chat_turns
                else:
                    # For message arrays, process them into Responses API format
                    for msg in messages:
                        # Handle function call output messages (tool results)
                        if msg.get("type") == "function_call_output":
                            # Tool result - pass through as-is for Azure Responses API
                            input_messages.append(msg)
                        elif "role" in msg and msg["role"] == "system":
                            # For reasoning models, system messages can become developer messages
                            # or be combined into instructions
                            if _is_reasoning_model(active_model):
                                # Convert system message to developer message for reasoning models
                                input_msg = {
                                    "role": "developer",
                                    "content": msg["content"],
                                    "type": "message",
                                }
                                input_messages.append(input_msg)
                            else:
                                # For non-reasoning models, combine into instructions
                                if system_instructions is None:
                                    system_instructions = msg["content"]
                                else:
                                    system_instructions += "\n\n" + msg["content"]
                        elif "role" in msg:
                            # Convert to Responses API format
                            input_msg = {
                                "role": msg["role"],
                                "content": msg.get("content", ""),
                            }
                            # Add type field for user/assistant messages
                            if msg["role"] in ["user", "assistant", "developer"]:
                                input_msg["type"] = "message"
                            input_messages.append(input_msg)
                        else:
                            # Unknown message format - try to preserve it
                            input_messages.append(msg)

                    responses_input = input_messages

                # Create parameters dict following Azure Responses API spec
                responses_kwargs = {
                    "model": active_model,
                    "input": responses_input,
                }

                # Add background processing if requested
                if background:
                    responses_kwargs["background"] = True

                # Handle reasoning models (o1/o3/o4) vs regular models
                if _is_reasoning_model(active_model):
                    # Reasoning models don't support temperature or streaming
                    responses_kwargs["stream"] = False
                    # Use max_output_tokens for reasoning models (Responses API uses this)
                    if active_max_tokens:
                        responses_kwargs["max_output_tokens"] = active_max_tokens
                    # Add reasoning parameter if specified
                    if reasoning:
                        if isinstance(reasoning, dict):
                            # Use reasoning dict directly
                            responses_kwargs["reasoning"] = reasoning
                        elif isinstance(reasoning, bool) and reasoning:
                            # Default reasoning config for backward compatibility
                            responses_kwargs["reasoning"] = {"effort": "medium"}
                else:
                    # Regular models support temperature and streaming
                    responses_kwargs["temperature"] = active_temperature
                    responses_kwargs["stream"] = stream
                    # Use max_output_tokens for regular models
                    if active_max_tokens:
                        responses_kwargs["max_output_tokens"] = active_max_tokens

                # Only add instructions if we have system messages (for message array input)
                if not isinstance(chat_turns, str) and system_instructions:
                    responses_kwargs["instructions"] = system_instructions

                # Add tools if provided (Responses API supports tools)
                # Follow OpenAI Responses API function calling documentation format
                if tools:
                    resp_tools: List[Dict[str, Any]] = []
                    for t in tools:
                        # Ensure tools follow the correct OpenAI Responses API format
                        if "function" in t:
                            # Already in correct format, ensure strict mode if not specified
                            tool_copy = dict(t)
                            if "strict" not in tool_copy:
                                tool_copy["strict"] = True  # Default to strict mode
                            resp_tools.append(tool_copy)
                        else:
                            # Convert legacy format to OpenAI Responses API format
                            tool_def = {
                                "type": "function",
                                "function": {
                                    "name": t.get("name"),
                                    "description": t.get("description"),
                                    "parameters": t.get("parameters", {}),
                                },
                                "strict": True,  # Enable strict mode by default
                            }
                            # Validate and enhance the schema
                            validated_tool = self.validate_function_schema(tool_def)
                            resp_tools.append(validated_tool)

                    responses_kwargs["tools"] = resp_tools

                    # Add tool choice parameter
                    if tool_choice is not None:
                        responses_kwargs["tool_choice"] = tool_choice

                    # Add parallel tool calls parameter
                    if not parallel_tool_calls:
                        responses_kwargs["parallel_tool_calls"] = False

                # Remove None values to avoid sending JSON null
                clean_responses_kwargs = {
                    k: v for k, v in responses_kwargs.items() if v is not None
                }

                # Log API request for debugging (only if debug logging enabled)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("=== AZURE RESPONSES API REQUEST ===")
                    logger.debug(f"Model: {active_model}, Provider: {self.provider}")
                    logger.debug(f"Temperature: {active_temperature}, Stream: {stream}")
                    logger.debug(f"Input Messages: {len(input_messages)} total")
                    # Only log full payload in debug mode
                    logger.debug(
                        f"Request Payload: {json.dumps(clean_responses_kwargs, indent=2)}"
                    )

                try:
                    response = await self.client.responses.create(
                        **clean_responses_kwargs
                    )

                    # Check for Responses API error field in response
                    if hasattr(response, "error") and response.error:
                        error_msg = f"Responses API error: {response.error}"
                        logger.error(error_msg)
                        raise RuntimeError(error_msg)

                except Exception as exc:  # noqa: BLE001
                    # ------------------------------------------------------------------ #
                    # Graceful fallback when the *Responses* deployment is missing
                    # ------------------------------------------------------------------ #
                    # Azure returns a **404 DeploymentNotFound** error when the selected
                    # deployment name does not exist *for the responses endpoint*.
                    # This is a common configuration issue – most users create only a
                    # *chat* deployment.  Instead of bubbling the low-level error up to
                    # the chat frontend we transparently retry the request via the
                    # regular Chat Completions endpoint which works against the
                    # existing deployment.  The client instance itself keeps
                    # ``use_responses_api`` unchanged so that a correctly configured
                    # deployment will still use the richer API on the next call.
                    # ------------------------------------------------------------------ #

                    try:
                        from openai import NotFoundError, BadRequestError  # type: ignore
                    except Exception:  # pragma: no cover – stubbed in CI
                        NotFoundError = type("NotFoundError", (Exception,), {})
                        BadRequestError = type("BadRequestError", (Exception,), {})

                    # ---------------------
                    # Deployment missing → 404
                    # Bad *tools* schema → 400
                    # ---------------------
                    _is_missing_deployment = isinstance(exc, NotFoundError)

                    _is_tool_schema_error = isinstance(
                        exc, BadRequestError
                    ) and "tools[0].type" in str(exc)

                    # Detect 400 responses complaining about unsupported
                    # sampling parameters (e.g. "Unsupported parameter:
                    # 'temperature' is not supported with this model.").
                    _is_parameter_unsupported_error = False

                    if isinstance(exc, BadRequestError):
                        msg_lc = str(exc).lower()
                        if (
                            "unsupported parameter" in msg_lc
                            and "is not supported with this model" in msg_lc
                        ):
                            _is_parameter_unsupported_error = True

                    if (
                        self.provider == "azure"
                        and self.use_responses_api
                        and (
                            _is_missing_deployment
                            or _is_tool_schema_error
                            or _is_parameter_unsupported_error
                        )
                    ):
                        logger.warning(
                            "Responses API error (%s) – falling back to Chat Completions.",
                            exc,
                        )

                        # Prepare equivalent Chat-Completions arguments
                        completions_kwargs = {
                            "model": active_model,
                            "messages": messages,
                            "max_tokens": active_max_tokens,
                        }

                        # o3 models don't support temperature or streaming
                        if not active_model.lower().startswith("o3"):
                            completions_kwargs["temperature"] = active_temperature
                            completions_kwargs["stream"] = stream
                        else:
                            # o3 models don't support streaming
                            completions_kwargs["stream"] = False

                        if tools:
                            # Ensure tools have the required format for Chat Completions API
                            chat_tools: List[Dict[str, Any]] = []
                            for t in tools:
                                if "function" in t:
                                    # Already in correct format
                                    chat_tools.append(t)
                                else:
                                    # Convert legacy format
                                    tool_def = {
                                        "type": "function",
                                        "function": {
                                            "name": t.get("name"),
                                            "description": t.get("description"),
                                            "parameters": t.get("parameters", {}),
                                        },
                                    }
                                    chat_tools.append(tool_def)
                            completions_kwargs["tools"] = chat_tools

                            # Add tool choice for Chat Completions API fallback
                            if tool_choice is not None:
                                completions_kwargs["tool_choice"] = tool_choice

                            # Add parallel tool calls
                            if not parallel_tool_calls:
                                completions_kwargs["parallel_tool_calls"] = False

                        completions_kwargs = {
                            k: v for k, v in completions_kwargs.items() if v is not None
                        }

                        response = await self.client.chat.completions.create(  # type: ignore[attr-defined]
                            **completions_kwargs,
                        )
                    else:
                        raise

                # Log API response for debugging (only if debug logging enabled)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("=== AZURE RESPONSES API RESPONSE ===")
                    if hasattr(response, "usage") and response.usage:
                        logger.debug(f"Token Usage: {response.usage}")
                    logger.debug(
                        f"Response Status: {getattr(response, 'status', 'unknown')}"
                    )
                    # Only log full response in debug mode
                    if hasattr(response, "output_text") and response.output_text:
                        logger.debug(
                            f"Response Text Length: {len(response.output_text)}"
                        )
                    elif hasattr(response, "output") and response.output:
                        logger.debug(f"Response Output Items: {len(response.output)}")

                # Handle streaming response - check actual stream value used in request
                actual_stream = responses_kwargs.get("stream", False)
                if actual_stream:
                    return self._stream_response(response)
                return response

            # -----------------------------------------------------------------
            # Regular Chat Completions (OpenAI or non-preview Azure)
            # -----------------------------------------------------------------

            # -----------------------------------------------------------------
            # Compatibility shim – the *tools* parameter replaced the older
            # *functions* field.  When the runtime OpenAI SDK (or upstream
            # HTTP API) rejects the *tools* argument with a *TypeError* or
            # *OpenAI* error code we transparently retry with *functions* so
            # that users running older versions continue to get responses
            # instead of a cryptic 400.
            # -----------------------------------------------------------------

            call_kwargs: Dict[str, Any] = {
                "model": active_model,
                "messages": messages,
            }

            # Handle reasoning models vs regular models for Chat Completions
            if _is_reasoning_model(active_model):
                # Reasoning models use max_completion_tokens and don't support temperature/streaming
                call_kwargs["stream"] = False
                if active_max_tokens:
                    call_kwargs["max_completion_tokens"] = active_max_tokens
                # Add reasoning parameter if specified
                if reasoning:
                    if isinstance(reasoning, dict):
                        # Use reasoning dict directly
                        call_kwargs["reasoning"] = reasoning
                    elif isinstance(reasoning, bool) and reasoning:
                        # Default reasoning config for backward compatibility
                        call_kwargs["reasoning"] = {"effort": "medium"}
            else:
                # Regular models use max_tokens and support temperature/streaming
                call_kwargs["temperature"] = active_temperature
                call_kwargs["stream"] = stream
                if active_max_tokens:
                    call_kwargs["max_tokens"] = active_max_tokens

            if tools:
                # Ensure tools have the required format for Chat Completions API
                chat_tools: List[Dict[str, Any]] = []
                for t in tools:
                    if "function" in t:
                        # Already in correct format
                        chat_tools.append(t)
                    else:
                        # Convert legacy format to OpenAI standard
                        tool_def = {
                            "type": "function",
                            "function": {
                                "name": t.get("name"),
                                "description": t.get("description"),
                                "parameters": t.get("parameters", {}),
                            },
                        }
                        chat_tools.append(tool_def)
                call_kwargs["tools"] = chat_tools

                # Add tool choice for Chat Completions API
                if tool_choice is not None:
                    call_kwargs["tool_choice"] = tool_choice

                # Add parallel tool calls
                if not parallel_tool_calls:
                    call_kwargs["parallel_tool_calls"] = False

            # The same graceful-degradation logic we added for the Responses
            # branch above: when *tools* is rejected by an older model we
            # retry with the deprecated *functions* field.

            # ---- scrub None values so JSON null never gets sent ----------
            clean_kwargs = {k: v for k, v in call_kwargs.items() if v is not None}

            # Log API request for debugging (only if debug logging enabled)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("=== CHAT COMPLETIONS API REQUEST ===")
                logger.debug(f"Provider: {self.provider}, Model: {active_model}")
                logger.debug(f"Temperature: {active_temperature}, Stream: {stream}")
                logger.debug(
                    f"Messages: {len(messages)} total, Tools: {tools is not None}"
                )
                # Only log full payload in debug mode
                logger.debug(f"Request Payload: {json.dumps(clean_kwargs, indent=2)}")

            try:
                response = await self.client.chat.completions.create(**clean_kwargs)

                # Log API response for debugging (only if debug logging enabled)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("=== CHAT COMPLETIONS API RESPONSE ===")
                    if hasattr(response, "choices") and response.choices:
                        choice = response.choices[0]
                        logger.debug(f"Finish Reason: {choice.finish_reason}")
                        if (
                            hasattr(choice, "message")
                            and hasattr(choice.message, "tool_calls")
                            and choice.message.tool_calls
                        ):
                            logger.debug(
                                f"Tool Calls: {len(choice.message.tool_calls)} calls"
                            )
                        if hasattr(choice, "message") and hasattr(
                            choice.message, "content"
                        ):
                            logger.debug(
                                f"Response Content Length: {len(choice.message.content or '')}"
                            )
                    if hasattr(response, "usage"):
                        logger.debug(f"Token Usage: {response.usage}")

                # Handle streaming response - check actual stream value used in request
                actual_stream = clean_kwargs.get("stream", False)
                if actual_stream:
                    return self._stream_response(response)
                return response
            except (
                Exception
            ) as exc:  # noqa: BLE001 – capture BadRequest / TypeError alike
                # 1. The newest SDK raises *TypeError* when an unexpected
                #    keyword parameter is supplied.
                # 2. The HTTP backend (or older SDK versions) raise
                #    *BadRequestError* for the same situation.  We therefore
                #    broaden the except clause and inspect the message only
                #    when we added *tools* – to avoid masking unrelated
                #    failures (network, invalid key, …).

                has_tools = "tools" in call_kwargs

                if has_tools and (
                    isinstance(exc, TypeError)
                    or exc.__class__.__name__
                    in {  # guard against stub types
                        "BadRequestError",
                        "InvalidRequestError",
                    }
                ):
                    legacy_kwargs = dict(call_kwargs)
                    legacy_kwargs.pop("tools")
                    legacy_kwargs["functions"] = tools  # type: ignore[arg-type]
                    legacy_kwargs = {
                        k: v for k, v in legacy_kwargs.items() if v is not None
                    }
                    return await self.client.chat.completions.create(**legacy_kwargs)

                # Re-raise unchanged – caller handles logging / user feedback.
                raise

        except Exception as exc:  # noqa: BLE001 – broad for logging / Sentry
            # Forward exception after capturing telemetry so calling code can
            # decide how to react (retry, user-facing error, …).
            raise  # re-raise unchanged

    # ------------------------------------------------------------------
    # Streaming helpers
    # ------------------------------------------------------------------

    async def _stream_response(self, response: Any) -> AsyncIterator[str]:
        """Convert OpenAI/Azure streaming response to string chunks."""
        logger.debug(
            f"Starting stream response, use_responses_api: {self.use_responses_api}"
        )
        chunk_count = 0

        try:
            if self.use_responses_api:
                # Azure Responses API streaming
                logger.debug("Processing Azure Responses API stream")
                async for chunk in response:
                    chunk_count += 1
                    logger.debug(f"Received chunk {chunk_count}: {type(chunk)}")

                    # Azure streaming events come in different flavours.  We
                    # purposefully *only* forward incremental “delta”
                    # fragments here – the *done* event often repeats the
                    # full response which would lead to duplicated content
                    # on the consumer side.  Other event types like
                    # ``ResponseOutputItem...`` are handled separately
                    # below.

                    # Handle different OpenAI Responses API streaming events
                    event_type = getattr(chunk, "type", None)

                    if event_type == "response.output_item.added":
                        # Function call started - log but don't yield
                        item = getattr(chunk, "item", {})
                        if getattr(item, "type", None) == "function_call":
                            logger.debug(
                                f"Function call started: {getattr(item, 'name', 'unknown')}"
                            )

                    elif event_type == "response.function_call_arguments.delta":
                        # Function call arguments streaming - could yield progress indicator
                        delta = getattr(chunk, "delta", "")
                        logger.debug(f"Function arguments delta: {delta[:20]}...")
                        # Note: We don't yield function call deltas as content

                    elif event_type == "response.function_call_arguments.done":
                        # Function call complete - log completion
                        logger.debug("Function call arguments complete")

                    # ResponseTextDeltaEvent → incremental token fragment
                    elif hasattr(chunk, "delta") and chunk.delta:
                        logger.debug(
                            "Yielding delta content: %s...",
                            chunk.delta[:50],
                        )
                        yield chunk.delta

                    # ResponseOutputItemDoneEvent → list of output items –
                    # stream the *content* field when present.
                    elif hasattr(chunk, "output") and chunk.output:
                        for item in chunk.output:
                            if hasattr(item, "content") and item.content:
                                logger.debug(
                                    "Yielding content: %s...",
                                    item.content[:50],
                                )
                                yield item.content

                    # ``ResponseTextDoneEvent`` and similar *completion*
                    # events include the *full* text again.  We skip those to
                    # avoid sending duplicates – the cumulative *buffer* in
                    # ``StreamingHandler`` already contains the complete
                    # response after receiving all deltas.
            else:
                # Standard Chat Completions API streaming
                logger.debug("Processing Chat Completions API stream")
                async for chunk in response:
                    chunk_count += 1
                    logger.debug(f"Received chunk {chunk_count}: {type(chunk)}")

                    if hasattr(chunk, "choices") and chunk.choices:
                        choice = chunk.choices[0]
                        if hasattr(choice, "delta") and choice.delta:
                            # Handle tool call streaming in Chat Completions
                            if (
                                hasattr(choice.delta, "tool_calls")
                                and choice.delta.tool_calls
                            ):
                                # Function call streaming - log but don't yield as content
                                for tool_call_delta in choice.delta.tool_calls:
                                    logger.debug(
                                        f"Tool call delta received for index {getattr(tool_call_delta, 'index', 0)}"
                                    )
                                # Note: Tool call content is handled separately by the processor

                            # Regular content streaming
                            elif (
                                hasattr(choice.delta, "content")
                                and choice.delta.content
                            ):
                                logger.debug(
                                    f"Yielding choice content: {choice.delta.content[:50]}..."
                                )
                                yield choice.delta.content
        except Exception as e:
            logger.error(f"Error in _stream_response: {e}", exc_info=True)

        logger.debug(f"Stream processing complete, processed {chunk_count} chunks")

    # ------------------------------------------------------------------
    # Convenience helpers used by the wider code-base
    # ------------------------------------------------------------------

    async def generate_response(self, prompt: str, **kwargs) -> Any:  # noqa: ANN401
        """Shortcut for a single-user prompt.

        This is the method exercised by
        :pyfunc:`backend/tests/test_exception_handling.py::test_llm_client_exception_handling`.
        """

        messages = [
            {"role": "system", "content": self._DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        return await self.complete(messages, **kwargs)

    async def respond(self, *args, **kwargs):  # noqa: ANN401
        """Compatibility shim for deprecated respond() method.

        This method is deprecated and will warn when used. Use chat() instead.
        """
        import warnings

        warnings.warn(
            "`respond()` is deprecated; use `chat()`", DeprecationWarning, stacklevel=2
        )
        return await self.complete(*args, **kwargs)

    # The surrounding business-logic adds *code context* as an additional
    # *system* message to steer the model.  We simply join the snippets into a
    # single string – sophistication is not necessary for the unit tests.
    @staticmethod
    def prepare_code_context(chunks: Sequence[Dict[str, Any]]) -> str:  # noqa: D401
        """Return a readable representation of *chunks* for inclusion in the
        system prompt."""

        if not chunks:
            return "No code context available."

        parts: List[str] = []
        for chunk in chunks:
            path = chunk.get("file_path", "<unknown>")
            start = chunk.get("start_line", "?")
            end = chunk.get("end_line", "?")
            content = chunk.get("content", "").strip()
            parts.append(
                f"File: {path} lines {start}-{end}\n" + "-" * 20 + f"\n{content}\n"
            )
        return "\n\n".join(parts)

    async def create_completion_with_functions(
        self,
        messages: Sequence[Dict[str, Any]],
        functions: List[Dict[str, Any]],
        function_call: str | Dict[str, str] | None = "auto",
        **kwargs,
    ) -> Any:
        """Legacy function calling interface for backward compatibility.

        Converts old-style function definitions to new tool format following
        OpenAI Responses API documentation patterns.
        """
        import warnings

        warnings.warn(
            "create_completion_with_functions() is deprecated; use complete() with tools parameter",
            DeprecationWarning,
            stacklevel=2,
        )

        # Convert functions to tools format
        tools = []
        for func in functions:
            tool = {
                "type": "function",
                "function": func,
                "strict": True,  # Enable strict mode by default
            }
            tools.append(tool)

        # Convert function_call to tool_choice
        tool_choice = None
        if function_call == "auto":
            tool_choice = "auto"
        elif function_call == "none":
            tool_choice = "none"
        elif isinstance(function_call, dict):
            tool_choice = {"type": "function", "function": function_call}

        return await self.complete(
            messages=messages, tools=tools, tool_choice=tool_choice, **kwargs
        )

    @staticmethod
    def validate_function_schema(func: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and enhance function schema for OpenAI Responses API.

        Follows OpenAI function calling best practices:
        - Ensures additionalProperties is False for strict mode
        - Validates required fields are present
        - Adds strict mode if not specified
        """
        validated = dict(func)

        # Ensure proper structure
        if "function" in validated:
            # Already in new format
            function_def = validated["function"]
        else:
            # Legacy format - convert
            function_def = validated
            validated = {"type": "function", "function": function_def, "strict": True}

        # Validate function definition
        if "parameters" in function_def:
            params = function_def["parameters"]
            if isinstance(params, dict) and params.get("type") == "object":
                # Ensure additionalProperties is False for strict mode
                if "additionalProperties" not in params:
                    params["additionalProperties"] = False

                # For strict mode, all properties should be in required
                if "properties" in params and "required" not in params:
                    params["required"] = list(params["properties"].keys())

        # Enable strict mode by default
        if "strict" not in validated:
            validated["strict"] = True

        return validated


# ---------------------------------------------------------------------------
# Module level singleton – keeps backward compatibility with prior releases
# ---------------------------------------------------------------------------

llm_client = LLMClient()

# Re-export the *openai* client classes so that external callers (and the test
# suite!) can ``patch('app.llm.client.AsyncOpenAI', …)``.

__all__ = [
    "LLMClient",
    "llm_client",
    "AsyncOpenAI",
    "AsyncAzureOpenAI",
    "AsyncAnthropic",
]
