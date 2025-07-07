
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
    ProviderConfig,
    validate_config_consistency
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
        self, 
        updates: Dict[str, Any], 
        updated_by: str = "api"
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
        # Try database first
        model_config = self.db.query(ModelConfiguration).filter_by(
            model_id=model_id
        ).first()
        
        if model_config:
            return self._model_config_to_info(model_config)
        
        # Fallback to static catalog
        return self._get_static_model_info(model_id)
    
    def get_available_models(
        self, 
        provider: Optional[str] = None,
        include_deprecated: bool = False
    ) -> List[ModelInfo]:
        """Get all available models."""
        models = []
        
        # Load from database
        query = self.db.query(ModelConfiguration)
        if provider:
            query = query.filter_by(provider=provider)
        if not include_deprecated:
            query = query.filter_by(is_deprecated=False)
        
        db_models = query.all()
        models.extend([self._model_config_to_info(m) for m in db_models])
        
        # Add static models not in database
        static_models = self._get_static_models()
        existing_ids = {m.model_id for m in models}
        
        for static_model in static_models:
            if static_model.model_id not in existing_ids:
                if not provider or static_model.provider == provider:
                    models.append(static_model)
        
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
    
    def validate_config(self, config_dict: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate configuration dictionary."""
        try:
            # Try to create UnifiedModelConfig
            config = UnifiedModelConfig(**config_dict)
            
            # Validate consistency
            return validate_config_consistency(config)
            
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
                use_responses_api=config.use_responses_api
            )
            
            # Simple test message
            test_messages = [
                {"role": "system", "content": "You are a test assistant."},
                {"role": "user", "content": "Say 'test successful' and nothing else."}
            ]
            
            # Test with timeout
            response = await asyncio.wait_for(
                client.complete(
                    messages=test_messages,
                    model=config.model_id,
                    temperature=config.temperature,
                    max_tokens=10,
                    stream=False
                ),
                timeout=30.0
            )
            
            elapsed = time.time() - start_time
            
            return {
                "success": True,
                "message": "Configuration test successful",
                "response_time": round(elapsed, 2),
                "model": config.model_id,
                "provider": config.provider
            }
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "message": "Test timed out after 30 seconds",
                "error": "timeout"
            }
        except Exception as e:
            logger.error(f"Configuration test failed: {e}")
            return {
                "success": False,
                "message": "Configuration test failed",
                "error": str(e)
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
                    result[config.key] = float(config.value) if "." in str(config.value) else int(config.value)
                elif config.value_type == "boolean":
                    result[config.key] = config.value in [True, "true", "True", "1", 1]
                elif config.value_type == "object":
                    result[config.key] = json.loads(config.value) if isinstance(config.value, str) else config.value
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
                        changed_by=updated_by
                    )
                    self.db.add(history)
                
                # Update value
                existing.value = value
                existing.value_type = value_type
                existing.updated_by = updated_by
            else:
                # Create new
                new_config = RuntimeConfig(
                    key=key,
                    value=value,
                    value_type=value_type,
                    updated_by=updated_by
                )
                self.db.add(new_config)
        
        try:
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError(f"Configuration update failed: {e}")
    
    def _get_default_config(self) -> UnifiedModelConfig:
        """Get default configuration from settings."""
        return UnifiedModelConfig(
            provider=settings.llm_provider,
            model_id=settings.llm_default_model or settings.llm_model,
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
            performance_tier=model.tier,
            average_latency_ms=model.avg_response_time_ms,
            is_available=model.is_available,
            is_deprecated=model.is_deprecated,
            deprecation_date=model.deprecation_date,
            recommended_use_cases=model.recommended_use_cases or []
        )
    
    def _get_static_models(self) -> List[ModelInfo]:
        """Get static model catalog."""
        # This would be populated from a configuration file or hardcoded catalog
        # For now, returning common models
        return [
            ModelInfo(
                model_id="gpt-4o-mini",
                display_name="GPT-4 Omni Mini",
                provider="openai",
                model_family="gpt-4",
                capabilities={
                    "supports_functions": True,
                    "supports_vision": True,
                    "max_context_window": 128000,
                    "max_output_tokens": 4096
                },
                cost_per_1k_input_tokens=0.00015,
                cost_per_1k_output_tokens=0.0006,
                performance_tier="fast",
                recommended_use_cases=["general", "code", "analysis"]
            ),
            ModelInfo(
                model_id="gpt-4o",
                display_name="GPT-4 Omni",
                provider="openai",
                model_family="gpt-4",
                capabilities={
                    "supports_functions": True,
                    "supports_vision": True,
                    "max_context_window": 128000,
                    "max_output_tokens": 4096
                },
                cost_per_1k_input_tokens=0.0025,
                cost_per_1k_output_tokens=0.01,
                performance_tier="balanced",
                recommended_use_cases=["complex", "code", "creative"]
            ),
            # Add more models as needed
        ]
    
    def _get_static_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """Get static model info by ID."""
        static_models = self._get_static_models()
        for model in static_models:
            if model.model_id == model_id:
                return model
        return None
