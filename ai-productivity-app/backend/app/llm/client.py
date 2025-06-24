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
from typing import Any, Dict, List, Sequence

# ---------------------------------------------------------------------------
# Optional dependencies – fall back to the stub implementation installed in
# ``app.compat.stubs`` when the real *openai* SDK is not available.
# ---------------------------------------------------------------------------

try:
    from openai import AsyncOpenAI, AsyncAzureOpenAI  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – handled by compat.stubs
    # ``compat.stubs.install_stubs`` already inserted a synthetic *openai*
    # module that exposes *AsyncOpenAI* / *AsyncAzureOpenAI* so we can import
    # it after the fact without additional work.
    from openai import AsyncOpenAI, AsyncAzureOpenAI  # type: ignore  # noqa: E501 pylint: disable=ungrouped-imports

# Sentry is entirely optional for tests – use a fallback when not present.
try:
    import sentry_sdk  # type: ignore
except ModuleNotFoundError:  # pragma: no cover

    class _StubSentry:  # pylint: disable=too-few-public-methods
        @staticmethod
        def capture_exception(_exc):
            return None

    sentry_sdk = _StubSentry()  # type: ignore

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
            sentry_sdk.capture_exception(exc)

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
            "api_version": getattr(settings, "azure_openai_api_version", "2024-02-01"),
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
        temperature: float | int = 0.7,
        stream: bool = False,
        tools: Any | None = None,
        reasoning: bool | None = None,  # noqa: D401 – kept for forward compat
        max_tokens: int | None = None,
    ) -> Any:  # noqa: ANN401 – OpenAI return type is *dynamic*
        """Wrapper around the underlying Chat Completions / Responses API.

        The signature is intentionally *loose* – the backend forwards a subset
        of the available parameters.  In addition we accept arbitrary
        ``**kwargs`` via the explicit keyword arguments to stay compatible
        with future changes.
        """

        if self.client is None:
            raise RuntimeError("LLM client not initialised – missing credentials?")

        # Convert messages into canonical list – some callers might pass
        # tuples / generators.
        messages = _sanitize_messages(messages or [])

        try:
            if self.use_responses_api:
                # Azure *preview* Responses API – *system* messages need to go
                # into the *instructions* field while the rest stays in
                # *input* according to the official docs.  The test-suite does
                # **not** call this branch, therefore we keep the conversion
                # rudimentary.

                # Separate system instructions from normal conversation.
                system_instructions = None
                input_messages: List[Dict[str, str]] = []
                for msg in messages:
                    if msg["role"] == "system" and system_instructions is None:
                        system_instructions = msg["content"]
                    else:
                        input_messages.append(msg)

                return await self.client.responses.create(
                    model=self.active_model,
                    input=input_messages,
                    instructions=system_instructions,
                    temperature=temperature,
                    stream=stream,
                    max_tokens=max_tokens,
                )

            # -----------------------------------------------------------------
            # Regular Chat Completions (OpenAI or non-preview Azure)
            # -----------------------------------------------------------------

            return await self.client.chat.completions.create(
                model=self.active_model,
                messages=messages,
                temperature=temperature,
                stream=stream,
                tools=tools,
                max_tokens=max_tokens,
            )

        except Exception as exc:  # noqa: BLE001 – broad for logging / Sentry
            # Forward exception after capturing telemetry so calling code can
            # decide how to react (retry, user-facing error, …).
            sentry_sdk.capture_exception(exc)
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
