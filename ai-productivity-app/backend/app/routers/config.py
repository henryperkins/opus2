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
# Persistent runtime configuration
# ---------------------------------------------------------------------------
# Configuration is now stored persistently in the database via RuntimeConfig model
# and managed through ConfigService. This replaces the in-memory _RUNTIME_CONFIG
# approach for production deployments.

from typing import Any
from pydantic import BaseModel, Field, NonNegativeInt, confloat, validator
from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.config_service import ConfigService


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


# Legacy in-memory config for backward compatibility and fallback
# This will be gradually phased out in favor of database storage
_RUNTIME_CONFIG: dict[str, Any] = {
    "provider": settings.llm_provider,
    "chat_model": settings.llm_default_model or settings.llm_model,
    "useResponsesApi": False,
}

def get_config_service(db: Session = Depends(get_db)) -> ConfigService:
    """Dependency to get ConfigService instance."""
    return ConfigService(db)

def get_current_config(config_service: ConfigService) -> dict[str, Any]:
    """Get current configuration from database, falling back to in-memory config."""
    try:
        db_config = config_service.get_all_config()
        if db_config:
            # Merge database config with fallback values
            current_config = _RUNTIME_CONFIG.copy()
            current_config.update(db_config)
            return current_config
        else:
            # Initialize database with current in-memory config if empty
            config_service.initialize_default_config()
            return config_service.get_all_config()
    except Exception as e:
        logger.warning(f"Failed to load config from database, using in-memory fallback: {e}")
        return _RUNTIME_CONFIG


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
async def get_config(config_service: ConfigService = Depends(get_config_service)):  # noqa: D401
    """Return a JSON object with provider → model mapping."""
    logger.info("/api/config requested – returning model catalogue")
    
    # Get current configuration from database
    current_config = get_current_config(config_service)

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
            "provider": current_config.get("provider"),
            "chat_model": current_config.get("chat_model"),
            "useResponsesApi": current_config.get("useResponsesApi", False),
            "temperature": current_config.get("temperature", 0.7),
            "maxTokens": current_config.get("maxTokens"),
            "topP": current_config.get("topP"),
            "frequencyPenalty": current_config.get("frequencyPenalty"),
            "presencePenalty": current_config.get("presencePenalty"),
            "systemPrompt": current_config.get("systemPrompt"),
        },
    }


# ---------------------------------------------------------------------------
# Runtime update endpoints
# ---------------------------------------------------------------------------


@router.put("/model", summary="Update *current* chat model configuration")
async def update_model_config(
    payload: ModelConfigPayload, 
    config_service: ConfigService = Depends(get_config_service)
):  # noqa: D401
    """Persist the provided configuration to database and return the full config."""

    # Update only the provided fields to keep previously configured values.
    # We want *internal* field names here (``chat_model`` instead of ``model``)
    update_data = payload.dict(exclude_unset=True, by_alias=False)
    if not update_data:
        raise HTTPException(status_code=400, detail="No configuration provided")

    try:
        # Update database configuration
        config_service.set_multiple_config(update_data, updated_by="api_user")
        
        # Also update in-memory config for backward compatibility
        _RUNTIME_CONFIG.update(update_data)

        # Trigger LLM client reconfiguration if provider or model changed
        if "provider" in update_data or "chat_model" in update_data or "useResponsesApi" in update_data:
            try:
                from app.llm.client import llm_client
                await llm_client.reconfigure(
                    provider=update_data.get("provider"),
                    model=update_data.get("chat_model"),
                    use_responses_api=update_data.get("useResponsesApi")
                )
                logger.info("LLM client reconfigured successfully")
            except Exception as e:
                logger.warning("Failed to reconfigure LLM client: %s", e)
                # Don't fail the config update if reconfiguration fails

        logger.info("/api/config/model – runtime configuration updated: %s", update_data)

        # Get updated configuration to return
        current_config = get_current_config(config_service)
        
        # Broadcast configuration update to all WebSocket connections
        try:
            from app.websocket.manager import connection_manager
            await connection_manager.broadcast_config_update(current_config)
            logger.info("Configuration update broadcasted to WebSocket clients")
        except Exception as e:
            logger.warning("Failed to broadcast config update via WebSocket: %s", e)
        
        return {
            "success": True,
            "message": "Model configuration updated",
            "current": current_config,
        }
        
    except Exception as e:
        logger.error("Failed to update model configuration: %s", e)
        raise HTTPException(status_code=500, detail=f"Configuration update failed: {str(e)}")


