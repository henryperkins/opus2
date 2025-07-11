"""Centralized service for model capabilities and information.

This service provides a unified interface for querying model capabilities,
validation, and metadata from the ModelConfiguration database.
"""

import logging
from typing import Dict, Any, Optional, List, Set, Tuple
from datetime import datetime, timedelta

from sqlalchemy import event, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.config import ModelConfiguration
from app.schemas.generation import ModelInfo, ModelCapabilities

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# SQLAlchemy event hooks to automatically invalidate the cache when the
# *model_configurations* table changes.  The hooks are defined at import
# time so they are active as soon as the service module is loaded.  Using
# *lambda* keeps the dependency on ModelService lightweight (no circular
# imports).
# ----------------------------------------------------------------------


def _invalidate_on_change(mapper, connection, target):  # noqa: D401 – SQLA signature
    """Event handler that clears cache for the affected *model_id*."""

    try:
        ModelService.invalidate_global(getattr(target, "model_id", None))
    except Exception as exc:  # pragma: no cover – defensive
        logger.warning("Failed to invalidate ModelService cache: %s", exc)


# Register hooks – they are no-ops if the table gets manipulated outside of
# the ORM (e.g. raw SQL migrations) but cover the vast majority of runtime
# operations.

event.listen(ModelConfiguration, "after_insert", _invalidate_on_change)
event.listen(ModelConfiguration, "after_update", _invalidate_on_change)
event.listen(ModelConfiguration, "after_delete", _invalidate_on_change)


