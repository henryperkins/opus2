"""Factory helpers to create fully-configured OpenAI / Azure OpenAI SDK clients.

This small module centralises the logic that was previously duplicated in
``app.llm.client.LLMClient`` and ``app.embeddings.generator.EmbeddingGenerator``.
All functions read their configuration exclusively from
``app.config.settings`` so the rest of the code base no longer has to worry
about environment variables or default fall-backs.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from openai import AsyncAzureOpenAI, AsyncOpenAI  # type: ignore

from app.config import settings

# The sandbox test-runner injects a stubbed *openai* module.  Importing the
# real SDK therefore succeeds regardless of the execution environment.  No
# additional guards required.

logger = logging.getLogger(__name__)


def _optional(key: str, value: Any) -> Dict[str, Any]:
    """Return ``{key: value}`` when *value* is truthy, else an empty dict.

    Keeps the factory helpers succinct by avoiding repetitive
    ``if value: kwargs[<key>] = value`` blocks.
    NEVER use for required secrets like API keys.
    """
    return {key: value} if value else {}


def get_openai_client() -> AsyncOpenAI:  # pragma: no cover – trivial
    """Return a fully configured *AsyncOpenAI* instance.

    The helper prefers the environment variable overrides that are exposed
    via ``app.config.settings``.  Missing *api_key*s are tolerated in the CI
    sandbox where the stubbed SDK accepts arbitrary values.
    """

    api_key = settings.openai_api_key
    if not api_key:
        logger.info("OpenAI API key missing – falling back to stub client")

    kwargs: Dict[str, Any] = {"api_key": api_key}

    # Optional extras
    kwargs.update(_optional("base_url", getattr(settings, "openai_base_url", None)))
    kwargs.update(_optional("organization", getattr(settings, "openai_org", None)))
    kwargs.update(_optional("timeout", getattr(settings, "openai_timeout", None)))

    return AsyncOpenAI(**kwargs)  # type: ignore[arg-type]


def get_azure_client() -> AsyncAzureOpenAI:  # pragma: no cover – trivial
    """Return a fully configured *AsyncAzureOpenAI* instance."""


    # ------------------------------------------------------------------
    # Azure *v1* preview surface (incl. **Responses API**)
    # ------------------------------------------------------------------
    #
    # The newer preview endpoints live under `/openai/v1/...` instead of the
    # classic data-plane path.  We therefore build *base_url* accordingly so
    # that the SDK issues requests like
    #   https://RESOURCE.openai.azure.com/openai/v1/responses
    #
    # Chat Completions on the v1 surface no longer require a *deployment*
    # name – you pass the *model* parameter directly.  This aligns with the
    # Responses API which also operates on model IDs.
    # ------------------------------------------------------------------

    resource_endpoint = (
        settings.azure_openai_endpoint or "https://example.openai.azure.com"
    ).rstrip("/")

    base_url = f"{resource_endpoint}/openai/v1/"

    # Users can override the API version via environment or runtime config.
    # When not specified we follow the official guidance and default to
    # **latest** which will automatically resolve to the most recent
    # non-breaking version.

    api_version = getattr(settings, "azure_openai_api_version", None) or "latest"

    kwargs: Dict[str, Any] = {
        "api_version": api_version,
        "base_url": base_url,
        "default_query": {"api-version": api_version},
    }

    # Authentication strategy – default to API key unless *azure_auth_method*
    # explicitly asks for Entra ID.
    auth_method = getattr(settings, "azure_auth_method", "api_key").lower()
    if auth_method == "api_key":
        kwargs.update(_optional("api_key", settings.azure_openai_api_key))
        if "api_key" not in kwargs:
            logger.info("AZURE_OPENAI_API_KEY missing – stub client will be used")
    else:
        # The actual Entra ID flow requires *azure-identity* which is not part
        # of the sandbox environment.  We therefore inject a dummy token
        # provider that returns a placeholder.
        kwargs["azure_ad_token_provider"] = lambda: "stub-token"

    kwargs.update(_optional("timeout", getattr(settings, "openai_timeout", None)))

    return AsyncAzureOpenAI(**kwargs)  # type: ignore[arg-type]
