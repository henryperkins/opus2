# app/services/unified_config_service.py
"""
Unified configuration service for AI model settings.
Single source of truth using RuntimeConfig table.
"""
import json
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.config import RuntimeConfig, ConfigHistory, ModelConfiguration
from app.schemas.generation import (
    UnifiedModelConfig,
    ModelInfo,
    validate_config_consistency,
)
from app.config import settings

logger = logging.getLogger(__name__)


class UnifiedConfigService:
    """Centralized service for all AI configuration management."""

    # Configuration key prefixes
    PREFIX_GENERATION = "gen_"
    PREFIX_REASONING = "reason_"
    PREFIX_PROVIDER = "provider_"
    PREFIX_MODEL = "model_"

    def __init__(self, db: Session):
        self.db = db
        self._config_cache = {}

    def get_current_config(self) -> UnifiedModelConfig:
        """Get current unified configuration."""
        # Load all config from RuntimeConfig
        all_config = self._load_all_config()

        # Convert to UnifiedModelConfig
        try:
            return UnifiedModelConfig.from_runtime_config(all_config)
        except Exception as e:
            logger.warning(f"Failed to load config, using defaults: {e}")
            return self._get_default_config()

    def update_config(
        self, updates: Dict[str, Any], updated_by: str = "api"
    ) -> UnifiedModelConfig:
        """Update configuration with validation."""
        # Get current config
        current = self.get_current_config()

        # Apply updates
        updated_dict = current.model_dump()
        updated_dict.update(updates)

        # Create new config instance for validation
        try:
            new_config = UnifiedModelConfig(**updated_dict)
        except ValueError as e:
            raise ValueError(f"Invalid configuration: {e}")

        # Validate consistency
        is_valid, error = validate_config_consistency(new_config)
        if not is_valid:
            raise ValueError(error)

        # Convert to runtime format
        runtime_config = new_config.to_runtime_config()

        # Save to database
        self._save_config(runtime_config, updated_by)

        # Clear cache
        self._config_cache.clear()

        return new_config

    def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """Get detailed model information."""
        model_config = (
            self.db.query(ModelConfiguration).filter_by(model_id=model_id).first()
        )

        if model_config:
            return self._model_config_to_info(model_config)

        return None

    def get_available_models(
        self, provider: Optional[str] = None, include_deprecated: bool = False
    ) -> List[ModelInfo]:
        """Get all available models from database."""
        # Load from database only
        query = self.db.query(ModelConfiguration)
        if provider:
            query = query.filter_by(provider=provider)
        if not include_deprecated:
            query = query.filter_by(is_deprecated=False)

        db_models = query.all()
        models = [self._model_config_to_info(m) for m in db_models]

        return sorted(models, key=lambda m: (m.provider, m.display_name))

    def initialize_defaults(self):
        """Initialize default configuration if none exists."""
        try:
            existing = self.db.query(RuntimeConfig).first()
            if existing:
                return  # Already initialized

            # Get defaults from settings
            default_config = self._get_default_config()
            runtime_config = default_config.to_runtime_config()

            # Save to database
            self._save_config(runtime_config, "system_init")

            logger.info("Initialized default AI configuration")

        except Exception as e:
            logger.error(f"Failed to initialize defaults: {e}")
            self.db.rollback()

    def validate_config(
        self, config_dict: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """Validate configuration dictionary with enhanced capability checking."""
        try:
            # Try to create UnifiedModelConfig
            config = UnifiedModelConfig(**config_dict)

            # Basic consistency validation
            is_valid, error = validate_config_consistency(config)
            if not is_valid:
                return False, error

            # Enhanced capability validation using ModelService
            from app.services.model_service import ModelService
            model_service = ModelService(self.db)
            
            # Validate model-specific capabilities
            model_valid, model_error = model_service.validate_model_config(
                config.model_id, config_dict
            )
            if not model_valid:
                return False, model_error

            return True, None

        except ValueError as e:
            return False, str(e)
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False, "Invalid configuration format"

    async def test_config(self, config: UnifiedModelConfig) -> Dict[str, Any]:
        """Test configuration with actual API call."""
        from app.llm.client import LLMClient
        import asyncio
        import time

        start_time = time.time()

        try:
            # Create temporary client with test config
            client = LLMClient()
            await client.reconfigure(
                provider=config.provider,
                model=config.model_id,
                use_responses_api=config.use_responses_api,
            )

            # Simple test message
            test_messages = [
                {"role": "system", "content": "You are a test assistant."},
                {"role": "user", "content": "Say 'test successful' and nothing else."},
            ]

            # Test with timeout
            await asyncio.wait_for(
                client.complete(
                    messages=test_messages,
                    model=config.model_id,
                    temperature=config.temperature,
                    max_tokens=10,
                    stream=False,
                ),
                timeout=30.0,
            )

            elapsed = time.time() - start_time

            return {
                "success": True,
                "message": "Configuration test successful",
                "response_time": round(elapsed, 2),
                "model": config.model_id,
                "provider": config.provider,
            }

        except asyncio.TimeoutError:
            return {
                "success": False,
                "message": "Test timed out after 30 seconds",
                "error": "timeout",
            }
        except Exception as e:
            logger.error(f"Configuration test failed: {e}")
            return {
                "success": False,
                "message": "Configuration test failed",
                "error": str(e),
            }

    # Private methods

    def _load_all_config(self) -> Dict[str, Any]:
        """Load all configuration from RuntimeConfig."""
        if self._config_cache:
            return self._config_cache

        configs = self.db.query(RuntimeConfig).all()
        result = {}

        for config in configs:
            try:
                # Handle different value types
                if config.value_type == "string":
                    result[config.key] = config.value
                elif config.value_type == "number":
                    result[config.key] = (
                        float(config.value)
                        if "." in str(config.value)
                        else int(config.value)
                    )
                elif config.value_type == "boolean":
                    result[config.key] = config.value in [True, "true", "True", "1", 1]
                elif config.value_type == "object":
                    result[config.key] = (
                        json.loads(config.value)
                        if isinstance(config.value, str)
                        else config.value
                    )
                else:
                    result[config.key] = config.value
            except Exception as e:
                logger.warning(f"Failed to parse config {config.key}: {e}")
                result[config.key] = config.value

        self._config_cache = result
        return result

    def _save_config(self, config_dict: Dict[str, Any], updated_by: str):
        """Save configuration to RuntimeConfig."""
        for key, value in config_dict.items():
            # Skip None values
            if value is None:
                continue

            # Determine value type
            if isinstance(value, bool):
                value_type = "boolean"
            elif isinstance(value, (int, float)):
                value_type = "number"
            elif isinstance(value, (dict, list)):
                value_type = "object"
                value = json.dumps(value)
            else:
                value_type = "string"
                value = str(value)

            # Get existing config
            existing = self.db.query(RuntimeConfig).filter_by(key=key).first()

            if existing:
                # Record history
                old_value = existing.value
                if old_value != value:
                    history = ConfigHistory(
                        config_key=key,
                        old_value=old_value,
                        new_value=value,
                        changed_by=updated_by,
                    )
                    self.db.add(history)

                # Update value
                existing.value = value
                existing.value_type = value_type
                existing.updated_by = updated_by
            else:
                # Create new
                new_config = RuntimeConfig(
                    key=key, value=value, value_type=value_type, updated_by=updated_by
                )
                self.db.add(new_config)

        try:
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Configuration update failed due to integrity constraint: {e}")
            raise ValueError(f"Configuration update failed: {e}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Unexpected error during configuration save: {e}")
            raise RuntimeError(f"Configuration save failed: {e}")

    def _get_default_config(self) -> UnifiedModelConfig:
        """Get default configuration from settings."""
        # Try to find a valid model from the database
        default_provider = settings.llm_provider
        default_model_id = settings.llm_default_model or settings.llm_model
        
        # Verify the model exists in database
        model_config = self.db.query(ModelConfiguration).filter_by(
            model_id=default_model_id,
            is_available=True,
            is_deprecated=False
        ).first()
        
        # If not found, try to find any available model for the provider
        if not model_config:
            model_config = self.db.query(ModelConfiguration).filter_by(
                provider=default_provider,
                is_available=True,
                is_deprecated=False
            ).first()
        
        # If still not found, get any available model
        if not model_config:
            model_config = self.db.query(ModelConfiguration).filter_by(
                is_available=True,
                is_deprecated=False
            ).first()
        
        # Use found model or fallback to settings
        if model_config:
            actual_provider = model_config.provider
            actual_model_id = model_config.model_id
        else:
            logger.warning(
                f"No valid model found in database, using settings: {default_provider}/{default_model_id}"
            )
            actual_provider = default_provider
            actual_model_id = default_model_id
        
        return UnifiedModelConfig(
            provider=actual_provider,
            model_id=actual_model_id,
            temperature=0.7,
            max_tokens=None,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            enable_reasoning=settings.enable_reasoning,
            reasoning_effort=settings.reasoning_effort,
            claude_extended_thinking=settings.claude_extended_thinking,
            claude_thinking_mode=settings.claude_thinking_mode,
            claude_thinking_budget_tokens=settings.claude_thinking_budget_tokens,
        )

    def _model_config_to_info(self, model: ModelConfiguration) -> ModelInfo:
        """Convert ModelConfiguration to ModelInfo."""
        from app.schemas.generation import ModelCapabilities

        capabilities = ModelCapabilities()
        if model.capabilities:
            capabilities = ModelCapabilities(**model.capabilities)

        return ModelInfo(
            model_id=model.model_id,
            display_name=model.name,
            provider=model.provider,
            model_family=model.model_family,
            capabilities=capabilities,
            cost_per_1k_input_tokens=model.cost_input_per_1k,
            cost_per_1k_output_tokens=model.cost_output_per_1k,
            performance_tier="balanced",  # Default tier since not in model table
            average_latency_ms=model.avg_response_time_ms,
            is_available=model.is_available,
            is_deprecated=model.is_deprecated,
            deprecation_date=getattr(model, 'deprecation_date', None),
            recommended_use_cases=getattr(model, 'recommended_use_cases', []) or [],
        )