class ModelService:
    """Centralized service for model capabilities and validation."""
    
    # ------------------------------------------------------------------
    # Caching strategy ---------------------------------------------------
    # ------------------------------------------------------------------
    #
    # The service keeps a lightweight in-memory cache because model
    # capabilities are queried **very** frequently during request
    # validation.  To avoid stale information – especially after models
    # are added or updated – the entries now include a *timestamp* and are
    # subject to an expiry time (*CACHE_TTL*).  The cache is shared across
    # all *ModelService* instances so invalidation works application-wide.
    # ------------------------------------------------------------------

    # Seconds until a cache entry is considered stale.  Five minutes is a
    # reasonable balance between database traffic and freshness.
    CACHE_TTL: int = 300

    # ``{cache_key: (value, timestamp)}``
    _GLOBAL_CACHE: Dict[str, Tuple[Any, datetime]] = {}

    def __init__(self, db: Session):
        self.db = db
        # Instance view of the global cache so existing attribute access
        # continues to work without changes.
        self._cache = ModelService._GLOBAL_CACHE
    
    def get_model_capabilities(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model capabilities from database."""
        cache_key = f"capabilities_{model_id}"
        
        if cache_key in self._cache:
            value, ts = self._cache[cache_key]
            if datetime.utcnow() - ts < timedelta(seconds=self.CACHE_TTL):
                return value
            # Expired – remove so we fall through to DB lookup
            del self._cache[cache_key]
        
        try:
            stmt = select(ModelConfiguration).filter_by(model_id=model_id)
            model = self.db.execute(stmt).scalar_one_or_none()
            if model and model.capabilities:
                capabilities = model.capabilities
                # Store with timestamp
                self._cache[cache_key] = (capabilities, datetime.utcnow())
                return capabilities
        except SQLAlchemyError as e:
            logger.error(f"Database error getting capabilities for {model_id}: {e}")
        
        return None
    
    def get_model_metadata(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model metadata from database."""
        cache_key = f"metadata_{model_id}"
        
        if cache_key in self._cache:
            value, ts = self._cache[cache_key]
            if datetime.utcnow() - ts < timedelta(seconds=self.CACHE_TTL):
                return value
            del self._cache[cache_key]
        
        try:
            stmt = select(ModelConfiguration).filter_by(model_id=model_id)
            model = self.db.execute(stmt).scalar_one_or_none()
            if model and model.model_metadata:
                metadata = model.model_metadata
                self._cache[cache_key] = (metadata, datetime.utcnow())
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
        return ModelService.is_reasoning_model_static(model_id)

    # ------------------------------------------------------------------
    # Static helpers -----------------------------------------------------
    # ------------------------------------------------------------------
    #
    # The application currently needs *light-weight* helper functions that
    # can be called **early during startup** (e.g. from the Azure provider
    # initialisation) where no database session is available yet.  To avoid
    # spreading multiple hard-coded *reasoning model* sets across the code
    # base we expose *static* variants that rely **only on the pattern
    # fallback** above.  Whenever a SQLAlchemy session *is* available the
    # instance methods should be preferred because they consult the
    # database-backed capabilities column.
    # ------------------------------------------------------------------

    _REASONING_MODEL_PATTERNS: set[str] = {
        "o1",
        "o1-mini",
        "o1-preview",
        "o1-pro",
        "o3",
        "o3-mini",
        "o3-pro",
        "o4-mini",
    }

    _RESPONSES_API_MODEL_PATTERNS: set[str] = {
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4.1-nano",
        "gpt-4.5",
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

    @staticmethod
    def is_reasoning_model_static(model_id: str) -> bool:
        """Fast pattern-based check that works without DB access."""
        if not model_id:
            return False
        return model_id.lower() in ModelService._REASONING_MODEL_PATTERNS

    @staticmethod
    def requires_responses_api_static(model_id: str) -> bool:
        """Fast pattern-based check for Responses-API requirement."""
        if not model_id:
            return False
        return model_id.lower() in ModelService._RESPONSES_API_MODEL_PATTERNS
    
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
        vision_patterns = ['gpt-4o', 'gpt-4.1', 'gpt-4.5', 'claude', 'o3', 'o4']
        return any(pattern in model_id.lower() for pattern in vision_patterns)
    
    def supports_json_mode(self, model_id: str) -> bool:
        """Check if model supports JSON mode."""
        capabilities = self.get_model_capabilities(model_id)
        if capabilities:
            return capabilities.get('supports_json_mode', False)
        
        # OpenAI models typically support JSON mode
        return 'gpt' in model_id.lower()

    # ------------------------------------------------------------------
    # Cache invalidation helpers ----------------------------------------
    # ------------------------------------------------------------------

    @classmethod
    def invalidate_global(cls, model_id: Optional[str] = None):
        """Invalidate cached entries.

        If *model_id* is provided, remove only that model's cache entries.
        Otherwise clear the entire cache.
        """

        if model_id is None:
            cls._GLOBAL_CACHE.clear()
            return

        cls._GLOBAL_CACHE.pop(f"capabilities_{model_id}", None)
        cls._GLOBAL_CACHE.pop(f"metadata_{model_id}", None)
    
    def requires_responses_api(self, model_id: str) -> bool:
        """Check if model requires Azure Responses API."""
        metadata = self.get_model_metadata(model_id)
        if metadata:
            return metadata.get('requires_responses_api', False)
        
        # Fallback to pattern matching
        return ModelService.requires_responses_api_static(model_id)
    
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
        if any(pattern in model_id.lower() for pattern in ['gpt-4', 'claude', 'o1', 'o3', 'o4']):
            # GPT-4.1 series and newer have 1M+ context
            if any(pattern in model_id.lower() for pattern in ['gpt-4.1', 'gpt-4.5', 'o3', 'o4']):
                return 1000000 if 'gpt-4.1' in model_id.lower() else 200000
            return 128000
        
        return 8192  # Conservative default
    
    def get_default_parameters(self, model_id: str) -> Dict[str, Any]:
        """Get default parameters for model."""
        try:
            stmt = select(ModelConfiguration).filter_by(model_id=model_id)
            model = self.db.execute(stmt).scalar_one_or_none()
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
            stmt = select(ModelConfiguration).filter(
                ModelConfiguration.is_available == True,
                ModelConfiguration.is_deprecated == False
            )
            
            if provider:
                stmt = stmt.filter(ModelConfiguration.provider == provider)
            
            models = self.db.execute(stmt).scalars().all()
            
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
            stmt = select(ModelConfiguration).filter_by(model_id=model_id)
            model = self.db.execute(stmt).scalar_one_or_none()
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