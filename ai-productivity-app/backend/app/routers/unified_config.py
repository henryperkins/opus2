# app/routers/unified_config.py
"""
Unified API router for all AI configuration endpoints.
Replaces scattered config, models, and provider endpoints.
"""
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from datetime import datetime
import asyncio

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
        # Build provider catalogue dynamically to avoid hard-coded drift
        providers: Dict[str, Dict[str, Any]] = {}

        for model in available_models:
            provider_key = str(model.provider).lower()

            # Ensure entry exists
            providers.setdefault(
                provider_key,
                {
                    "display_name": provider_key.capitalize(),
                    "models": [],
                    "capabilities": {},
                },
            )

            providers[provider_key]["models"].append(model.model_dump(by_alias=True))

            # Merge provider-level capability flags – *True* if any model
            caps = model.capabilities or {}
            for cap_field in [
                "supports_functions",
                "supports_streaming",
                "supports_vision",
                "supports_responses_api",
                "supports_reasoning",
                "supports_thinking",
            ]:
                if getattr(caps, cap_field, False):
                    providers[provider_key]["capabilities"][cap_field] = True

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


from app.dependencies import CurrentUserRequired, get_current_user, AdminRequired
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
    current_user: AdminRequired,
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
        # Add use_responses_api to the updates if it's not already there
        if 'use_responses_api' not in updates and 'model_id' in updates:
            model_info = service.get_model_info(updates.get('model_id'))
            if model_info and model_info.capabilities:
                updates['use_responses_api'] = model_info.capabilities.supports_responses_api
        # Validate and update configuration
        updated_config = service.update_config(
            updates, updated_by=current_user.username
        )

        # Notify LLM client of changes
        await _notify_llm_client(updated_config)

        # Broadcast update via WebSocket
        await _broadcast_config_update(updated_config, service, "config_update")

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


@router.patch("", response_model=UnifiedModelConfig)
async def patch_configuration(
    updates: Dict[str, Any],
    current_user: AdminRequired,
    service: UnifiedConfigService = Depends(get_config_service),
) -> UnifiedModelConfig:
    """
    Update AI configuration with validation (PATCH variant).
    
    This endpoint provides the same functionality as PUT but uses PATCH method
    for compatibility with frontend code that expects partial updates.
    
    Accepts partial updates to any configuration fields:
    - Model selection (provider, model_id)
    - Generation parameters (temperature, max_tokens, etc.)
    - Reasoning settings (reasoning_effort, thinking modes)
    
    All updates are validated for consistency before applying.
    """
    # Delegate to the PUT handler logic
    return await update_configuration(updates, current_user, service)


