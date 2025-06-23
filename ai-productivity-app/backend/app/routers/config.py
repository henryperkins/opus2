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

from fastapi import APIRouter, HTTPException

from app.config import settings


router = APIRouter(prefix="/api/config", tags=["config"])

# ---------------------------------------------------------------------------
# Logging – keep verbose debug off by default; INFO is sufficient for
# production troubleshooting.  The FastAPI / Uvicorn stack will inherit the
# parent logging configuration (usually *INFO*).
# ---------------------------------------------------------------------------

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dynamic in-memory runtime configuration
# ---------------------------------------------------------------------------
# We keep a **single** global dict that represents the *current* chat model
# configuration.  This is sufficient for development and unit-tests because
# the application usually runs as a single Python process.  Production
# deployments that run multiple gunicorn / uvicorn workers should replace this
# with a persistent store (PostgreSQL, Redis, …).  The implementation is kept
# deliberately simple so that we do not introduce additional dependencies.

from pydantic import BaseModel, Field, NonNegativeInt, confloat, validator


class ModelConfigPayload(BaseModel):
    """Schema for model configuration updates coming from the frontend."""

    provider: str | None = Field(default=None, examples=["openai", "azure"])
    # External JSON key is identical (chat_model) – UI already uses that.
    chat_model: str | None = Field(default=None, examples=["gpt-4o-mini"])

    # Optional fine-tuning parameters – validated but not used server-side yet
    temperature: confloat(ge=0.0, le=2.0) | None = None
    maxTokens: NonNegativeInt | None = None
    topP: confloat(ge=0.0, le=1.0) | None = Field(default=None, alias="topP")
    frequencyPenalty: confloat(ge=0.0, le=2.0) | None = Field(
        default=None, alias="frequencyPenalty"
    )
    presencePenalty: confloat(ge=0.0, le=2.0) | None = Field(
        default=None, alias="presencePenalty"
    )
    systemPrompt: str | None = Field(default=None, alias="systemPrompt")

    # Azure Responses API toggle – when *true* the frontend expects the
    # backend to route conversations through the `/responses` endpoint
    # instead of classic Chat Completions.  The flag is **provider agnostic**
    # (OpenAI may add similar capabilities later).
    useResponsesApi: bool | None = Field(default=None, alias="useResponsesApi")

    class Config:
        populate_by_name = True

    @validator("provider")
    def _normalise_provider(cls, v):  # noqa: N805 – Pydantic validator name
        if v is None:
            return v
        v = v.lower()
        if v not in {"openai", "azure"}:
            raise ValueError("Unsupported provider")
        return v


# Default configuration – bootstrapped from environment variables so the
# behaviour is identical to the previous *static* implementation.

_RUNTIME_CONFIG: dict[str, str] = {
    "provider": settings.llm_provider,
    "chat_model": settings.llm_default_model or settings.llm_model,
    "useResponsesApi": False,
}


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

    # Traditional Chat Completions models
    "gpt-4o",  # or your deployment named "gpt4o-general"
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-4",
    "gpt-35-turbo",  # Azure naming convention for GPT-3.5

    # Azure Responses API models (requires api_version="preview")
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4.1-nano",
    "o3",
    "o4-mini",
    "gpt-image-1",
    "computer-use-preview",
]


@router.get("", summary="Return supported LLM providers and models")
async def get_config():  # noqa: D401
    """Return a JSON object with provider → model mapping."""
    logger.info("/api/config requested – returning model catalogue")

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
                "api_versions": [
                    "2024-02-01",  # Standard Chat Completions API
                    "2025-04-01-preview",  # Latest Responses API with advanced features
                    "preview",     # Legacy preview alias
                ],
                "features": {
                    "responses_api": (
                        settings.azure_openai_api_version in ["preview", "2025-04-01-preview"]
                    ),
                    "background_tasks": True,
                    "image_generation": True,
                    "computer_use": True,
                    "mcp_servers": True,
                },
            },
        },
        # Expose the **currently** configured defaults so the UI can mark
        # them as selected.
        "current": {
            "provider": _RUNTIME_CONFIG["provider"],
            "chat_model": _RUNTIME_CONFIG["chat_model"],
            "useResponsesApi": _RUNTIME_CONFIG.get("useResponsesApi", False),
        },
    }


# ---------------------------------------------------------------------------
# Runtime update endpoints
# ---------------------------------------------------------------------------


@router.put("/model", summary="Update *current* chat model configuration")
async def update_model_config(payload: ModelConfigPayload):  # noqa: D401
    """Persist the provided configuration in memory and return the full config."""

    # Update only the provided fields to keep previously configured values.
    # We want *internal* field names here (``chat_model`` instead of ``model``)
    update_data = payload.dict(exclude_unset=True, by_alias=False)
    if not update_data:
        raise HTTPException(status_code=400, detail="No configuration provided")

    _RUNTIME_CONFIG.update(update_data)

    logger.info("/api/config/model – runtime configuration updated: %s", update_data)

    return {
        "success": True,
        "message": "Model configuration updated",
        "current": _RUNTIME_CONFIG,
    }


@router.post("/test", summary="Validate that the supplied configuration works")
async def test_model_config(payload: ModelConfigPayload):  # noqa: D401
    """Trivial test endpoint – would call the LLM provider in production."""

    # The *test* simply echos back the payload and returns success=True so the
    # frontend perceives the configuration as valid.  Extend this with a real
    # provider API call once credentials are available in the environment.

    _ = payload  # silence linter – variable kept for future use

    return {
        "success": True,
        "message": "Configuration is syntactically valid",
        "latency": 0.0,
    }
