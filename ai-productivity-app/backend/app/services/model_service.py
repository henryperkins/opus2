"""Centralized service for model capabilities and information.

This service provides a unified interface for querying model capabilities,
validation, and metadata from the ModelConfiguration database.
"""

import logging
from typing import Dict, Any, Optional, List, Set
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.config import ModelConfiguration
from app.schemas.generation import ModelInfo, ModelCapabilities

logger = logging.getLogger(__name__)


class ModelService:
    """Centralized service for model capabilities and validation."""
    
    def __init__(self, db: Session):
        self.db = db
        self._cache: Dict[str, Any] = {}
    
    def get_model_capabilities(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model capabilities from database."""
        cache_key = f"capabilities_{model_id}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            model = self.db.query(ModelConfiguration).filter_by(model_id=model_id).first()
            if model and model.capabilities:
                capabilities = model.capabilities
                self._cache[cache_key] = capabilities
                return capabilities
        except SQLAlchemyError as e:
            logger.error(f"Database error getting capabilities for {model_id}: {e}")
        
        return None
    
    def get_model_metadata(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model metadata from database."""
        cache_key = f"metadata_{model_id}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            model = self.db.query(ModelConfiguration).filter_by(model_id=model_id).first()
            if model and model.model_metadata:
                metadata = model.model_metadata
                self._cache[cache_key] = metadata
                return metadata
        except SQLAlchemyError as e:
            logger.error(f"Database error getting metadata for {model_id}: {e}")
        
        return None
    
    def is_reasoning_model(self, model_id: str) -> bool:
        """Check if model supports reasoning."""
        capabilities = self.get_model_capabilities(model_id)
        if capabilities:
            return capabilities.get('supports_reasoning', False)
        
        # Fallback to pattern matching
        model_lower = model_id.lower()
        reasoning_models = {
            "o1",
            "o1-mini",
            "o1-preview",
            "o1-pro",
            "o3",
            "o3-mini",
            "o3-pro",
            "o4-mini",
        }
        return model_lower in reasoning_models
    
    def supports_streaming(self, model_id: str) -> bool:
        """Check if model supports streaming."""
        capabilities = self.get_model_capabilities(model_id)
        if capabilities:
            return capabilities.get('supports_streaming', True)
        
        # Reasoning models typically don't support streaming
        if self.is_reasoning_model(model_id):
            return False
        
        return True  # Default assumption
    
    def supports_functions(self, model_id: str) -> bool:
        """Check if model supports function calling."""
        capabilities = self.get_model_capabilities(model_id)
        if capabilities:
            return capabilities.get('supports_functions', True)
        
        # Reasoning models typically don't support functions
        if self.is_reasoning_model(model_id):
            return False
        
        return True  # Default assumption
    
    def supports_vision(self, model_id: str) -> bool:
        """Check if model supports vision/image inputs."""
        capabilities = self.get_model_capabilities(model_id)
        if capabilities:
            return capabilities.get('supports_vision', False)
        
        # Pattern-based fallback
        vision_patterns = ['gpt-4o', 'claude']
        return any(pattern in model_id.lower() for pattern in vision_patterns)
    
    def supports_json_mode(self, model_id: str) -> bool:
        """Check if model supports JSON mode."""
        capabilities = self.get_model_capabilities(model_id)
        if capabilities:
            return capabilities.get('supports_json_mode', False)
        
        # OpenAI models typically support JSON mode
        return 'gpt' in model_id.lower()
    
    def requires_responses_api(self, model_id: str) -> bool:
        """Check if model requires Azure Responses API."""
        metadata = self.get_model_metadata(model_id)
        if metadata:
            return metadata.get('requires_responses_api', False)
        
        # Fallback to pattern matching
        model_lower = model_id.lower()
        responses_api_models = {
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4.1",
            "computer-use-preview",
            "o3",
            "o3-mini",
            "o3-pro",
            "o4-mini",
            "o1",
            "o1-mini",
            "o1-preview",
            "o1-pro",
        }
        return model_lower in responses_api_models
    
    def supports_thinking(self, model_id: str) -> bool:
        """Check if model supports Claude-style thinking."""
        metadata = self.get_model_metadata(model_id)
        if metadata:
            return metadata.get('supports_thinking', False)
        
        # Claude-specific feature
        claude_patterns = ['claude-opus-4', 'claude-sonnet-4', 'claude-3-5-sonnet']
        return any(pattern in model_id.lower() for pattern in claude_patterns)
    
    def get_max_tokens(self, model_id: str) -> int:
        """Get maximum output tokens for model."""
        capabilities = self.get_model_capabilities(model_id)
        if capabilities:
            return capabilities.get('max_output_tokens', 4096)
        
        # Reasoning models typically have higher limits
        if self.is_reasoning_model(model_id):
            return 65536
        
        return 4096  # Conservative default
    
    def get_context_window(self, model_id: str) -> int:
        """Get context window size for model."""
        capabilities = self.get_model_capabilities(model_id)
        if capabilities:
            return capabilities.get('max_context_window', 8192)
        
        # Modern models typically have larger context windows
        if any(pattern in model_id.lower() for pattern in ['gpt-4', 'claude', 'o1', 'o3']):
            return 128000
        
        return 8192  # Conservative default
    
    def get_default_parameters(self, model_id: str) -> Dict[str, Any]:
        """Get default parameters for model."""
        try:
            model = self.db.query(ModelConfiguration).filter_by(model_id=model_id).first()
            if model and model.default_params:
                return model.default_params
        except SQLAlchemyError as e:
            logger.error(f"Database error getting default params for {model_id}: {e}")
        
        # Reasoning models have different defaults
        if self.is_reasoning_model(model_id):
            return {}  # No temperature, etc.
        
        # Standard defaults
        return {
            'temperature': 0.7,
            'top_p': 1.0,
            'frequency_penalty': 0.0,
            'presence_penalty': 0.0
        }
    
    def validate_model_config(self, model_id: str, config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate configuration against model capabilities."""
        
        # Check temperature for reasoning models
        if self.is_reasoning_model(model_id):
            if config.get('temperature') is not None and config['temperature'] != 1.0:
                return False, f"Reasoning model {model_id} does not support temperature control"
        
        # Check streaming support
        if config.get('stream', False) and not self.supports_streaming(model_id):
            return False, f"Model {model_id} does not support streaming"
        
        # Check function calling support
        if config.get('tools') and not self.supports_functions(model_id):
            return False, f"Model {model_id} does not support function calling"
        
        # Check max tokens limit
        max_tokens = config.get('max_tokens')
        if max_tokens:
            model_max = self.get_max_tokens(model_id)
            if max_tokens > model_max:
                return False, f"Model {model_id} maximum tokens is {model_max}, requested {max_tokens}"
        
        return True, None
    
    def get_models_by_capability(self, capability: str, provider: Optional[str] = None) -> List[str]:
        """Get list of model IDs that support a specific capability."""
        try:
            query = self.db.query(ModelConfiguration).filter(
                ModelConfiguration.is_available == True,
                ModelConfiguration.is_deprecated == False
            )
            
            if provider:
                query = query.filter(ModelConfiguration.provider == provider)
            
            models = query.all()
            
            matching_models = []
            for model in models:
                if model.capabilities and model.capabilities.get(capability, False):
                    matching_models.append(model.model_id)
            
            return matching_models
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting models by capability {capability}: {e}")
            return []
    
    def get_cost_info(self, model_id: str) -> Optional[Dict[str, float]]:
        """Get cost information for model."""
        try:
            model = self.db.query(ModelConfiguration).filter_by(model_id=model_id).first()
            if model:
                return {
                    'input_cost_per_1k': model.cost_input_per_1k,
                    'output_cost_per_1k': model.cost_output_per_1k
                }
        except SQLAlchemyError as e:
            logger.error(f"Database error getting cost info for {model_id}: {e}")
        
        return None
    
    def clear_cache(self):
        """Clear the internal cache."""
        self._cache.clear()


# Convenience function for one-off queries
def get_model_service(db: Session) -> ModelService:
    """Get a ModelService instance."""
    return ModelService(db)