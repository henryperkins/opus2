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
    
    # Default presets with provider-specific configurations
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
                    "model_id": "claude-opus-4-20250514",
                    "temperature": 1.2,
                    "max_tokens": 3000,
                    "top_p": 0.95,
                    "claude_extended_thinking": True,
                    "claude_thinking_mode": "aggressive",
                    "claude_thinking_budget_tokens": 32768,
                }
            }
        },
        {
            "id": "precise",
            "name": "Precise",
            "description": "Deterministic responses",
            "provider_configs": {
                "openai": {
                    "model_id": "gpt-4o",
                    "temperature": 0.3,
                    "max_tokens": 2048,
                    "top_p": 0.9,
                },
                "azure": {
                    "model_id": "gpt-4.1",
                    "temperature": 0.3,
                    "max_tokens": 2048,
                    "top_p": 0.9,
                    "use_responses_api": True,
                },
                "anthropic": {
                    "model_id": "claude-3-5-sonnet-20241022",
                    "temperature": 0.3,
                    "max_tokens": 2048,
                    "top_p": 0.9,
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
                    "model_id": "gpt-4.1-mini",
                    "temperature": 0.7,
                    "max_tokens": 1024,
                },
                "anthropic": {
                    "model_id": "claude-3-5-sonnet-20241022",
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
                    "max_tokens": 4096,
                    "enable_reasoning": True,
                    "reasoning_effort": "high",
                    "use_responses_api": True,
                },
                "anthropic": {
                    "model_id": "claude-opus-4-20250514",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "claude_extended_thinking": True,
                    "claude_thinking_mode": "aggressive",
                    "claude_thinking_budget_tokens": 65536,
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
            # ------------------------------------------------------------------
            # The original implementation always returned the **OpenAI** variant
            # *without* its associated provider field.  That caused 422 errors
            # whenever the active configuration used a different provider – the
            # frontend patched a model like "gpt-4o" while the server kept the
            # previous provider (e.g. "azure"), triggering a validation
            # mismatch (model does not belong to provider).
            #
            # To keep the payload compact *and* unambiguous we still expose a
            # single representative configuration **but** we now embed the
            # corresponding `provider` so the backend can switch both fields in
            # one PATCH request.
            # ------------------------------------------------------------------

            # Pick the OpenAI variant as the generic example (unchanged)
            # Grab the OpenAI variant and emit **camelCase** keys so the
            # frontend can PATCH the object verbatim (ConfigUpdate expects
            # camelCase – `modelId`, `maxTokens` …).  We also embed the
            # corresponding provider so that both fields are switched in one
            # round-trip.

            raw_cfg = preset["provider_configs"].get("openai", {})

            # Convert snake_case → camelCase to comply with the API contract
            def _to_camel(s: str) -> str:
                parts = s.split("_")
                return parts[0] + "".join(p.title() for p in parts[1:])

            config = {(_to_camel(k) if "_" in k else k): v for k, v in raw_cfg.items()}

            # Ensure provider travels with the patch payload
            config.setdefault("provider", "openai")
            presets.append({
                "id": preset["id"],
                "name": preset["name"],
                "description": preset["description"],
                "config": config  # Generic config for display
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
            # Fallback to a compatible configuration
            logger.warning(f"No specific config for provider {provider} in preset {preset_id}")
            # Try to adapt from another provider
            if "openai" in preset["provider_configs"]:
                provider_config = self._adapt_config_for_provider(
                    preset["provider_configs"]["openai"], 
                    provider
                )
            else:
                # Use first available config
                provider_config = list(preset["provider_configs"].values())[0]
                provider_config = self._adapt_config_for_provider(provider_config, provider)
        
        # Ensure the model is available for the provider
        model_id = provider_config.get("model_id")
        if model_id:
            model_info = self.model_service.get_model_info(model_id)
            if model_info and model_info.provider != provider:
                # Find an equivalent model for the provider
                equivalent = self._find_equivalent_model(model_id, provider)
                if equivalent:
                    provider_config["model_id"] = equivalent
                else:
                    logger.warning(f"No equivalent model found for {model_id} on {provider}")
                    # Remove model_id to avoid validation errors
                    provider_config.pop("model_id", None)
        
        # Add provider to the config
        provider_config["provider"] = provider
        
        return provider_config
    
    def _adapt_config_for_provider(self, config: Dict[str, Any], provider: str) -> Dict[str, Any]:
        """
        Adapt a configuration from one provider to another.
        """
        adapted = config.copy()
        
        if provider == "anthropic":
            # Convert standard reasoning to Claude thinking
            if adapted.get("enable_reasoning"):
                adapted.pop("enable_reasoning", None)
                adapted.pop("reasoning_effort", None)
                adapted["claude_extended_thinking"] = True
                adapted["claude_thinking_mode"] = "enabled"
            
            # Remove Azure-specific settings
            adapted.pop("use_responses_api", None)
            
        elif provider in ["azure", "openai"]:
            # Convert Claude thinking to reasoning
            if adapted.get("claude_extended_thinking"):
                adapted.pop("claude_extended_thinking", None)
                adapted.pop("claude_thinking_mode", None)
                adapted.pop("claude_thinking_budget_tokens", None)
                adapted["enable_reasoning"] = True
                adapted["reasoning_effort"] = "medium"
            
            # Add Azure-specific settings
            if provider == "azure":
                model_id = adapted.get("model_id", "")
                if ModelService.requires_responses_api_static(model_id):
                    adapted["use_responses_api"] = True
        
        return adapted
    
    def _find_equivalent_model(self, model_id: str, provider: str) -> Optional[str]:
        """
        Find an equivalent model for a different provider.
        """
        # Model equivalence mapping
        equivalence_map = {
            "gpt-4o": {
                "azure": "gpt-4.1",
                "anthropic": "claude-3-5-sonnet-20241022"
            },
            "gpt-4o-mini": {
                "azure": "gpt-4.1-mini",
                "anthropic": "claude-3-5-sonnet-20241022"
            },
            "gpt-4.1": {
                "openai": "gpt-4o",
                "anthropic": "claude-3-5-sonnet-20241022"
            },
            "o3": {
                "openai": "gpt-4o",
                "anthropic": "claude-opus-4-20250514"
            },
            "claude-3-5-sonnet-20241022": {
                "openai": "gpt-4o-mini",
                "azure": "gpt-4.1"
            },
            "claude-opus-4-20250514": {
                "openai": "gpt-4o",
                "azure": "o3"
            }
        }
        
        if model_id in equivalence_map:
            return equivalence_map[model_id].get(provider)
        
        # If no direct mapping, try to find a model with similar capabilities
        original_info = self.model_service.get_model_info(model_id)
        if not original_info:
            return None
        
        # Find models with similar capabilities for the target provider
        available_models = self.db.query(ModelConfiguration).filter_by(
            provider=provider,
            is_available=True,
            is_deprecated=False
        ).all()
        
        best_match = None
        best_score = 0
        
        for model in available_models:
            score = 0
            if model.capabilities:
                # Score based on matching capabilities
                if model.capabilities.get("supports_reasoning") == original_info.capabilities.supports_reasoning:
                    score += 2
                if model.capabilities.get("supports_functions") == original_info.capabilities.supports_functions:
                    score += 1
                if model.capabilities.get("supports_streaming") == original_info.capabilities.supports_streaming:
                    score += 1
                
                # Prefer models with similar context windows
                if abs(model.capabilities.get("max_context_window", 0) - original_info.capabilities.max_context_window) < 10000:
                    score += 1
            
            if score > best_score:
                best_score = score
                best_match = model.model_id
        
        return best_match
