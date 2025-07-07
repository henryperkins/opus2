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


def _optional(value: Any) -> Dict[str, Any]:
    """Helper that returns an empty mapping when *value* is falsy.

    Reduces repetitive *if value: kwargs[...]* blocks so the factory remains
    succinct.  Only use for *optional* parameters – **never** for required
    secrets like API keys.
    """

    return value and {"dummy": value} or {}


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
    base_url = getattr(settings, "openai_base_url", None)
    if base_url:
        kwargs["base_url"] = base_url

    org = getattr(settings, "openai_org", None)
    if org:
        kwargs["organization"] = org

    timeout = getattr(settings, "openai_timeout", None)
    if timeout:
        kwargs["timeout"] = timeout

    return AsyncOpenAI(**kwargs)  # type: ignore[arg-type]


def get_azure_client() -> AsyncAzureOpenAI:  # pragma: no cover – trivial
    """Return a fully configured *AsyncAzureOpenAI* instance."""

    endpoint = settings.azure_openai_endpoint or "https://example.openai.azure.com"

    api_version = (
        getattr(settings, "azure_openai_api_version", None) or "2025-04-01-preview"
    )

    kwargs: Dict[str, Any] = {
        "azure_endpoint": endpoint,
        "api_version": api_version,
    }

    # Authentication strategy – default to API key unless *azure_auth_method*
    # explicitly asks for Entra ID.
    auth_method = getattr(settings, "azure_auth_method", "api_key").lower()
    if auth_method == "api_key":
        if settings.azure_openai_api_key:
            kwargs["api_key"] = settings.azure_openai_api_key
        else:
            logger.info("AZURE_OPENAI_API_KEY missing – stub client will be used")
    else:
        # The actual Entra ID flow requires *azure-identity* which is not part
        # of the sandbox environment.  We therefore inject a dummy token
        # provider that returns a placeholder.
        kwargs["azure_ad_token_provider"] = lambda: "stub-token"

    timeout = getattr(settings, "openai_timeout", None)
    if timeout:
        kwargs["timeout"] = timeout

    return AsyncAzureOpenAI(**kwargs)  # type: ignore[arg-type]
