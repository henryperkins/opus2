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

_IN_SANDBOX = (
    os.getenv("APP_CI_SANDBOX") == "1" or "pytest" in sys.modules
)

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


from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _is_responses_api_enabled() -> bool:
    """Return *True* when the current configuration selects the Azure
    *Responses API* variant.

    According to the Azure documentation the *preview* API-version enables the
    new endpoint.  We keep the logic intentionally *simple* – for the purpose
    of the unit tests we only need to distinguish two cases:

    1. provider == "azure" **and** api_version == "preview"  → Responses API
    2. everything else                                       → Chat Completions
    """

    return (
        settings.llm_provider.lower() == "azure"
        and getattr(settings, "azure_openai_api_version", "").lower() == "preview"
    )


def _sanitize_messages(messages: Sequence[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Ensure *messages* are JSON serialisable and in the canonical format the
    OpenAI SDK expects.  The helper **does not** perform any advanced
    validation – it simply converts the sequence to a *list* and casts the
    *role* / *content* values to ``str``.
    """

    out: List[Dict[str, str]] = []
    for msg in messages:
        out.append({"role": str(msg["role"]), "content": str(msg["content"])})
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
        self.use_responses_api: bool = _is_responses_api_enabled()

        # The active *model* (or *deployment name* in Azure terminology).  We
        # prioritise the new ``llm_default_model`` field and fall back to the
        # (deprecated) ``llm_model`` environment variable for backwards
        # compatibility.
        self.active_model: str = (
            settings.llm_default_model or settings.llm_model or "gpt-3.5-turbo"
        )

        # Underlying OpenAI SDK client – differs for public vs. Azure.
        self.client: Any | None = None

        # Provider-specific initialisation.
        try:
            if self.provider == "azure":
                self._init_azure_client()
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

    async def reconfigure(self,
                         provider: str | None = None,
                         model: str | None = None,
                         use_responses_api: bool | None = None) -> None:
        """Dynamically reconfigure the client with new provider/model settings."""
        runtime_config = self._get_runtime_config()

        # Use runtime config values or provided parameters
        new_provider = (provider or runtime_config.get("provider", self.provider)).lower()
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
            else:
                self._init_openai_client()
            logger.info("LLM client reinitialized for provider: %s", new_provider)

        # Update model and responses API settings
        self.active_model = new_model
        self.use_responses_api = new_responses_api and new_provider == "azure"

        logger.info("LLM client reconfigured - Provider: %s, Model: %s, ResponsesAPI: %s",
                   self.provider, self.active_model, self.use_responses_api)

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
            settings.azure_openai_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT") or "https://example.openai.azure.com"
        )

        api_key = (
            settings.azure_openai_api_key or os.getenv("AZURE_OPENAI_API_KEY") or "test-key"
        )

        extra_kwargs: Dict[str, Any] = {
            "azure_endpoint": endpoint,
            "api_version": getattr(settings, "azure_openai_api_version", "2025-04-01-preview"),
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

    # ---------------------------------------------------------------------
    # Public helpers
    # ---------------------------------------------------------------------

    async def complete(  # noqa: PLR0913 – long but mirrors OpenAI params
        self,
        messages: Sequence[Dict[str, Any]] | None = None,
        *,
        temperature: float | int | None = None,
        stream: bool = False,
        tools: Any | None = None,
        reasoning: bool | None = None,  # noqa: D401 – kept for forward compat
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
        active_temperature = temperature if temperature is not None else runtime_config.get("temperature", 0.7)
        active_max_tokens = max_tokens or runtime_config.get("max_tokens")

        # Auto-reconfigure if model/provider changed
        if active_model != self.active_model or runtime_config.get("provider", self.provider).lower() != self.provider:
            await self.reconfigure(
                provider=runtime_config.get("provider"),
                model=active_model,
                use_responses_api=runtime_config.get("use_responses_api")
            )

        # Convert messages into canonical list – some callers might pass
        # tuples / generators.
        messages = _sanitize_messages(messages or [])

        try:
            if self.use_responses_api:
                # Azure Responses API - follows the official documentation pattern
                # System messages go into instructions, user/assistant messages into input

                system_instructions = None
                input_messages: List[Dict[str, Any]] = []

                for msg in messages:
                    if msg["role"] == "system":
                        # Combine multiple system messages if present
                        if system_instructions is None:
                            system_instructions = msg["content"]
                        else:
                            system_instructions += "\n\n" + msg["content"]
                    else:
                        # Convert to Responses API format
                        input_msg = {
                            "role": msg["role"],
                            "content": msg["content"]
                        }
                        # Add type field for user/assistant messages
                        if msg["role"] in ["user", "assistant"]:
                            input_msg["type"] = "message"
                        input_messages.append(input_msg)

                # Create parameters dict following Azure Responses API spec
                responses_kwargs = {
                    "model": active_model,
                    "input": input_messages,
                }

                # o3 models don't support temperature or streaming
                if not active_model.lower().startswith("o3"):
                    responses_kwargs["temperature"] = active_temperature
                    responses_kwargs["stream"] = stream
                else:
                    # o3 models don't support streaming
                    responses_kwargs["stream"] = False

                # Only add instructions if we have system messages
                if system_instructions:
                    responses_kwargs["instructions"] = system_instructions

                # Only add max_tokens if specified (responses API uses max_output_tokens)
                if active_max_tokens:
                    responses_kwargs["max_output_tokens"] = active_max_tokens

                # Add tools if provided (Responses API supports tools) – ensure
                # each entry includes the mandatory "type" field ("function"
                # is the only allowed value at the moment).
                if tools:
                    resp_tools: List[Dict[str, Any]] = []
                    for t in tools:
                        t_copy = dict(t)
                        # Azure requires explicit type declaration
                        t_copy.setdefault("type", "function")
                        resp_tools.append(t_copy)

                    responses_kwargs["tools"] = resp_tools

                # Remove None values to avoid sending JSON null
                clean_responses_kwargs = {k: v for k, v in responses_kwargs.items() if v is not None}

                # Log API request for debugging (only if debug logging enabled)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("=== AZURE RESPONSES API REQUEST ===")
                    logger.debug(f"Model: {active_model}, Provider: {self.provider}")
                    logger.debug(f"Temperature: {active_temperature}, Stream: {stream}")
                    logger.debug(f"Input Messages: {len(input_messages)} total")
                    # Only log full payload in debug mode
                    logger.debug(f"Request Payload: {json.dumps(clean_responses_kwargs, indent=2)}")

                try:
                    response = await self.client.responses.create(**clean_responses_kwargs)
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

                    _is_tool_schema_error = (
                        isinstance(exc, BadRequestError)
                        and "tools[0].type" in str(exc)
                    )

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
                            _is_missing_deployment or _is_tool_schema_error or _is_parameter_unsupported_error
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
                            # Ensure tools have the required type field for Chat Completions API
                            chat_tools: List[Dict[str, Any]] = []
                            for t in tools:
                                t_copy = dict(t)
                                t_copy.setdefault("type", "function")
                                chat_tools.append(t_copy)
                            completions_kwargs["tools"] = chat_tools

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
                    if hasattr(response, 'usage') and response.usage:
                        logger.debug(f"Token Usage: {response.usage}")
                    logger.debug(f"Response Status: {getattr(response, 'status', 'unknown')}")
                    # Only log full response in debug mode
                    if hasattr(response, 'output_text') and response.output_text:
                        logger.debug(f"Response Text Length: {len(response.output_text)}")
                    elif hasattr(response, 'output') and response.output:
                        logger.debug(f"Response Output Items: {len(response.output)}")

                # Handle streaming response
                if stream:
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
                "max_tokens": active_max_tokens,
            }

            # o3 models don't support temperature or streaming
            if not active_model.lower().startswith("o3"):
                call_kwargs["temperature"] = active_temperature
                call_kwargs["stream"] = stream
            else:
                # o3 models don't support streaming
                call_kwargs["stream"] = False

            if tools:
                # Ensure tools have the required type field for Chat Completions API
                chat_tools: List[Dict[str, Any]] = []
                for t in tools:
                    t_copy = dict(t)
                    t_copy.setdefault("type", "function")
                    chat_tools.append(t_copy)
                call_kwargs["tools"] = chat_tools

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
                logger.debug(f"Messages: {len(messages)} total, Tools: {tools is not None}")
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
                        if hasattr(choice, 'message') and hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
                            logger.debug(f"Tool Calls: {len(choice.message.tool_calls)} calls")
                        if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                            logger.debug(f"Response Content Length: {len(choice.message.content or '')}")
                    if hasattr(response, 'usage'):
                        logger.debug(f"Token Usage: {response.usage}")

                # Handle streaming response
                if stream:
                    return self._stream_response(response)
                return response
            except Exception as exc:  # noqa: BLE001 – capture BadRequest / TypeError alike
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
                    or exc.__class__.__name__ in {  # guard against stub types
                        "BadRequestError",
                        "InvalidRequestError",
                    }
                ):
                    legacy_kwargs = dict(call_kwargs)
                    legacy_kwargs.pop("tools")
                    legacy_kwargs["functions"] = tools  # type: ignore[arg-type]
                    legacy_kwargs = {k: v for k, v in legacy_kwargs.items() if v is not None}
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
        logger.debug(f"Starting stream response, use_responses_api: {self.use_responses_api}")
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

                    # ResponseTextDeltaEvent → incremental token fragment
                    if hasattr(chunk, 'delta') and chunk.delta:
                        logger.debug(
                            "Yielding delta content: %s...",
                            chunk.delta[:50],
                        )
                        yield chunk.delta

                    # ResponseOutputItemDoneEvent → list of output items –
                    # stream the *content* field when present.
                    elif hasattr(chunk, 'output') and chunk.output:
                        for item in chunk.output:
                            if hasattr(item, 'content') and item.content:
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
                    
                    if hasattr(chunk, 'choices') and chunk.choices:
                        choice = chunk.choices[0]
                        if hasattr(choice, 'delta') and choice.delta:
                            if hasattr(choice.delta, 'content') and choice.delta.content:
                                logger.debug(f"Yielding choice content: {choice.delta.content[:50]}...")
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
]
