# backend/app/routers/config.py
"""Runtime configuration & metadata endpoints.

The frontend needs to know which LLM *providers* and *models* are available in
the current deployment so that it can render a suitable selection component
and construct the correct API requests.

This router exposes a **read-only** endpoint that returns a list of supported
providers together with their respective model-catalogue.  We derive the data
from static look-up tables to avoid an additional network request to the OpenAI
API on every page-load.
"""

from fastapi import APIRouter

from app.config import settings


router = APIRouter(prefix="/api/config", tags=["config"])


# ---------------------------------------------------------------------------
# Static provider → models mapping
# ---------------------------------------------------------------------------

# NOTE: The list purposefully contains **only** the mainstream ChatCompletion
# models that are fully supported by the application.  Power-users can still
# specify arbitrary deployment names via the environment variable
# ``LLM_MODEL``.  Exposing *every* single variant here would clutter the UI
# without adding tangible benefits.


_OPENAI_CHAT_MODELS = [
    "gpt-4o-mini",  # 2025-05 preview model family (fast, cost-effective)
    "gpt-4o",       # omni model (multimodal)
    "gpt-4-turbo",  # 2024-04 cost-optimised GPT-4
    "gpt-4",        # legacy 8k context
    "gpt-3.5-turbo-0125",
    "gpt-3.5-turbo-1106",
    "gpt-3.5-turbo-0613",
]


_AZURE_CHAT_MODELS = [
    # For Azure the *model* parameter equals the **deployment name** which is
    # user defined.  We therefore expose a set of sensible *placeholders* that
    # an administrator can map to their concrete deployment names.  The
    # frontend usually provides a text-input when "azure" is selected so that
    # operators can fill in the correct value.
    "gpt-4o",  # or your deployment named "gpt4o-general"
    "gpt-4-turbo",
    "gpt-4",
    "gpt-35-turbo",  # Azure naming convention for GPT-3.5
]


@router.get("", summary="Return supported LLM providers and models")
async def get_config():  # noqa: D401
    """Return a JSON object with provider → model mapping."""

    return {
        "providers": {
            "openai": {
                "chat_models": _OPENAI_CHAT_MODELS,
                "embedding_models": [
                    "text-embedding-3-small",
                    "text-embedding-3-large",
                    "text-embedding-ada-002",
                ],
            },
            "azure": {
                "chat_models": _AZURE_CHAT_MODELS,
                # The embedding model dimension identical to the public
                # endpoint – only the *deployment name* differs.
                "embedding_models": [
                    "text-embedding-ada-002",
                ],
            },
        },
        # Expose the **currently** configured defaults so the UI can mark
        # them as selected.
        "current": {
            "provider": settings.llm_provider,
            "chat_model": settings.llm_model,
        },
    }
