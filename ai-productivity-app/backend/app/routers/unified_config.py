# app/routers/unified_config.py
"""
Unified API router for all AI configuration endpoints.
Replaces scattered config, models, and provider endpoints.
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.services.unified_config_service import UnifiedConfigService
from app.schemas.generation import (
    UnifiedModelConfig,
    ConfigResponse,
    ModelInfo,
)
from app.dependencies import CurrentUserRequired
from app.websocket.manager import connection_manager
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ai-config", tags=["ai-configuration"])


def get_config_service(db: Session = Depends(get_db)) -> UnifiedConfigService:
    """Dependency to get config service instance."""
    return UnifiedConfigService(db)


@router.get("", response_model=ConfigResponse)
async def get_configuration(
    current_user: CurrentUserRequired,
    service: UnifiedConfigService = Depends(get_config_service),
) -> ConfigResponse:
    """
    Get current AI configuration including all settings and available models.

    Returns complete configuration state:
    - Current model and provider settings
    - Generation parameters (temperature, tokens, etc.)
    - Reasoning/thinking configuration
    - Available models and providers
    """
    try:
        current_config = service.get_current_config()
        available_models = service.get_available_models()

        # Build provider catalog with capabilities
        providers = {
            "openai": {
                "display_name": "OpenAI",
                "models": [
                    m.model_dump() for m in available_models if m.provider == "openai"
                ],
                "capabilities": {
                    "supports_functions": True,
                    "supports_streaming": True,
                    "supports_vision": True,
                },
            },
            "azure": {
                "display_name": "Azure OpenAI",
                "models": [
                    m.model_dump() for m in available_models if m.provider == "azure"
                ],
                "capabilities": {
                    "supports_functions": True,
                    "supports_streaming": True,
                    "supports_responses_api": True,
                    "supports_reasoning": True,
                },
            },
            "anthropic": {
                "display_name": "Anthropic",
                "models": [
                    m.model_dump()
                    for m in available_models
                    if m.provider == "anthropic"
                ],
                "capabilities": {
                    "supports_functions": True,
                    "supports_streaming": True,
                    "supports_thinking": True,
                },
            },
        }

        return ConfigResponse(
            current=current_config,
            available_models=available_models,
            providers=providers,
            last_updated=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Failed to get configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load configuration",
        )


from app.dependencies import CurrentUserRequired, get_current_user
from app.models.user import User

...

@router.get("/defaults", response_model=dict, summary="Built-in defaults")
async def get_defaults(
    service: UnifiedConfigService = Depends(get_config_service),
    user: Optional[User] = Depends(get_current_user)
) -> dict:
    """
    Return the canonical default provider / model / generation parameters.
    """
    return service.get_defaults()


@router.put("", response_model=UnifiedModelConfig)
async def update_configuration(
    updates: Dict[str, Any],
    current_user: CurrentUserRequired,
    service: UnifiedConfigService = Depends(get_config_service),
) -> UnifiedModelConfig:
    """
    Update AI configuration with validation.

    Accepts partial updates to any configuration fields:
    - Model selection (provider, model_id)
    - Generation parameters (temperature, max_tokens, etc.)
    - Reasoning settings (reasoning_effort, thinking modes)

    All updates are validated for consistency before applying.
    """
    try:
        # Validate and update configuration
        updated_config = service.update_config(
            updates, updated_by=current_user.username
        )

        # Notify LLM client of changes
        await _notify_llm_client(updated_config)

        # Broadcast update via WebSocket
        await _broadcast_config_update(updated_config, service)

        logger.info(f"Configuration updated by {current_user.username}")

        return updated_config

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update configuration",
        )


@router.post("/test")
async def test_configuration(
    current_user: CurrentUserRequired,
    service: UnifiedConfigService = Depends(get_config_service),
    config: Optional[UnifiedModelConfig] = None,
) -> Dict[str, Any]:
    """
    Test AI configuration with actual API call.

    Tests the provided configuration (or current if none provided) by:
    - Validating all parameters
    - Making a test API call
    - Measuring response time

    Returns test results including success status and timing.
    """
    try:
        # Use provided config or current
        test_config = config or service.get_current_config()

        # Run test
        result = await service.test_config(test_config)

        logger.info(
            f"Configuration test by {current_user.username}: "
            f"{'Success' if result['success'] else 'Failed'}"
        )

        return result

    except Exception as e:
        logger.error(f"Configuration test failed: {e}")
        return {"success": False, "message": "Test failed", "error": str(e)}


@router.get("/models", response_model=list[ModelInfo])
async def get_available_models(
    current_user: CurrentUserRequired,
    service: UnifiedConfigService = Depends(get_config_service),
    provider: Optional[str] = None,
    include_deprecated: bool = False,
) -> list[ModelInfo]:
    """
    Get list of available AI models.

    Query parameters:
    - provider: Filter by provider (openai, azure, anthropic)
    - include_deprecated: Include deprecated models

    Returns detailed information for each model including capabilities and costs.
    """
    try:
        models = service.get_available_models(provider, include_deprecated)
        return models

    except Exception as e:
        logger.error(f"Failed to get models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load available models",
        )


@router.get("/models/{model_id}", response_model=ModelInfo)
async def get_model_info(
    model_id: str,
    current_user: CurrentUserRequired,
    service: UnifiedConfigService = Depends(get_config_service),
) -> ModelInfo:
    """
    Get detailed information for a specific model.

    Returns complete model information including:
    - Capabilities and limitations
    - Cost per token
    - Performance characteristics
    - Recommended use cases
    """
    model_info = service.get_model_info(model_id)

    if not model_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_id}' not found",
        )

    return model_info


@router.post("/validate")
async def validate_configuration(
    config: Dict[str, Any],
    current_user: CurrentUserRequired,
    service: UnifiedConfigService = Depends(get_config_service),
) -> Dict[str, Any]:
    """
    Validate configuration without saving.

    Enhanced validation checks:
    - Parameter value ranges and types
    - Provider/model compatibility
    - Model-specific capability restrictions
    - Reasoning model limitations
    - Function calling support
    - Streaming compatibility
    - Token limits

    Returns detailed validation result with specific error details and warnings.
    """
    is_valid, error = service.validate_config(config)
    
    # Additional capability information
    capabilities_info = {}
    warnings = []
    
    if "model_id" in config:
        from app.services.model_service import ModelService
        from app.database import get_db
        
        try:
            db = next(get_db())
            model_service = ModelService(db)
            
            model_id = config["model_id"]
            capabilities_info = {
                "supports_streaming": model_service.supports_streaming(model_id),
                "supports_functions": model_service.supports_functions(model_id),
                "supports_vision": model_service.supports_vision(model_id),
                "supports_reasoning": model_service.is_reasoning_model(model_id),
                "max_tokens": model_service.get_max_tokens(model_id),
                "context_window": model_service.get_context_window(model_id)
            }
            
            # Generate warnings for potentially incompatible settings
            if config.get("stream", False) and not capabilities_info["supports_streaming"]:
                warnings.append(f"Model {model_id} does not support streaming")
            
            if config.get("tools") and not capabilities_info["supports_functions"]:
                warnings.append(f"Model {model_id} does not support function calling")
            
            max_tokens = config.get("max_tokens")
            if max_tokens and max_tokens > capabilities_info["max_tokens"]:
                warnings.append(f"Requested max_tokens ({max_tokens}) exceeds model limit ({capabilities_info['max_tokens']})")
            
        except Exception as e:
            logger.warning(f"Could not get capability info: {e}")

    return {
        "valid": is_valid, 
        "error": error, 
        "warnings": warnings,
        "capabilities": capabilities_info,
        "validated_at": datetime.utcnow()
    }


@router.get("/presets")
async def get_configuration_presets(
    current_user: CurrentUserRequired,
) -> list[Dict[str, Any]]:
    """
    Get predefined configuration presets.

    Returns common configuration presets optimized for different use cases:
    - Balanced: General purpose
    - Creative: Higher temperature for varied outputs
    - Precise: Lower temperature for consistent outputs
    - Fast: Optimized for speed
    - Powerful: Maximum capability models
    """
    presets = [
        {
            "id": "balanced",
            "name": "Balanced",
            "description": "Good balance of quality and speed",
            "config": {
                "temperature": 0.7,
                "max_tokens": 2048,
                "top_p": 0.95,
                "reasoning_effort": "medium",
            },
        },
        {
            "id": "creative",
            "name": "Creative",
            "description": "More creative and varied responses",
            "config": {
                "temperature": 1.2,
                "max_tokens": 3000,
                "top_p": 0.95,
                "frequency_penalty": 0.2,
                "presence_penalty": 0.2,
                "reasoning_effort": "high",
            },
        },
        {
            "id": "precise",
            "name": "Precise",
            "description": "Focused and deterministic responses",
            "config": {
                "temperature": 0.3,
                "max_tokens": 2048,
                "top_p": 0.9,
                "reasoning_effort": "high",
            },
        },
        {
            "id": "fast",
            "name": "Fast",
            "description": "Optimized for quick responses",
            "config": {
                "model_id": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 1024,
                "reasoning_effort": "low",
            },
        },
        {
            "id": "powerful",
            "name": "Powerful",
            "description": "Maximum capability for complex tasks",
            "config": {
                "model_id": "gpt-4o",
                "temperature": 0.7,
                "max_tokens": 4096,
                "reasoning_effort": "high",
                "enable_reasoning": True,
            },
        },
    ]

    return presets


# Helper functions


async def _notify_llm_client(config: UnifiedModelConfig):
    """Notify LLM client of configuration changes."""
    try:
        from app.llm.client import llm_client

        await llm_client.reconfigure(
            provider=config.provider,
            model=config.model_id,
            use_responses_api=config.use_responses_api,
        )
    except Exception as e:
        logger.warning(f"Failed to reconfigure LLM client: {e}")


async def _broadcast_config_update(
    config: UnifiedModelConfig, service: UnifiedConfigService
):
    """Broadcast configuration update via WebSocket."""
    try:
        # Build update message
        update_message = {
            "type": "config_update",
            "data": {
                "current": config.model_dump(),
                "available_models": [
                    m.model_dump() for m in service.get_available_models()
                ],
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

        await connection_manager.broadcast_json(update_message)

    except Exception as e:
        logger.warning(f"Failed to broadcast config update: {e}")


