# app/services/unified_config_service.py
"""
Unified configuration service for AI model settings.
Single source of truth using RuntimeConfig table.
"""
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.config import RuntimeConfig, ConfigHistory, ModelConfiguration
from app.schemas.generation import (
    UnifiedModelConfig,
    ModelInfo,
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
    
    # Cache TTL in seconds (5 minutes)
    CACHE_TTL_SECONDS = 300

    def __init__(self, db: Session):
        self.db = db
        self._config_cache = {}
        self._cache_timestamp = None

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

        # Apply updates directly - Pydantic model handles camelCase aliases
        updated_dict = current.model_dump()
        updated_dict.update(updates)

        # Create new config instance for validation
        try:
            new_config = UnifiedModelConfig(**updated_dict)
        except ValueError as e:
            raise ValueError(f"Invalid configuration: {e}")

        # Validate using enhanced validation
        is_valid, error = self.validate_config(new_config.model_dump())
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

    async def test_config(self, config: UnifiedModelConfig, dry_run: bool = False) -> Dict[str, Any]:
        """Test configuration with actual API call or dry-run validation."""
        import time
        
        # For dry-run, only validate without making actual API calls
        if dry_run:
            start_time = time.time()
            
            # Validate configuration
            is_valid, error = self.validate_config(config.model_dump())
            
            # Check if model exists in database
            model_info = self.get_model_info(config.model_id)
            if not model_info:
                return {
                    "success": False,
                    "message": f"Model '{config.model_id}' not found",
                    "error": "model_not_found",
                    "dry_run": True
                }
                
            if not is_valid:
                return {
                    "success": False,
                    "message": "Configuration validation failed",
                    "error": error,
                    "dry_run": True
                }
                
            elapsed = time.time() - start_time
            
            return {
                "success": True,
                "message": "Configuration validation successful (dry-run)",
                "response_time": round(elapsed, 3),
                "model": config.model_id,
                "provider": config.provider,
                "dry_run": True,
                "model_info": {
                    "display_name": model_info.display_name,
                    "capabilities": model_info.capabilities.model_dump() if model_info.capabilities else {},
                    "cost_per_1k_input": model_info.cost_per_1k_input_tokens,
                    "cost_per_1k_output": model_info.cost_per_1k_output_tokens,
                }
            }
        
        # Actual API test (non dry-run)
        from app.llm.client import llm_client as client
        import asyncio

        start_time = time.time()
        snapshot = client.snapshot()

        try:
            # Create temporary client with test config
            await client.reconfigure(
                provider=config.provider,
                model=config.model_id,
                use_responses_api=config.use_responses_api,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                top_p=config.top_p,
                frequency_penalty=config.frequency_penalty,
                presence_penalty=config.presence_penalty,
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
                "dry_run": False
            }

        except asyncio.TimeoutError:
            return {
                "success": False,
                "message": "Test timed out after 30 seconds",
                "error": "timeout",
                "dry_run": False
            }
        except Exception as e:
            logger.error(f"Configuration test failed: {e}")
            return {
                "success": False,
                "message": "Configuration test failed",
                "error": str(e),
                "dry_run": False
            }
        finally:
            await client.restore(snapshot)

    # Private methods

    def _load_all_config(self) -> Dict[str, Any]:
        """Load all configuration from RuntimeConfig with TTL-based cache."""
        # Check if cache is still valid
        if self._config_cache and self._cache_timestamp:
            from datetime import datetime, timedelta
            if datetime.utcnow() - self._cache_timestamp < timedelta(seconds=self.CACHE_TTL_SECONDS):
                return self._config_cache

        configs = self.db.query(RuntimeConfig).all()
        result = {}

        for config in configs:
            try:
                # Handle different value types
                if config.value_type == "string":
                    result[config.key] = config.value
                elif config.value_type == "number":
                    # Preserve numeric types returned by PostgreSQL JSONB
                    if isinstance(config.value, (int, float)):
                        result[config.key] = config.value
                    else:
                        # Fallback to safe parsing for legacy string rows
                        try:
                            result[config.key] = int(config.value)
                        except (ValueError, TypeError):
                            try:
                                result[config.key] = float(config.value)
                            except (ValueError, TypeError):
                                # Leave as-is to avoid raising during load
                                result[config.key] = config.value
                elif config.value_type == "boolean":
                    result[config.key] = config.value in [True, "true", "True", "1", 1]
                elif config.value_type in ("object", "array"):
                    # Value stored as native JSONB; return as-is
                    result[config.key] = config.value
                else:
                    result[config.key] = config.value
            except Exception as e:
                logger.warning(f"Failed to parse config {config.key}: {e}")
                result[config.key] = config.value

        self._config_cache = result
        from datetime import datetime
        self._cache_timestamp = datetime.utcnow()
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
            elif isinstance(value, dict):
                value_type = "object"
            elif isinstance(value, list):
                value_type = "array"
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
            self.db.expire_all()    # ensure subsequent reads hit DB
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
        # Deprecated ``settings.llm_model`` removed; rely solely on *llm_default_model*
        default_model_id = settings.llm_default_model

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

    # ------------------------------------------------------------------
    # Presets / Defaults helpers
    # ------------------------------------------------------------------
    def get_presets(self) -> List[Dict[str, Any]]:
        """
        Return predefined configuration presets optimised for common
        scenarios (balanced, creative, precise, fast, powerful).

        The router delegates to this method so the presets live in the
        service layer rather than being duplicated in the API route.
        """
        return [
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
                "description": "Optimised for quick responses",
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

    def get_defaults(self) -> dict[str, Any]:
        """
        Return the *authoritative* default configuration in camelCase
        so the frontend never hard-codes fallback values.
        """
        return self._get_default_config().model_dump(by_alias=True)