@router.put("/batch", response_model=UnifiedModelConfig)
async def batch_update_configuration(
    updates: List[Dict[str, Any]],
    current_user: AdminRequired,
    service: UnifiedConfigService = Depends(get_config_service),
) -> UnifiedModelConfig:
    """
    Batch update configuration with transaction support.

    Accepts multiple configuration updates that are applied atomically.
    If any update fails, all changes are rolled back.

    Useful for complex configuration changes that need to be consistent.
    """
    try:
        # Get current config for rollback
        current_config = service.get_current_config()

        # Apply updates sequentially within transaction
        final_config = current_config
        for update in updates:
            # Validate each update before applying
            is_valid, error = service.validate_config(update)
            if not is_valid:
                raise ValueError(f"Update validation failed: {error}")

            # Apply update
            final_config = service.update_config(
                update, updated_by=current_user.username
            )

        # Notify LLM client of final state
        await _notify_llm_client(final_config)

        # Broadcast batch update via WebSocket
        await _broadcast_config_update(final_config, service, "config_batch_update")

        logger.info(f"Batch configuration updated by {current_user.username}")

        return final_config

    except ValueError as e:
        # Rollback to previous config on validation error
        service.update_config(
            current_config.model_dump(), updated_by=f"rollback_{current_user.username}"
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to batch update configuration: {e}")
        # Attempt rollback
        try:
            service.update_config(
                current_config.model_dump(), updated_by=f"rollback_{current_user.username}"
            )
        except Exception as rollback_error:
            logger.error(f"Rollback failed: {rollback_error}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to batch update configuration",
        )


@router.post("/test")
async def test_configuration(
    current_user: CurrentUserRequired,
    service: UnifiedConfigService = Depends(get_config_service),
    config: Optional[UnifiedModelConfig] = None,
    dry_run: bool = False,
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

        # Run test with dry_run flag
        result = await service.test_config(test_config, dry_run=dry_run)

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
    service: UnifiedConfigService = Depends(get_config_service),
) -> list[Dict[str, Any]]:
    """
    Return predefined configuration presets sourced from the service layer.
    """
    return service.get_presets()


@router.post("/resolve-conflict")
async def resolve_configuration_conflict(
    conflict_data: Dict[str, Any],
    current_user: CurrentUserRequired,
    service: UnifiedConfigService = Depends(get_config_service),
) -> Dict[str, Any]:
    """
    Resolve configuration conflicts when multiple users modify settings simultaneously.

    Accepts conflict data with:
    - current_config: Current server configuration
    - proposed_config: User's proposed changes
    - conflict_strategy: 'merge', 'overwrite', or 'abort'

    Returns resolved configuration or conflict details.
    """
    try:
        current_config = service.get_current_config()
        proposed_config = conflict_data.get("proposed_config", {})
        strategy = conflict_data.get("conflict_strategy", "merge")

        if strategy == "abort":
            return {
                "success": False,
                "message": "Configuration conflict - changes aborted",
                "current_config": current_config.model_dump(),
                "conflicts": _detect_conflicts(current_config.model_dump(), proposed_config)
            }

        elif strategy == "overwrite":
            # Force overwrite - apply proposed changes
            updated_config = service.update_config(
                proposed_config, updated_by=current_user.username
            )

            await _broadcast_config_update(updated_config, service, "config_conflict_resolved")

            return {
                "success": True,
                "message": "Configuration conflict resolved - changes applied",
                "resolved_config": updated_config.model_dump()
            }

        elif strategy == "merge":
            # Intelligent merge - combine non-conflicting changes
            conflicts = _detect_conflicts(current_config.model_dump(), proposed_config)

            if conflicts:
                return {
                    "success": False,
                    "message": "Configuration conflicts detected - manual resolution required",
                    "current_config": current_config.model_dump(),
                    "proposed_config": proposed_config,
                    "conflicts": conflicts
                }

            # No conflicts - apply merge
            merged_config = _merge_configs(current_config.model_dump(), proposed_config)
            updated_config = service.update_config(
                merged_config, updated_by=current_user.username
            )

            await _broadcast_config_update(updated_config, service, "config_conflict_resolved")

            return {
                "success": True,
                "message": "Configuration merged successfully",
                "resolved_config": updated_config.model_dump()
            }

        else:
            raise ValueError(f"Unknown conflict strategy: {strategy}")

    except Exception as e:
        logger.error(f"Failed to resolve configuration conflict: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve configuration conflict",
        )


# Helper functions


async def _notify_llm_client(config: UnifiedModelConfig):
    """Notify LLM client of configuration changes."""
    try:
        from app.llm.client import llm_client

        await llm_client.reconfigure(
            provider=config.provider,
            model=config.model_id,
            use_responses_api=config.use_responses_api,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            top_p=config.top_p,
            frequency_penalty=config.frequency_penalty,
            presence_penalty=config.presence_penalty,
        )
    except Exception as e:
        logger.warning(f"Failed to reconfigure LLM client: {e}")


async def _broadcast_config_update(
    config: UnifiedModelConfig, service: UnifiedConfigService, event_type: str = "config_update"
):
    """Broadcast configuration update via WebSocket."""
    try:
        # Build update message
        update_message = {
            "type": event_type,
            "data": {
                "current": config.model_dump(by_alias=True),
                "available_models": [
                    m.model_dump(by_alias=True) for m in service.get_available_models()
                ],
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

        await connection_manager.broadcast_config_update(update_message)

    except Exception as e:
        logger.warning(f"Failed to broadcast config update: {e}")


def _detect_conflicts(current_config: Dict[str, Any], proposed_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Detect configuration conflicts between current and proposed settings."""
    conflicts = []

    # Check for conflicting model selection
    if "model_id" in proposed_config and "provider" in proposed_config:
        current_model = current_config.get("model_id")
        current_provider = current_config.get("provider")
        proposed_model = proposed_config.get("model_id")
        proposed_provider = proposed_config.get("provider")

        if (current_model != proposed_model or current_provider != proposed_provider):
            conflicts.append({
                "field": "model_selection",
                "current": {"model_id": current_model, "provider": current_provider},
                "proposed": {"model_id": proposed_model, "provider": proposed_provider},
                "severity": "high"
            })

    # Check for conflicting reasoning settings
    reasoning_fields = ["enable_reasoning", "reasoning_effort", "claude_extended_thinking", "claude_thinking_mode"]
    for field in reasoning_fields:
        if field in proposed_config and field in current_config:
            if current_config[field] != proposed_config[field]:
                conflicts.append({
                    "field": field,
                    "current": current_config[field],
                    "proposed": proposed_config[field],
                    "severity": "medium"
                })

    # Check for conflicting generation parameters
    generation_fields = ["temperature", "max_tokens", "top_p", "frequency_penalty", "presence_penalty"]
    for field in generation_fields:
        if field in proposed_config and field in current_config:
            if abs(current_config[field] - proposed_config[field]) > 0.1:  # Threshold for meaningful difference
                conflicts.append({
                    "field": field,
                    "current": current_config[field],
                    "proposed": proposed_config[field],
                    "severity": "low"
                })

    return conflicts


def _merge_configs(current_config: Dict[str, Any], proposed_config: Dict[str, Any]) -> Dict[str, Any]:
    """Merge proposed configuration changes with current configuration."""
    merged = current_config.copy()

    # Apply non-conflicting changes
    for key, value in proposed_config.items():
        if key not in current_config or current_config[key] == value:
            merged[key] = value

    return merged


