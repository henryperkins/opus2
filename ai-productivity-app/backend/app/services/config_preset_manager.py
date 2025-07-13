"""
Configuration preset manager that ensures provider compatibility
and handles preset application with proper validation.
"""

import logging
from typing import Dict, Any, List, Optional
from app.schemas.generation import UnifiedModelConfig
from app.services.config_validation_service import ConfigValidationService
from app.services.model_service import ModelService
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ConfigPresetManager:
    """
    Manages configuration presets with provider awareness and compatibility checking.
    """
    
    # Model equivalence mapping for cross-provider adaptation
    MODEL_EQUIVALENCE_MAP = {
        "small": {
            "openai": "gpt-4o-mini",
            "azure": "o4-mini",
            "anthropic": "claude-3-5-haiku-20241022"
        },
        "medium": {
            "openai": "gpt-4o",
            "azure": "gpt-4.1",
            "anthropic": "claude-3-5-sonnet-20241022"
        },
        "large": {
            "openai": "gpt-4o",
            "azure": "o3",
            "anthropic": "claude-opus-4-20250514"
        },
        "latest": {
            "openai": "gpt-4o",
            "azure": "o3",
            "anthropic": "claude-sonnet-4-20250522"
        }
    }
    
    # Provider-specific parameter adjustments
    PROVIDER_PARAM_ADJUSTMENTS = {
        "azure": {
            "reasoning_models": ["o3", "o3-mini", "o1", "o1-mini"],
            "reasoning_temperature": 1.0,  # Azure reasoning models require temp=1.0
            "requires_responses_api": True
        },
        "anthropic": {
            "thinking_models": ["claude-opus-4-20250514", "claude-sonnet-4-20250522"],
            "supports_extended_thinking": True,
            "max_output_tokens": {
                "claude-opus-4-20250514": 32000,
                "claude-sonnet-4-20250522": 64000,
                "claude-3-5-haiku-20241022": 8000
            }
        }
    }
    
    # Updated presets with provider-specific configurations
    DEFAULT_PRESETS = [
        {
            "id": "balanced",
            "name": "Balanced",
            "description": "Good balance of quality and speed",
            "provider_configs": {
                "openai": {
                    "model_id": "gpt-4o-mini",
                    "temperature": 0.7,
                    "max_tokens": 2048,
                    "top_p": 0.95,
                },
                "azure": {
                    "model_id": "gpt-4.1",
                    "temperature": 0.7,
                    "max_tokens": 2048,
                    "top_p": 0.95,
                    "use_responses_api": True,
                },
                "anthropic": {
                    "model_id": "claude-3-5-sonnet-20241022",
                    "temperature": 0.7,
                    "max_tokens": 2048,
                    "top_p": 0.95,
                    "claude_extended_thinking": True,
                    "claude_thinking_mode": "enabled",
                }
            }
        },
        {
            "id": "creative",
            "name": "Creative",
            "description": "More creative and varied responses",
            "provider_configs": {
                "openai": {
                    "model_id": "gpt-4o",
                    "temperature": 1.2,
                    "max_tokens": 3000,
                    "top_p": 0.95,
                    "frequency_penalty": 0.2,
                    "presence_penalty": 0.2,
                },
                "azure": {
                    "model_id": "gpt-4.1",
                    "temperature": 1.2,
                    "max_tokens": 3000,
                    "top_p": 0.95,
                    "frequency_penalty": 0.2,
                    "presence_penalty": 0.2,
                    "use_responses_api": True,
                },
                "anthropic": {
                    "model_id": "claude-sonnet-4-20250522",
                    "temperature": 1.2,
                    "max_tokens": 3000,
                    "top_p": 0.95,
                    "frequency_penalty": 0.2,
                    "presence_penalty": 0.2,
                    "claude_extended_thinking": True,
                    "claude_thinking_mode": "enabled",
                }
            }
        },
        {
            "id": "fast",
            "name": "Fast",
            "description": "Optimized for quick responses",
            "provider_configs": {
                "openai": {
                    "model_id": "gpt-4o-mini",
                    "temperature": 0.7,
                    "max_tokens": 1024,
                },
                "azure": {
                    "model_id": "o4-mini",
                    "temperature": 0.7,
                    "max_tokens": 1024,
                    "enable_reasoning": True,
                    "reasoning_effort": "low",
                    "use_responses_api": True,
                },
                "anthropic": {
                    "model_id": "claude-3-5-haiku-20241022",
                    "temperature": 0.7,
                    "max_tokens": 1024,
                    "claude_extended_thinking": False,
                }
            }
        },
        {
            "id": "powerful",
            "name": "Powerful",
            "description": "Maximum capability for complex tasks",
            "provider_configs": {
                "openai": {
                    "model_id": "gpt-4o",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "enable_reasoning": True,
                    "reasoning_effort": "high",
                },
                "azure": {
                    "model_id": "o3",
                    "temperature": 1.0,  # Reasoning models require temperature=1.0
                    "max_tokens": 100000,  # o3 supports up to 100K output
                    "enable_reasoning": True,
                    "reasoning_effort": "high",
                    "use_responses_api": True,
                },
                "anthropic": {
                    "model_id": "claude-opus-4-20250514",
                    "temperature": 0.7,
                    "max_tokens": 32000,  # Opus 4 max output
                    "claude_extended_thinking": True,
                    "claude_thinking_mode": "aggressive",
                    "claude_thinking_budget_tokens": 65536,
                }
            }
        },
        {
            "id": "coding",
            "name": "Coding Specialist",
            "description": "Optimized for software development tasks",
            "provider_configs": {
                "openai": {
                    "model_id": "gpt-4o",
                    "temperature": 0.2,
                    "max_tokens": 4096,
                    "top_p": 0.95,
                },
                "azure": {
                    "model_id": "o3",
                    "temperature": 1.0,
                    "max_tokens": 32000,
                    "enable_reasoning": True,
                    "reasoning_effort": "medium",
                    "use_responses_api": True,
                },
                "anthropic": {
                    "model_id": "claude-opus-4-20250514",
                    "temperature": 0.2,
                    "max_tokens": 32000,
                    "claude_extended_thinking": True,
                    "claude_thinking_mode": "enabled",
                    "claude_thinking_budget_tokens": 32768,
                }
            }
        }
    ]
    
    def __init__(self, db: Session):
        self.db = db
        self.validation_service = ConfigValidationService(db)
        self.model_service = ModelService(db)
    
    def get_presets(self) -> List[Dict[str, Any]]:
        """
        Get all available presets in a format compatible with the frontend.
        Returns presets with a generic config that will be adapted based on provider.
        """
        presets = []
        for preset in self.DEFAULT_PRESETS:
            # Return a generic representation that will be adapted based on current provider
            # We include a hint about provider adaptability in the description
            presets.append({
                "id": preset["id"],
                "name": preset["name"],
                "description": f"{preset['description']} (adapts to your provider)",
                "provider_configs": preset["provider_configs"]  # Include all configs for transparency
            })
        return presets
    
    def apply_preset(
        self, 
        preset_id: str, 
        current_config: UnifiedModelConfig,
        target_provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Apply a preset configuration, adapting it to the target provider.
        Returns the configuration update to be applied.
        """
        # Find the preset
        preset = None
        for p in self.DEFAULT_PRESETS:
            if p["id"] == preset_id:
                preset = p
                break
        
        if not preset:
            raise ValueError(f"Preset '{preset_id}' not found")
        
        # Determine target provider
        provider = target_provider or current_config.provider
        
        # Get provider-specific configuration
        provider_config = preset["provider_configs"].get(provider)
        
        if not provider_config:
            # Fallback to intelligent adaptation
            logger.info(f"No specific config for provider {provider} in preset {preset_id}, adapting...")
            provider_config = self._create_adapted_config(preset, provider, current_config)
        else:
            # Clone the config to avoid mutating the original
            provider_config = provider_config.copy()
        
        # Apply provider-specific adjustments
        provider_config = self._apply_provider_adjustments(provider_config, provider)
        
        # Ensure the model is available for the provider
        model_id = provider_config.get("model_id")
        if model_id:
            # Verify model exists and is available
            if not self._verify_model_availability(model_id, provider):
                # Find an equivalent model
                equivalent = self._find_equivalent_model(model_id, provider, preset_id)
                if equivalent:
                    logger.info(f"Substituting {model_id} with {equivalent} for provider {provider}")
                    provider_config["model_id"] = equivalent
                else:
                    logger.warning(f"No equivalent model found for {model_id} on {provider}")
                    # Use a safe default from the provider
                    provider_config["model_id"] = self._get_default_model_for_provider(provider)
        
        # Add provider to the config to ensure consistency
        provider_config["provider"] = provider
        
        # Clean up provider-specific fields based on the target provider
        provider_config = self._clean_provider_specific_fields(provider_config, provider)
        
        return provider_config
    
    def _create_adapted_config(
        self, 
        preset: Dict[str, Any], 
        provider: str,
        current_config: UnifiedModelConfig
    ) -> Dict[str, Any]:
        """
        Create an adapted configuration for a provider not explicitly defined in the preset.
        """
        # Start with the most similar provider's config as a base
        base_config = None
        
        # Priority order for similarity
        similarity_map = {
            "azure": ["openai", "anthropic"],
            "openai": ["azure", "anthropic"],
            "anthropic": ["openai", "azure"]
        }
        
        for similar_provider in similarity_map.get(provider, []):
            if similar_provider in preset["provider_configs"]:
                base_config = preset["provider_configs"][similar_provider].copy()
                break
        
        if not base_config:
            # Fallback to the first available config
            base_config = list(preset["provider_configs"].values())[0].copy()
        
        # Adapt the configuration for the target provider
        adapted_config = self._adapt_config_for_provider(base_config, provider)
        
        return adapted_config
    
    def _adapt_config_for_provider(self, config: Dict[str, Any], provider: str) -> Dict[str, Any]:
        """
        Adapt a configuration from one provider to another.
        """
        adapted = config.copy()
        
        # Find equivalent model based on capability tier
        model_id = adapted.get("model_id")
        if model_id:
            # Determine the capability tier of the original model
            tier = self._get_model_tier(model_id)
            if tier and tier in self.MODEL_EQUIVALENCE_MAP:
                new_model = self.MODEL_EQUIVALENCE_MAP[tier].get(provider)
                if new_model:
                    adapted["model_id"] = new_model
        
        # Apply provider-specific adjustments
        adapted = self._apply_provider_adjustments(adapted, provider)
        
        return adapted
    
    def _apply_provider_adjustments(self, config: Dict[str, Any], provider: str) -> Dict[str, Any]:
        """
        Apply provider-specific parameter adjustments.
        """
        adjusted = config.copy()
        
        if provider == "azure":
            # Check if using a reasoning model
            model_id = adjusted.get("model_id", "")
            if any(model in model_id for model in self.PROVIDER_PARAM_ADJUSTMENTS["azure"]["reasoning_models"]):
                # Azure reasoning models require specific settings
                adjusted["temperature"] = self.PROVIDER_PARAM_ADJUSTMENTS["azure"]["reasoning_temperature"]
                adjusted["enable_reasoning"] = True
                if "reasoning_effort" not in adjusted:
                    adjusted["reasoning_effort"] = "medium"
            
            # Azure typically uses Responses API
            adjusted["use_responses_api"] = self.PROVIDER_PARAM_ADJUSTMENTS["azure"]["requires_responses_api"]
            
        elif provider == "anthropic":
            # Check if using a thinking model
            model_id = adjusted.get("model_id", "")
            if model_id in self.PROVIDER_PARAM_ADJUSTMENTS["anthropic"]["thinking_models"]:
                # Enable extended thinking for capable models
                adjusted["claude_extended_thinking"] = True
                if "claude_thinking_mode" not in adjusted:
                    adjusted["claude_thinking_mode"] = "enabled"
                if "claude_thinking_budget_tokens" not in adjusted:
                    adjusted["claude_thinking_budget_tokens"] = 16384
            
            # Adjust max tokens based on model capabilities
            max_tokens_map = self.PROVIDER_PARAM_ADJUSTMENTS["anthropic"]["max_output_tokens"]
            if model_id in max_tokens_map:
                max_allowed = max_tokens_map[model_id]
                if adjusted.get("max_tokens", 0) > max_allowed:
                    adjusted["max_tokens"] = max_allowed
        
        elif provider == "openai":
            # OpenAI models support standard reasoning
            if adjusted.get("enable_reasoning"):
                if "reasoning_effort" not in adjusted:
                    adjusted["reasoning_effort"] = "medium"
        
        return adjusted
    
    def _clean_provider_specific_fields(self, config: Dict[str, Any], provider: str) -> Dict[str, Any]:
        """
        Remove fields that are not applicable to the target provider.
        """
        cleaned = config.copy()
        
        # Fields specific to each provider
        azure_only_fields = ["use_responses_api"]
        anthropic_only_fields = ["claude_extended_thinking", "claude_thinking_mode", "claude_thinking_budget_tokens"]
        openai_azure_fields = ["enable_reasoning", "reasoning_effort"]
        
        if provider == "azure":
            # Remove Anthropic-specific fields
            for field in anthropic_only_fields:
                cleaned.pop(field, None)
        elif provider == "anthropic":
            # Remove Azure and OpenAI reasoning fields
            for field in azure_only_fields + openai_azure_fields:
                cleaned.pop(field, None)
        elif provider == "openai":
            # Remove Azure and Anthropic specific fields
            for field in azure_only_fields + anthropic_only_fields:
                cleaned.pop(field, None)
        
        return cleaned
    
    def _get_model_tier(self, model_id: str) -> Optional[str]:
        """
        Determine the capability tier of a model.
        """
        # Map models to their tiers
        model_tier_map = {
            # Small/Fast models
            "gpt-4o-mini": "small",
            "o4-mini": "small",
            "claude-3-5-haiku-20241022": "small",
            
            # Medium models
            "gpt-4.1": "medium",
            "claude-3-5-sonnet-20241022": "medium",
            
            # Large/Powerful models
            "gpt-4o": "large",
            "o3": "large",
            "o3-mini": "medium",  # Despite name, it's quite capable
            "claude-opus-4-20250514": "large",
            
            # Latest models
            "claude-sonnet-4-20250522": "latest",
        }
        
        return model_tier_map.get(model_id)
    
    def _find_equivalent_model(self, model_id: str, provider: str, preset_id: str) -> Optional[str]:
        """
        Find an equivalent model for the given provider based on capability matching.
        """
        # Get the tier of the original model
        tier = self._get_model_tier(model_id)
        
        if tier and tier in self.MODEL_EQUIVALENCE_MAP:
            return self.MODEL_EQUIVALENCE_MAP[tier].get(provider)
        
        # If no direct mapping, try to match based on preset intent
        preset_model_hints = {
            "fast": "small",
            "balanced": "medium",
            "powerful": "large",
            "creative": "latest",
            "coding": "large"
        }
        
        hint_tier = preset_model_hints.get(preset_id)
        if hint_tier and hint_tier in self.MODEL_EQUIVALENCE_MAP:
            return self.MODEL_EQUIVALENCE_MAP[hint_tier].get(provider)
        
        return None
    
    def _verify_model_availability(self, model_id: str, provider: str) -> bool:
        """
        Verify if a model is available for the given provider.
        """
        try:
            model_info = self.model_service.get_model_info(model_id)
            return model_info and model_info.provider == provider and model_info.is_available
        except Exception:
            # If we can't verify, assume it might not be available
            return False
    
    def _get_default_model_for_provider(self, provider: str) -> str:
        """
        Get a safe default model for the provider.
        """
        defaults = {
            "openai": "gpt-4o-mini",
            "azure": "gpt-4.1",
            "anthropic": "claude-3-5-sonnet-20241022"
        }
        return defaults.get(provider, "gpt-4o-mini")