@router.post("/test", summary="Validate that the supplied configuration works")
async def test_model_config(
    payload: ModelConfigPayload,
    config_service: ConfigService = Depends(get_config_service)
):  # noqa: D401
    """Test the provided configuration by making an actual API call."""
    
    import time
    import asyncio
    from app.llm.client import LLMClient
    
    start_time = time.time()
    
    try:
        # Create a temporary LLM client with the test configuration
        test_client = LLMClient()
        
        # Configure the test client with provided parameters
        test_provider = payload.provider or "openai"
        test_model = payload.chat_model or "gpt-3.5-turbo"
        test_temperature = payload.temperature or 0.7
        test_max_tokens = payload.maxTokens or 50  # Small limit for testing
        
        # Reconfigure for testing
        await test_client.reconfigure(
            provider=test_provider,
            model=test_model,
            use_responses_api=payload.useResponsesApi or False
        )
        
        # Test with a simple prompt
        test_messages = [
            {"role": "system", "content": "You are a helpful assistant. Respond briefly."},
            {"role": "user", "content": "Say 'test successful' if you can read this."}
        ]
        
        # Make the API call with timeout
        try:
            response = await asyncio.wait_for(
                test_client.complete(
                    messages=test_messages,
                    temperature=test_temperature,
                    max_tokens=test_max_tokens,
                    stream=False
                ),
                timeout=30.0  # 30 second timeout
            )
            
            # Extract response content
            if hasattr(response, "choices") and response.choices:
                response_text = response.choices[0].message.content.strip()
                success = "test" in response_text.lower()
            else:
                # Fallback for stub/mock responses
                response_text = str(response)
                success = True
            
            latency = time.time() - start_time
            
            return {
                "success": success,
                "message": "Model configuration test completed successfully" if success else "Model responded but test phrase not found",
                "latency": round(latency, 3),
                "response_preview": response_text[:100] + ("..." if len(response_text) > 100 else ""),
                "provider": test_provider,
                "model": test_model,
                "configuration": {
                    "temperature": test_temperature,
                    "max_tokens": test_max_tokens,
                    "use_responses_api": payload.useResponsesApi or False
                }
            }
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "message": "Model test timed out after 30 seconds",
                "latency": 30.0,
                "error_type": "timeout",
                "provider": test_provider,
                "model": test_model
            }
            
    except Exception as e:
        latency = time.time() - start_time
        error_message = str(e)
        
        # Categorize common errors
        if "api_key" in error_message.lower() or "unauthorized" in error_message.lower():
            error_type = "authentication"
            friendly_message = "Authentication failed - check your API key configuration"
        elif "not found" in error_message.lower() or "invalid" in error_message.lower():
            error_type = "invalid_model"
            friendly_message = f"Invalid model or configuration: {test_model}"
        elif "timeout" in error_message.lower() or "connection" in error_message.lower():
            error_type = "connection"
            friendly_message = "Connection failed - check network and endpoint configuration"
        else:
            error_type = "unknown"
            friendly_message = f"Test failed: {error_message}"
        
        logger.warning("Model configuration test failed: %s", error_message)
        
        return {
            "success": False,
            "message": friendly_message,
            "latency": round(latency, 3),
            "error_type": error_type,
            "error_details": error_message,
            "provider": payload.provider or "unknown",
            "model": payload.chat_model or "unknown"
        }
