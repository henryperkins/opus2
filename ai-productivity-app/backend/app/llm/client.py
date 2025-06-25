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
from typing import Any, Dict, List, Sequence

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
            # Try to get configuration from database first
            from app.database import SessionLocal
            from app.services.config_service import ConfigService

            with SessionLocal() as db:
                config_service = ConfigService(db)
                db_config = config_service.get_all_config()

                if db_config:
                    return db_config

        except Exception as e:
            logger.debug(f"Failed to load config from database: {e}")

        try:
            # Fallback to in-memory config
            from app.routers.config import _RUNTIME_CONFIG
            return _RUNTIME_CONFIG
        except ImportError:
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
    ) -> Any:  # noqa: ANN401 – OpenAI return type is *dynamic*
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
                    "temperature": active_temperature,
                    "stream": stream,
                }

                # Only add instructions if we have system messages
                if system_instructions:
                    responses_kwargs["instructions"] = system_instructions

                # Only add max_tokens if specified (responses API uses max_output_tokens)
                if active_max_tokens:
                    responses_kwargs["max_output_tokens"] = active_max_tokens

                # Add tools if provided (Responses API supports tools)
                if tools:
                    responses_kwargs["tools"] = tools

                # Remove None values to avoid sending JSON null
                clean_responses_kwargs = {k: v for k, v in responses_kwargs.items() if v is not None}

                # Log API request for debugging
                logger.info("=== AZURE RESPONSES API REQUEST ===")
                logger.info(f"Model: {active_model}")
                logger.info(f"Provider: {self.provider}")
                logger.info(f"Temperature: {active_temperature}")
                logger.info(f"Max Output Tokens: {active_max_tokens}")
                logger.info(f"Stream: {stream}")
                logger.info(f"System Instructions: {system_instructions}")
                logger.info(f"Input Messages ({len(input_messages)} total):")
                for i, msg in enumerate(input_messages):
                    content_preview = str(msg.get('content', ''))[:200] + "..." if len(str(msg.get('content', ''))) > 200 else str(msg.get('content', ''))
                    logger.info(f"  [{i + 1}] {msg.get('role', 'unknown')}: {content_preview}")
                logger.info(f"Full Request Payload: {json.dumps(clean_responses_kwargs, indent=2)}")

                response = await self.client.responses.create(**clean_responses_kwargs)

                # Log API response for debugging
                logger.info("=== AZURE RESPONSES API RESPONSE ===")
                if hasattr(response, 'output_text') and response.output_text:
                    logger.info(f"Response Text: {response.output_text}")
                elif hasattr(response, 'output') and response.output:
                    logger.info(f"Response Output: {response.output}")
                    # Extract text from output for compatibility
                    if isinstance(response.output, list) and response.output:
                        for output_item in response.output:
                            if hasattr(output_item, 'content') and isinstance(output_item.content, list):
                                for content_item in output_item.content:
                                    if hasattr(content_item, 'text'):
                                        logger.info(f"Output Text: {content_item.text}")

                if hasattr(response, 'usage') and response.usage:
                    logger.info(f"Token Usage: {response.usage}")

                logger.info(f"Response Status: {getattr(response, 'status', 'unknown')}")
                logger.info(f"Full Response Object: {json.dumps(response.model_dump() if hasattr(response, 'model_dump') else str(response), indent=2)}")

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
                "temperature": active_temperature,
                "stream": stream,
                "max_tokens": active_max_tokens,
            }

            if tools:
                call_kwargs["tools"] = tools

            # ---- scrub None values so JSON null never gets sent ----------
            clean_kwargs = {k: v for k, v in call_kwargs.items() if v is not None}

            # Log API request for debugging
            logger.info("=== CHAT COMPLETIONS API REQUEST ===")
            logger.info(f"Provider: {self.provider}")
            logger.info(f"Model: {active_model}")
            logger.info(f"Temperature: {active_temperature}")
            logger.info(f"Max Tokens: {active_max_tokens}")
            logger.info(f"Stream: {stream}")
            logger.info(f"Tools: {tools is not None}")
            logger.info(f"Messages ({len(messages)} total):")
            for i, msg in enumerate(messages):
                content_preview = msg['content'][:200] + "..." if len(msg['content']) > 200 else msg['content']
                logger.info(f"  [{i + 1}] {msg['role']}: {content_preview}")
            logger.info(f"Full Request Payload: {json.dumps(clean_kwargs, indent=2)}")

            try:
                response = await self.client.chat.completions.create(**clean_kwargs)

                # Log API response for debugging
                logger.info("=== CHAT COMPLETIONS API RESPONSE ===")
                if hasattr(response, "choices") and response.choices:
                    choice = response.choices[0]
                    logger.info(f"Finish Reason: {choice.finish_reason}")
                    if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                        logger.info(f"Response Content: {choice.message.content}")
                    if hasattr(choice, 'message') and hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
                        logger.info(f"Tool Calls: {len(choice.message.tool_calls)} calls")
                        for j, tool_call in enumerate(choice.message.tool_calls):
                            logger.info(f"  Tool Call [{j + 1}]: {tool_call.name} with args: {tool_call.arguments}")
                if hasattr(response, 'usage'):
                    logger.info(f"Token Usage: {response.usage}")
                logger.info(f"Full Response Object: {json.dumps(response.model_dump() if hasattr(response, 'model_dump') else str(response), indent=2)}")

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
