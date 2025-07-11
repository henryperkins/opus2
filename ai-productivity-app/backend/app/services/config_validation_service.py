"""
Configuration validation service that provides provider-aware validation
with clear error messages and handles field compatibility.
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
from app.schemas.generation import UnifiedModelConfig, ConfigUpdate
from app.services.model_service import ModelService
from app.models.config import ModelConfiguration
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ConfigValidationService:
    """
    Centralized configuration validation service that handles:
    - Provider-specific validation rules
    - Field name normalization (camelCase <-> snake_case)
    - Clear error messaging
    - Configuration compatibility checks
    """

    def __init__(self, db: Session):
        self.db = db
        self.model_service = ModelService(db)

    def normalize_field_names(self, data: Dict[str, Any], to_snake_case: bool = True) -> Dict[str, Any]:
        """
        Normalize field names between camelCase and snake_case.
        Handles nested dictionaries and special cases.
        """
        def convert_key(key: str) -> str:
            if to_snake_case:
                # camelCase to snake_case
                if key == "modelId":
                    return "model_id"
                result = []
                for i, char in enumerate(key):
                    if char.isupper() and i > 0:
                        result.append('_')
                        result.append(char.lower())
                    else:
                        result.append(char.lower())
                return ''.join(result)
            else:
                # snake_case to camelCase
                if key == "model_id":
                    return "modelId"
                parts = key.split('_')
                return parts[0] + ''.join(part.capitalize() for part in parts[1:])

        def normalize_dict(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {convert_key(k): normalize_dict(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [normalize_dict(item) for item in obj]
            else:
                return obj

        return normalize_dict(data)

    def validate_provider_requirements(
        self, provider: str, config: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Validate provider-specific requirements and return clear error messages.
        """
        errors = []

        if provider == "azure":
            # Azure requires specific configurations
            from app.config import settings

            # Check if Azure credentials are configured
            if not settings.azure_openai_endpoint:
                errors.append("Azure OpenAI endpoint not configured in environment")
            if not settings.azure_openai_api_key and settings.azure_auth_method == "api_key":
                errors.append("Azure OpenAI API key not configured in environment")

            # Check model compatibility
            model_id = config.get("model_id")
            if model_id:
                # With v1 API, Azure uses model IDs directly - no deployment validation needed
                # Just ensure the model exists in our database
                from app.database import SessionLocal
                from app.models.config import ModelConfiguration

                with SessionLocal() as db:
                    model = db.query(ModelConfiguration).filter_by(
                        model_id=model_id, provider="azure"
                    ).first()
                    if not model:
                        errors.append(f"Model {model_id} not found or not available for Azure")

        elif provider == "openai":
            from app.config import settings
            if not settings.openai_api_key:
                errors.append("OpenAI API key not configured in environment")

        elif provider == "anthropic":
            from app.config import settings
            if not settings.anthropic_api_key:
                errors.append("Anthropic API key not configured in environment")

            # Claude models don't support standard reasoning
            if config.get("enable_reasoning"):
                errors.append("Claude models use extended thinking, not standard reasoning. Use claude_extended_thinking instead")

        return len(errors) == 0, errors

    def validate_model_compatibility(
        self, model_id: str, provider: str, config: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Validate that the model is compatible with the requested configuration.
        """
        errors = []

        # Get model capabilities using ModelService methods
        try:
            capabilities = self.model_service.get_model_capabilities(model_id)

            if config.get("stream", False) and not self.model_service.supports_streaming(model_id):
                errors.append(f"Model {model_id} does not support streaming")

            if config.get("tools") and not self.model_service.supports_functions(model_id):
                errors.append(f"Model {model_id} does not support function calling")

            max_tokens = config.get("max_tokens")
            max_output_tokens = self.model_service.get_max_tokens(model_id)
            if max_tokens and max_output_tokens and max_tokens > max_output_tokens:
                errors.append(
                    f"Model {model_id} maximum output tokens is {max_output_tokens}, "
                    f"requested {max_tokens}"
                )
        except Exception:
            # Model not in database, use static checks
            is_reasoning = ModelService.is_reasoning_model_static(model_id)

            if is_reasoning:
                # Reasoning models have specific constraints
                if config.get("temperature") not in [None, 1.0]:
                    errors.append(f"Reasoning model {model_id} does not support temperature control (must be 1.0)")
                if config.get("stream", False):
                    errors.append(f"Reasoning model {model_id} does not support streaming")
                if config.get("tools"):
                    errors.append(f"Reasoning model {model_id} does not support function calling")

        return len(errors) == 0, errors

    def validate_config_update(
        self, current_config: UnifiedModelConfig, update: ConfigUpdate
    ) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validate a configuration update and return:
        - Success status
        - List of error messages
        - Normalized update dictionary
        """
        errors = []

        # Convert update to dict and normalize field names
        update_dict = update.dict(exclude_unset=True)
        normalized_update = self.normalize_field_names(update_dict, to_snake_case=True)

        # Merge with current config
        merged = current_config.model_dump()

        # Handle special field mappings
        if "model_id" in normalized_update:
            merged["model_id"] = normalized_update["model_id"]
            # Remove any conflicting modelId field
            merged.pop("modelId", None)

        # Apply other updates
        for key, value in normalized_update.items():
            if key != "model_id":  # Already handled above
                merged[key] = value

        # Determine effective provider and model
        provider = merged.get("provider", current_config.provider)
        model_id = merged.get("model_id", current_config.model_id)

        # Validate provider requirements
        provider_valid, provider_errors = self.validate_provider_requirements(provider, merged)
        errors.extend(provider_errors)

        # Validate model compatibility
        if model_id:
            model_valid, model_errors = self.validate_model_compatibility(model_id, provider, merged)
            errors.extend(model_errors)

        # Check if provider switch requires model change
        if "provider" in normalized_update and normalized_update["provider"] != current_config.provider:
            # Check if current model is available for new provider
            try:
                # Try to get model capabilities - if it fails, model might not exist for this provider
                capabilities = self.model_service.get_model_capabilities(current_config.model_id)
                # For now, we'll assume the model exists and is compatible
                # A more robust check would query the database directly
            except Exception:
                if "model_id" not in normalized_update:
                    errors.append(
                        f"Current model {current_config.model_id} is not available for provider "
                        f"{normalized_update['provider']}. Please select a compatible model."
                    )

        return len(errors) == 0, errors, merged

    def suggest_compatible_config(
        self, provider: str, requested_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Suggest a compatible configuration for the given provider.
        """
        compatible = requested_config.copy()

        # Get available models for provider
        available_models = self.model_service.get_models_by_capability("completion", provider)

        if not available_models and "model_id" in compatible:
            # Current model not available, suggest first available
            all_models = self.db.query(ModelConfiguration).filter_by(
                provider=provider, is_available=True, is_deprecated=False
            ).first()
            if all_models:
                compatible["model_id"] = all_models.model_id

        # Adjust parameters based on provider
        if provider == "anthropic":
            # Convert reasoning to Claude thinking
            if compatible.get("enable_reasoning"):
                compatible.pop("enable_reasoning", None)
                compatible["claude_extended_thinking"] = True
                compatible["claude_thinking_mode"] = "enabled"

        elif provider in ["azure", "openai"]:
            # Convert Claude thinking to reasoning
            if compatible.get("claude_extended_thinking"):
                compatible.pop("claude_extended_thinking", None)
                compatible.pop("claude_thinking_mode", None)
                compatible["enable_reasoning"] = True

        return compatible

    def get_missing_fields_details(self, exception: Exception) -> List[Dict[str, str]]:
        """
        Parse Pydantic validation errors to extract detailed field information.
        """
        details = []

        if hasattr(exception, '__cause__') and hasattr(exception.__cause__, 'errors'):
            for error in exception.__cause__.errors():
                field_path = ' -> '.join(str(loc) for loc in error['loc'])
                details.append({
                    'field': field_path,
                    'type': error['type'],
                    'message': error['msg']
                })

        return details
