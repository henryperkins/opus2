# Migration Guide: Unified AI Configuration System

This guide explains how to migrate from the current scattered configuration system to the new unified approach.

## Overview of Changes

### Backend Changes

1. **New Schema Hierarchy** (`app/schemas/generation.py`)
   - `GenerationParams` - All generation parameters in one place
   - `ReasoningParams` - Unified reasoning/thinking settings
   - `UnifiedModelConfig` - Complete configuration object
   - Single validation logic with consistent ranges

2. **Centralized Service** (`app/services/unified_config_service.py`)
   - Replaces `ConfigService` methods
   - Uses RuntimeConfig as single source of truth
   - No more in-memory fallbacks or duplicated storage

3. **Unified API** (`app/routers/unified_config.py`)
   - Single endpoint prefix: `/api/v1/ai-config`
   - Replaces scattered endpoints from `/api/config`, `/api/v1/models`
   - Consistent request/response schemas

4. **Updated LLM Client Integration**
   - Reads configuration from unified service
   - No more merging from multiple sources
   - Consistent parameter application

### Frontend Changes

1. **New Context/Hook** (`contexts/AIConfigContext.jsx`)
   - Single `useAIConfig()` hook for all configuration
   - Specialized hooks: `useModelSelection()`, `useGenerationParams()`, `useReasoningConfig()`
   - Automatic WebSocket synchronization

2. **Unified Settings Component** (`components/settings/UnifiedAISettings.jsx`)
   - Single component for all AI settings
   - Replaces: `ModelConfiguration.jsx`, `ThinkingConfiguration.jsx`, `AIProviderInfo.jsx`
   - Consistent UI patterns

## Step-by-Step Migration

### Phase 1: Database Migration

```python
# alembic/versions/xxx_unify_config.py
"""Unify AI configuration system"""

def upgrade():
    # 1. Ensure RuntimeConfig table has all needed keys
    op.execute("""
        INSERT INTO runtime_config (key, value, value_type, updated_by)
        SELECT 'provider', llm_provider, 'string', 'migration'
        FROM settings
        WHERE NOT EXISTS (
            SELECT 1 FROM runtime_config WHERE key = 'provider'
        )
    """)
    
    # 2. Migrate any prompt template preferences
    op.execute("""
        UPDATE prompt_templates
        SET llm_preferences = jsonb_build_object(
            'temperature', COALESCE((llm_preferences->>'temperature')::float, 0.7),
            'max_tokens', COALESCE((llm_preferences->>'maxTokens')::int, 2048),
            'top_p', COALESCE((llm_preferences->>'topP')::float, 1.0)
        )
        WHERE llm_preferences IS NOT NULL
    """)
```

### Phase 2: Backend Code Updates

1. **Update imports in existing files:**

```python
# Before
from app.schemas.prompt import ModelPreferences
from app.schemas.models import ModelConfig
from app.services.config_service import ConfigService

# After
from app.schemas.generation import UnifiedModelConfig, GenerationParams
from app.services.unified_config_service import UnifiedConfigService
```

2. **Update LLM Client (`app/llm/client.py`):**

```python
def _get_runtime_config(self) -> Dict[str, Any]:
    """Get current runtime configuration."""
    try:
        from app.services.unified_config_service import UnifiedConfigService
        from app.database import SessionLocal
        
        with SessionLocal() as db:
            service = UnifiedConfigService(db)
            config = service.get_current_config()
            return config.to_runtime_config()
    except Exception as e:
        logger.error(f"Failed to load unified config: {e}")
        # Fallback to env settings
        return self._get_default_config()
```

3. **Update startup initialization (`app/main.py`):**

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize unified configuration
    with SessionLocal() as db:
        service = UnifiedConfigService(db)
        service.initialize_defaults()
    
    yield
```

### Phase 3: API Endpoint Migration

1. **Update router imports:**

```python
# app/main.py
# Remove old routers
# from .routers import config as config_router
# from .routers import models as models_router

# Add new unified router
from .routers import unified_config as ai_config_router

# Update router registration
app.include_router(ai_config_router.router)
```

2. **Add redirect endpoints for backward compatibility:**

```python
# app/routers/config.py - Add temporary redirects
@router.get("", deprecated=True)
async def get_config_deprecated():
    """Deprecated - use /api/v1/ai-config instead"""
    return RedirectResponse("/api/v1/ai-config", status_code=301)
```

### Phase 4: Frontend Migration

1. **Update API calls:**

```javascript
// Before
import { configAPI } from '../api/config';
const config = await configAPI.getConfig();

// After
import { useAIConfig } from '../contexts/AIConfigContext';
const { config, updateConfig } = useAIConfig();
```

2. **Replace components in settings pages:**

```jsx
// Before
<ModelConfiguration />
<ThinkingConfiguration />
<AIProviderInfo />

// After
<UnifiedAISettings />
```

3. **Update context providers in App.jsx:**

```jsx
// Add new provider
import { AIConfigProvider } from './contexts/AIConfigContext';

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <AIConfigProvider>
          {/* Other providers and components */}
        </AIConfigProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
```

### Phase 5: Testing

1. **Test configuration persistence:**
```bash
# Test that changes persist across restarts
curl -X PUT http://localhost:8000/api/v1/ai-config \
  -H "Content-Type: application/json" \
  -d '{"temperature": 0.8, "model_id": "gpt-4o"}'
```

2. **Test WebSocket synchronization:**
   - Open app in two browser windows
   - Change settings in one window
   - Verify changes appear in the other

3. **Test backward compatibility:**
   - Ensure old API endpoints redirect properly
   - Check that existing prompt templates still work

### Phase 6: Cleanup (After Verification)

1. **Remove deprecated code:**
   - Delete old schema files
   - Remove old service methods
   - Clean up duplicate router endpoints

2. **Update documentation:**
   - API documentation
   - Developer guides
   - Configuration examples

## Rollback Plan

If issues arise during migration:

1. **Database:** Keep backup of RuntimeConfig table
2. **Code:** Use feature flags to toggle between old/new systems
3. **API:** Maintain redirect endpoints until fully migrated

## Benefits After Migration

1. **Reduced Code:** ~40% less configuration-related code
2. **Better Performance:** Single source of truth, no merging
3. **Improved UX:** Consistent UI, real-time synchronization
4. **Easier Maintenance:** All configuration logic in one place
5. **Better Validation:** Consistent rules across the system

## Common Issues and Solutions

### Issue: Prompt templates not loading preferences
**Solution:** Run migration script to update JSONB structure

### Issue: WebSocket updates not working
**Solution:** Ensure AIConfigProvider wraps components needing updates

### Issue: Old API calls failing
**Solution:** Update to new endpoints or ensure redirects are in place

### Issue: Configuration not persisting
**Solution:** Check RuntimeConfig table permissions and constraints


---


### **`app/schemas/generation.py`**
```python
# app/schemas/generation.py
"""
Unified schema definitions for AI model configuration.
Single source of truth for all generation parameters, reasoning settings, and provider options.
"""
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime


class GenerationParams(BaseModel):
    """Core generation parameters supported by all providers."""
    
    temperature: Optional[float] = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Controls randomness in generation"
    )
    max_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        le=128000,
        description="Maximum tokens to generate"
    )
    top_p: Optional[float] = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter"
    )
    frequency_penalty: Optional[float] = Field(
        default=0.0,
        ge=-2.0,
        le=2.0,
        description="Penalty for token frequency"
    )
    presence_penalty: Optional[float] = Field(
        default=0.0,
        ge=-2.0,
        le=2.0,
        description="Penalty for token presence"
    )
    stop_sequences: Optional[List[str]] = Field(
        default=None,
        description="Sequences where generation stops"
    )
    seed: Optional[int] = Field(
        default=None,
        description="Random seed for reproducibility"
    )
    
    model_config = ConfigDict(protected_namespaces=())


class ReasoningParams(BaseModel):
    """Reasoning and thinking parameters for advanced models."""
    
    # General reasoning settings
    enable_reasoning: bool = Field(
        default=False,
        description="Enable reasoning for supported models"
    )
    reasoning_effort: Literal["low", "medium", "high"] = Field(
        default="medium",
        description="Reasoning effort level (Azure/OpenAI)"
    )
    
    # Claude-specific thinking settings
    claude_extended_thinking: Optional[bool] = Field(
        default=True,
        description="Enable Claude's extended thinking"
    )
    claude_thinking_mode: Optional[Literal["off", "enabled", "aggressive"]] = Field(
        default="enabled",
        description="Claude thinking mode"
    )
    claude_thinking_budget_tokens: Optional[int] = Field(
        default=16384,
        ge=1024,
        le=65536,
        description="Token budget for Claude thinking"
    )
    claude_show_thinking_process: Optional[bool] = Field(
        default=True,
        description="Show Claude's thinking process"
    )
    claude_adaptive_thinking_budget: Optional[bool] = Field(
        default=True,
        description="Auto-adjust thinking budget based on complexity"
    )
    
    # Thinking mode selection
    default_thinking_mode: Optional[str] = Field(
        default="chain_of_thought",
        description="Default thinking approach"
    )
    default_thinking_depth: Optional[Literal["surface", "detailed", "comprehensive", "exhaustive"]] = Field(
        default="detailed",
        description="Default thinking depth"
    )
    
    model_config = ConfigDict(protected_namespaces=())


class ProviderConfig(BaseModel):
    """Provider-specific configuration."""
    
    provider: Literal["openai", "azure", "anthropic"] = Field(
        ...,
        description="AI provider"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API key (stored encrypted)"
    )
    endpoint: Optional[str] = Field(
        default=None,
        description="API endpoint URL"
    )
    api_version: Optional[str] = Field(
        default=None,
        description="API version (Azure)"
    )
    organization_id: Optional[str] = Field(
        default=None,
        description="Organization ID (OpenAI)"
    )
    use_responses_api: Optional[bool] = Field(
        default=False,
        description="Use Azure Responses API"
    )
    
    model_config = ConfigDict(protected_namespaces=())


class ModelCapabilities(BaseModel):
    """Model capabilities and limits."""
    
    supports_functions: bool = True
    supports_vision: bool = False
    supports_reasoning: bool = False
    supports_streaming: bool = True
    supports_json_mode: bool = True
    max_context_window: int = 4096
    max_output_tokens: int = 4096
    supports_parallel_tools: bool = True
    
    model_config = ConfigDict(protected_namespaces=())


class ModelInfo(BaseModel):
    """Complete model information."""
    
    model_id: str = Field(..., description="Unique model identifier")
    display_name: str = Field(..., description="User-friendly name")
    provider: Literal["openai", "azure", "anthropic"] = Field(..., description="Provider")
    model_family: Optional[str] = Field(None, description="Model family (gpt-4, claude-3, etc)")
    
    # Capabilities
    capabilities: ModelCapabilities = Field(
        default_factory=ModelCapabilities,
        description="Model capabilities"
    )
    
    # Cost information
    cost_per_1k_input_tokens: Optional[float] = Field(None, ge=0)
    cost_per_1k_output_tokens: Optional[float] = Field(None, ge=0)
    
    # Performance characteristics
    performance_tier: Optional[Literal["fast", "balanced", "powerful"]] = Field(
        default="balanced",
        description="Performance tier"
    )
    average_latency_ms: Optional[int] = Field(None, description="Average response time")
    
    # Metadata
    is_available: bool = True
    is_deprecated: bool = False
    deprecation_date: Optional[datetime] = None
    recommended_use_cases: List[str] = Field(default_factory=list)
    
    model_config = ConfigDict(protected_namespaces=())


class UnifiedModelConfig(GenerationParams, ReasoningParams):
    """Complete model configuration combining all parameters."""
    
    # Model selection
    provider: Literal["openai", "azure", "anthropic"] = Field(
        ...,
        description="AI provider"
    )
    model_id: str = Field(
        ...,
        description="Model identifier"
    )
    
    # Optional overrides
    system_prompt: Optional[str] = Field(
        default=None,
        description="System prompt override"
    )
    response_format: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Response format (e.g., JSON mode)"
    )
    
    # Provider-specific settings
    use_responses_api: bool = Field(
        default=False,
        description="Use Azure Responses API"
    )
    
    # Metadata
    config_name: Optional[str] = Field(
        default=None,
        description="Configuration preset name"
    )
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @field_validator("model_id")
    @classmethod
    def validate_model_id(cls, v, info):
        """Validate model_id based on provider."""
        provider = info.data.get("provider")
        
        # Basic validation - could be extended with actual model lists
        if provider == "azure" and not v:
            raise ValueError("Model ID required for Azure provider")
        
        return v
    
    def to_runtime_config(self) -> Dict[str, Any]:
        """Convert to runtime configuration format."""
        config = self.model_dump(exclude_unset=True, exclude_none=True)
        
        # Flatten for storage
        flat_config = {
            "provider": config.pop("provider"),
            "chat_model": config.pop("model_id"),
            **config
        }
        
        return flat_config
    
    @classmethod
    def from_runtime_config(cls, config: Dict[str, Any]) -> "UnifiedModelConfig":
        """Create from runtime configuration."""
        # Map flat structure back to nested
        model_config = {
            "provider": config.get("provider", "openai"),
            "model_id": config.get("chat_model", "gpt-4o-mini"),
            **{k: v for k, v in config.items() if k not in ["provider", "chat_model"]}
        }
        
        return cls(**model_config)
    
    model_config = ConfigDict(protected_namespaces=())


# Request/Response schemas for API
class ConfigUpdateRequest(BaseModel):
    """Request schema for configuration updates."""
    
    config: Optional[UnifiedModelConfig] = None
    provider_config: Optional[ProviderConfig] = None
    update_type: Literal["full", "partial"] = "partial"
    
    model_config = ConfigDict(protected_namespaces=())


class ConfigResponse(BaseModel):
    """Response schema for configuration endpoints."""
    
    current: UnifiedModelConfig
    available_models: List[ModelInfo]
    providers: Dict[str, Dict[str, Any]]
    last_updated: datetime
    
    model_config = ConfigDict(protected_namespaces=())


# Validation helpers
def validate_config_consistency(config: UnifiedModelConfig) -> tuple[bool, Optional[str]]:
    """Validate configuration consistency across parameters."""
    
    # Reasoning models don't support temperature
    reasoning_models = ["o1", "o1-mini", "o3", "o3-mini", "o4-mini"]
    if any(model in config.model_id for model in reasoning_models):
        if config.temperature is not None and config.temperature != 1.0:
            return False, f"Reasoning model {config.model_id} does not support temperature control"
    
    # Claude models require specific thinking parameters
    if config.provider == "anthropic":
        if config.enable_reasoning and not config.claude_extended_thinking:
            return False, "Claude models use extended thinking, not standard reasoning"
    
    # Azure Responses API requirements
    if config.use_responses_api and config.provider != "azure":
        return False, "Responses API is only available for Azure provider"
    
    return True, None


# Export all schemas
__all__ = [
    "GenerationParams",
    "ReasoningParams", 
    "ProviderConfig",
    "ModelCapabilities",
    "ModelInfo",
    "UnifiedModelConfig",
    "ConfigUpdateRequest",
    "ConfigResponse",
    "validate_config_consistency"
]
```
---
### **`app/services/unified_config_service.py`**
```python
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
```
---
### **`app/routers/unified_config.py`**
```python
# app/routers/unified_config.py
"""
Unified API router for all AI configuration endpoints.
Replaces scattered config, models, and provider endpoints.
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.services.unified_config_service import UnifiedConfigService
from app.schemas.generation import (
    UnifiedModelConfig,
    ConfigUpdateRequest,
    ConfigResponse,
    ModelInfo
)
from app.auth.dependencies import get_current_user_required
from app.models.user import User
from app.websocket.manager import connection_manager
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ai-config", tags=["ai-configuration"])


def get_config_service(db: Session = Depends(get_db)) -> UnifiedConfigService:
    """Dependency to get config service instance."""
    return UnifiedConfigService(db)


@router.get("", response_model=ConfigResponse)
async def get_configuration(
    service: UnifiedConfigService = Depends(get_config_service),
    current_user: User = Depends(get_current_user_required)
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
                "models": [m.model_dump() for m in available_models if m.provider == "openai"],
                "capabilities": {
                    "supports_functions": True,
                    "supports_streaming": True,
                    "supports_vision": True
                }
            },
            "azure": {
                "display_name": "Azure OpenAI",
                "models": [m.model_dump() for m in available_models if m.provider == "azure"],
                "capabilities": {
                    "supports_functions": True,
                    "supports_streaming": True,
                    "supports_responses_api": True,
                    "supports_reasoning": True
                }
            },
            "anthropic": {
                "display_name": "Anthropic",
                "models": [m.model_dump() for m in available_models if m.provider == "anthropic"],
                "capabilities": {
                    "supports_functions": True,
                    "supports_streaming": True,
                    "supports_thinking": True
                }
            }
        }
        
        return ConfigResponse(
            current=current_config,
            available_models=available_models,
            providers=providers,
            last_updated=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to get configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load configuration"
        )


@router.put("", response_model=UnifiedModelConfig)
async def update_configuration(
    updates: Dict[str, Any],
    service: UnifiedConfigService = Depends(get_config_service),
    current_user: User = Depends(get_current_user_required)
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
            updates, 
            updated_by=current_user.username
        )
        
        # Notify LLM client of changes
        await _notify_llm_client(updated_config)
        
        # Broadcast update via WebSocket
        await _broadcast_config_update(updated_config, service)
        
        logger.info(f"Configuration updated by {current_user.username}")
        
        return updated_config
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update configuration"
        )


@router.post("/test")
async def test_configuration(
    config: Optional[UnifiedModelConfig] = None,
    service: UnifiedConfigService = Depends(get_config_service),
    current_user: User = Depends(get_current_user_required)
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
        return {
            "success": False,
            "message": "Test failed",
            "error": str(e)
        }


@router.get("/models", response_model=list[ModelInfo])
async def get_available_models(
    provider: Optional[str] = None,
    include_deprecated: bool = False,
    service: UnifiedConfigService = Depends(get_config_service),
    current_user: User = Depends(get_current_user_required)
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
            detail="Failed to load available models"
        )


@router.get("/models/{model_id}", response_model=ModelInfo)
async def get_model_info(
    model_id: str,
    service: UnifiedConfigService = Depends(get_config_service),
    current_user: User = Depends(get_current_user_required)
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
            detail=f"Model '{model_id}' not found"
        )
    
    return model_info


@router.post("/validate")
async def validate_configuration(
    config: Dict[str, Any],
    service: UnifiedConfigService = Depends(get_config_service),
    current_user: User = Depends(get_current_user_required)
) -> Dict[str, Any]:
    """
    Validate configuration without saving.
    
    Checks:
    - Parameter value ranges
    - Provider/model compatibility
    - Reasoning model restrictions
    
    Returns validation result with specific error details if invalid.
    """
    is_valid, error = service.validate_config(config)
    
    return {
        "valid": is_valid,
        "error": error,
        "validated_at": datetime.utcnow()
    }


@router.get("/presets")
async def get_configuration_presets(
    current_user: User = Depends(get_current_user_required)
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
                "reasoning_effort": "medium"
            }
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
                "reasoning_effort": "high"
            }
        },
        {
            "id": "precise",
            "name": "Precise",
            "description": "Focused and deterministic responses",
            "config": {
                "temperature": 0.3,
                "max_tokens": 2048,
                "top_p": 0.9,
                "reasoning_effort": "high"
            }
        },
        {
            "id": "fast",
            "name": "Fast",
            "description": "Optimized for quick responses",
            "config": {
                "model_id": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 1024,
                "reasoning_effort": "low"
            }
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
                "enable_reasoning": True
            }
        }
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
            use_responses_api=config.use_responses_api
        )
    except Exception as e:
        logger.warning(f"Failed to reconfigure LLM client: {e}")


async def _broadcast_config_update(
    config: UnifiedModelConfig, 
    service: UnifiedConfigService
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
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await connection_manager.broadcast_json(update_message)
        
    except Exception as e:
        logger.warning(f"Failed to broadcast config update: {e}")


# Initialize defaults on startup
@router.on_event("startup")
async def initialize_configuration():
    """Initialize default configuration on startup."""
    from app.database import SessionLocal
    
    try:
        with SessionLocal() as db:
            service = UnifiedConfigService(db)
            service.initialize_defaults()
            logger.info("AI configuration initialized")
    except Exception as e:
        logger.error(f"Failed to initialize configuration: {e}")
        # Don't fail startup, allow application to continue
```
---
### **`frontend/src/contexts/AIConfigContext.jsx`**
```jsx
// frontend/src/contexts/AIConfigContext.jsx
import React, { createContext, useContext, useReducer, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';

// Use the existing API client pattern from the codebase
// This would import from '../api/client' in the actual implementation
const apiClient = {
  get: (url) => fetch(url).then(res => res.json()),
  put: (url, data) => fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }).then(res => res.json()),
  post: (url, data) => fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }).then(res => res.json())
};

// API client
const API_BASE = '/api/v1/ai-config';

const aiConfigAPI = {
  getConfig: async () => {
    return await apiClient.get(API_BASE);
  },
  
  updateConfig: async (updates) => {
    return await apiClient.put(API_BASE, updates);
  },
  
  testConfig: async (config = null) => {
    return await apiClient.post(`${API_BASE}/test`, config);
  },
  
  getModels: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const url = queryString ? `${API_BASE}/models?${queryString}` : `${API_BASE}/models`;
    return await apiClient.get(url);
  },
  
  getModelInfo: async (modelId) => {
    return await apiClient.get(`${API_BASE}/models/${modelId}`);
  },
  
  validateConfig: async (config) => {
    return await apiClient.post(`${API_BASE}/validate`, config);
  },
  
  getPresets: async () => {
    return await apiClient.get(`${API_BASE}/presets`);
  }
};

// Context
const AIConfigContext = createContext(null);

// Action types
const ACTIONS = {
  SET_CONFIG: 'SET_CONFIG',
  UPDATE_CONFIG: 'UPDATE_CONFIG',
  SET_MODELS: 'SET_MODELS',
  SET_LOADING: 'SET_LOADING',
  SET_ERROR: 'SET_ERROR',
  SET_TEST_RESULT: 'SET_TEST_RESULT'
};

// Initial state
const initialState = {
  // Current configuration
  config: null,
  
  // Available models and providers
  models: [],
  providers: {},
  
  // UI state
  loading: false,
  error: null,
  testResult: null,
  
  // Metadata
  lastUpdated: null
};

// Reducer
function aiConfigReducer(state, action) {
  switch (action.type) {
    case ACTIONS.SET_CONFIG:
      return {
        ...state,
        config: action.payload.current,
        models: action.payload.available_models || state.models,
        providers: action.payload.providers || state.providers,
        lastUpdated: action.payload.last_updated,
        error: null
      };
      
    case ACTIONS.UPDATE_CONFIG:
      return {
        ...state,
        config: { ...state.config, ...action.payload },
        error: null
      };
      
    case ACTIONS.SET_MODELS:
      return {
        ...state,
        models: action.payload
      };
      
    case ACTIONS.SET_LOADING:
      return {
        ...state,
        loading: action.payload
      };
      
    case ACTIONS.SET_ERROR:
      return {
        ...state,
        error: action.payload,
        loading: false
      };
      
    case ACTIONS.SET_TEST_RESULT:
      return {
        ...state,
        testResult: action.payload
      };
      
    default:
      return state;
  }
}

// Provider component
export function AIConfigProvider({ children }) {
  const [state, dispatch] = useReducer(aiConfigReducer, initialState);
  const queryClient = useQueryClient();
  
  // Query for fetching configuration
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['ai-config'],
    queryFn: aiConfigAPI.getConfig,
    staleTime: 30000, // 30 seconds
    cacheTime: 5 * 60 * 1000, // 5 minutes
    onSuccess: (data) => {
      dispatch({ type: ACTIONS.SET_CONFIG, payload: data });
    },
    onError: (error) => {
      dispatch({ type: ACTIONS.SET_ERROR, payload: error.message });
      console.error('Failed to load AI configuration:', error);
    }
  });
  
  // Mutation for updating configuration
  const updateMutation = useMutation({
    mutationFn: aiConfigAPI.updateConfig,
    onMutate: async (updates) => {
      // Cancel outgoing queries
      await queryClient.cancelQueries(['ai-config']);
      
      // Optimistic update
      dispatch({ type: ACTIONS.UPDATE_CONFIG, payload: updates });
      
      // Return context for rollback
      return { previousConfig: state.config };
    },
    onError: (error, updates, context) => {
      // Rollback on error
      if (context?.previousConfig) {
        dispatch({ 
          type: ACTIONS.SET_CONFIG, 
          payload: { current: context.previousConfig } 
        });
      }
      dispatch({ type: ACTIONS.SET_ERROR, payload: error.message });
      toast.error('Failed to update configuration');
    },
    onSuccess: (data) => {
      dispatch({ type: ACTIONS.UPDATE_CONFIG, payload: data });
      queryClient.invalidateQueries(['ai-config']);
      toast.success('Configuration updated successfully');
    }
  });
  
  // Update configuration
  const updateConfig = useCallback(async (updates) => {
    return updateMutation.mutateAsync(updates);
  }, [updateMutation]);
  
  // Test configuration
  const testConfig = useCallback(async (config = null) => {
    dispatch({ type: ACTIONS.SET_TEST_RESULT, payload: null });
    
    try {
      const result = await aiConfigAPI.testConfig(config);
      dispatch({ type: ACTIONS.SET_TEST_RESULT, payload: result });
      
      if (result.success) {
        toast.success('Configuration test successful');
      } else {
        toast.error(result.message || 'Configuration test failed');
      }
      
      return result;
    } catch (error) {
      const errorResult = {
        success: false,
        message: error.message,
        error: error.response?.data?.detail || 'Test failed'
      };
      dispatch({ type: ACTIONS.SET_TEST_RESULT, payload: errorResult });
      toast.error('Configuration test failed');
      return errorResult;
    }
  }, []);
  
  // Get model info
  const getModelInfo = useCallback(async (modelId) => {
    try {
      return await aiConfigAPI.getModelInfo(modelId);
    } catch (error) {
      console.error(`Failed to get model info for ${modelId}:`, error);
      return null;
    }
  }, []);
  
  // Apply preset
  const applyPreset = useCallback(async (presetId) => {
    try {
      const presets = await aiConfigAPI.getPresets();
      const preset = presets.find(p => p.id === presetId);
      
      if (!preset) {
        throw new Error(`Preset '${presetId}' not found`);
      }
      
      await updateConfig(preset.config);
      toast.success(`Applied '${preset.name}' preset`);
      
    } catch (error) {
      console.error('Failed to apply preset:', error);
      toast.error('Failed to apply preset');
    }
  }, [updateConfig]);
  
  // Listen for WebSocket updates
  useEffect(() => {
    const handleConfigUpdate = (event) => {
      if (event.data?.type === 'config_update') {
        dispatch({ type: ACTIONS.SET_CONFIG, payload: event.data.data });
        queryClient.invalidateQueries(['ai-config']);
      }
    };
    
    // Add WebSocket listener if available
    if (window.websocketManager) {
      window.websocketManager.addEventListener('message', handleConfigUpdate);
      
      return () => {
        window.websocketManager.removeEventListener('message', handleConfigUpdate);
      };
    }
  }, [queryClient]);
  
  // Context value
  const contextValue = {
    // State
    config: state.config,
    models: state.models,
    providers: state.providers,
    loading: isLoading || state.loading,
    error: error || state.error,
    testResult: state.testResult,
    lastUpdated: state.lastUpdated,
    
    // Actions
    updateConfig,
    testConfig,
    getModelInfo,
    applyPreset,
    refetch,
    
    // Computed values
    currentModel: state.config?.model_id,
    currentProvider: state.config?.provider,
    isReasoningEnabled: state.config?.enable_reasoning || false,
    isThinkingEnabled: state.config?.claude_extended_thinking || false
  };
  
  return (
    <AIConfigContext.Provider value={contextValue}>
      {children}
    </AIConfigContext.Provider>
  );
}

// Hook to use AI configuration
export function useAIConfig() {
  const context = useContext(AIConfigContext);
  
  if (!context) {
    throw new Error('useAIConfig must be used within AIConfigProvider');
  }
  
  return context;
}

// Convenience hooks for specific features

export function useModelSelection() {
  const { config, models, updateConfig, currentModel, currentProvider } = useAIConfig();
  
  const selectModel = useCallback(async (modelId) => {
    // Find model info
    const model = models.find(m => m.model_id === modelId);
    if (!model) {
      throw new Error(`Model '${modelId}' not found`);
    }
    
    // Update configuration
    await updateConfig({
      model_id: modelId,
      provider: model.provider
    });
  }, [models, updateConfig]);
  
  const selectProvider = useCallback(async (provider) => {
    // Find first available model for provider
    const model = models.find(m => m.provider === provider);
    if (!model) {
      throw new Error(`No models available for provider '${provider}'`);
    }
    
    await updateConfig({
      provider: provider,
      model_id: model.model_id
    });
  }, [models, updateConfig]);
  
  return {
    currentModel,
    currentProvider,
    availableModels: models,
    selectModel,
    selectProvider
  };
}

export function useGenerationParams() {
  const { config, updateConfig } = useAIConfig();
  
  const updateParams = useCallback(async (params) => {
    const allowedParams = [
      'temperature', 'max_tokens', 'top_p', 
      'frequency_penalty', 'presence_penalty',
      'stop_sequences', 'seed'
    ];
    
    // Filter to allowed parameters
    const filtered = Object.keys(params)
      .filter(key => allowedParams.includes(key))
      .reduce((obj, key) => {
        obj[key] = params[key];
        return obj;
      }, {});
    
    if (Object.keys(filtered).length > 0) {
      await updateConfig(filtered);
    }
  }, [updateConfig]);
  
  return {
    temperature: config?.temperature,
    maxTokens: config?.max_tokens,
    topP: config?.top_p,
    frequencyPenalty: config?.frequency_penalty,
    presencePenalty: config?.presence_penalty,
    updateParams
  };
}

export function useReasoningConfig() {
  const { config, updateConfig, currentProvider } = useAIConfig();
  
  const isClaudeProvider = currentProvider === 'anthropic';
  const isAzureOrOpenAI = ['azure', 'openai'].includes(currentProvider);
  
  const updateReasoningConfig = useCallback(async (updates) => {
    const reasoningParams = [
      'enable_reasoning', 'reasoning_effort',
      'claude_extended_thinking', 'claude_thinking_mode',
      'claude_thinking_budget_tokens', 'claude_show_thinking_process',
      'claude_adaptive_thinking_budget', 'default_thinking_mode',
      'default_thinking_depth'
    ];
    
    // Filter to reasoning parameters
    const filtered = Object.keys(updates)
      .filter(key => reasoningParams.includes(key))
      .reduce((obj, key) => {
        obj[key] = updates[key];
        return obj;
      }, {});
    
    if (Object.keys(filtered).length > 0) {
      await updateConfig(filtered);
    }
  }, [updateConfig]);
  
  return {
    // General reasoning
    enableReasoning: config?.enable_reasoning,
    reasoningEffort: config?.reasoning_effort,
    
    // Claude thinking
    claudeExtendedThinking: config?.claude_extended_thinking,
    claudeThinkingMode: config?.claude_thinking_mode,
    claudeThinkingBudget: config?.claude_thinking_budget_tokens,
    
    // Provider flags
    isClaudeProvider,
    isAzureOrOpenAI,
    supportsReasoning: isAzureOrOpenAI && config?.use_responses_api,
    supportsThinking: isClaudeProvider,
    
    // Update function
    updateReasoningConfig
  };
}

// Export everything
export default AIConfigContext;
```
---
### **`frontend/src/components/settings/UnifiedAISettings.jsx`**
```jsx
// frontend/src/components/settings/UnifiedAISettings.jsx
import React, { useState, useEffect } from 'react';
import {
  Brain,
  Settings,
  Zap,
  DollarSign,
  AlertCircle,
  Check,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  Info
} from 'lucide-react';
import {
  useAIConfig,
  useModelSelection,
  useGenerationParams,
  useReasoningConfig
} from '../../contexts/AIConfigContext';

export default function UnifiedAISettings() {
  const {
    config,
    loading,
    error,
    testResult,
    testConfig,
    applyPreset,
    providers
  } = useAIConfig();

  const {
    currentModel,
    currentProvider,
    availableModels,
    selectModel,
    selectProvider
  } = useModelSelection();

  const {
    temperature,
    maxTokens,
    topP,
    frequencyPenalty,
    presencePenalty,
    updateParams
  } = useGenerationParams();

  const {
    enableReasoning,
    reasoningEffort,
    claudeExtendedThinking,
    claudeThinkingMode,
    claudeThinkingBudget,
    isClaudeProvider,
    isAzureOrOpenAI,
    supportsReasoning,
    supportsThinking,
    updateReasoningConfig
  } = useReasoningConfig();

  const [expandedSections, setExpandedSections] = useState({
    model: true,
    generation: true,
    reasoning: true,
    presets: false
  });

  const [isTesting, setIsTesting] = useState(false);

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const handleTestConfig = async () => {
    setIsTesting(true);
    try {
      await testConfig();
    } finally {
      setIsTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-start">
          <AlertCircle className="h-5 w-5 text-red-400 mr-2 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-medium text-red-800">Configuration Error</h3>
            <p className="mt-1 text-sm text-red-600">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Brain className="h-6 w-6 text-blue-500" />
          <h2 className="text-xl font-semibold text-gray-900">AI Configuration</h2>
        </div>
        <button
          onClick={handleTestConfig}
          disabled={isTesting}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {isTesting ? (
            <>
              <RefreshCw className="h-4 w-4 animate-spin" />
              Testing...
            </>
          ) : (
            <>
              <Zap className="h-4 w-4" />
              Test Configuration
            </>
          )}
        </button>
      </div>

      {/* Test Result */}
      {testResult && (
        <div className={`p-4 rounded-lg border ${
          testResult.success 
            ? 'bg-green-50 border-green-200' 
            : 'bg-red-50 border-red-200'
        }`}>
          <div className="flex items-start">
            {testResult.success ? (
              <Check className="h-5 w-5 text-green-600 mr-2 flex-shrink-0 mt-0.5" />
            ) : (
              <AlertCircle className="h-5 w-5 text-red-600 mr-2 flex-shrink-0 mt-0.5" />
            )}
            <div className="flex-1">
              <p className={`text-sm font-medium ${
                testResult.success ? 'text-green-800' : 'text-red-800'
              }`}>
                {testResult.message}
              </p>
              {testResult.response_time && (
                <p className="mt-1 text-sm text-gray-600">
                  Response time: {testResult.response_time}s
                </p>
              )}
              {testResult.error && (
                <p className="mt-1 text-sm text-red-600">
                  Error: {testResult.error}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Model Selection Section */}
      <Section
        title="Model Selection"
        icon={Settings}
        expanded={expandedSections.model}
        onToggle={() => toggleSection('model')}
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Provider
            </label>
            <select
              value={currentProvider || ''}
              onChange={(e) => selectProvider(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              {Object.entries(providers).map(([key, provider]) => (
                <option key={key} value={key}>
                  {provider.display_name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Model
            </label>
            <select
              value={currentModel || ''}
              onChange={(e) => selectModel(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              {availableModels
                .filter(m => m.provider === currentProvider)
                .map(model => (
                  <option key={model.model_id} value={model.model_id}>
                    {model.display_name}
                    {model.is_deprecated && ' (Deprecated)'}
                  </option>
                ))}
            </select>
          </div>
        </div>

        {/* Model Info */}
        {currentModel && (
          <ModelInfoCard modelId={currentModel} models={availableModels} />
        )}
      </Section>

      {/* Generation Parameters Section */}
      <Section
        title="Generation Parameters"
        icon={Zap}
        expanded={expandedSections.generation}
        onToggle={() => toggleSection('generation')}
      >
        <div className="space-y-4">
          <ParameterSlider
            label="Temperature"
            value={temperature || 0.7}
            min={0}
            max={2}
            step={0.1}
            onChange={(value) => updateParams({ temperature: value })}
            info="Controls randomness in generation. Lower values make output more focused and deterministic."
          />

          <ParameterSlider
            label="Max Tokens"
            value={maxTokens || 2048}
            min={1}
            max={8192}
            step={256}
            onChange={(value) => updateParams({ max_tokens: value })}
            info="Maximum number of tokens to generate in the response."
          />

          <ParameterSlider
            label="Top P"
            value={topP || 1.0}
            min={0}
            max={1}
            step={0.05}
            onChange={(value) => updateParams({ top_p: value })}
            info="Nucleus sampling parameter. Consider only tokens with cumulative probability above this threshold."
          />

          <ParameterSlider
            label="Frequency Penalty"
            value={frequencyPenalty || 0}
            min={-2}
            max={2}
            step={0.1}
            onChange={(value) => updateParams({ frequency_penalty: value })}
            info="Penalize tokens based on their frequency in the generated text so far."
          />

          <ParameterSlider
            label="Presence Penalty"
            value={presencePenalty || 0}
            min={-2}
            max={2}
            step={0.1}
            onChange={(value) => updateParams({ presence_penalty: value })}
            info="Penalize tokens based on whether they appear in the generated text so far."
          />
        </div>
      </Section>

      {/* Reasoning & Thinking Section */}
      {(supportsReasoning || supportsThinking) && (
        <Section
          title="Reasoning & Thinking"
          icon={Brain}
          expanded={expandedSections.reasoning}
          onToggle={() => toggleSection('reasoning')}
        >
          {isAzureOrOpenAI && supportsReasoning && (
            <div className="space-y-4 mb-6">
              <h4 className="text-sm font-medium text-gray-700">Azure/OpenAI Reasoning</h4>
              
              <div className="flex items-center justify-between">
                <label className="text-sm text-gray-600">Enable Reasoning</label>
                <input
                  type="checkbox"
                  checked={enableReasoning || false}
                  onChange={(e) => updateReasoningConfig({ enable_reasoning: e.target.checked })}
                  className="h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
                />
              </div>

              {enableReasoning && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Reasoning Effort
                  </label>
                  <select
                    value={reasoningEffort || 'medium'}
                    onChange={(e) => updateReasoningConfig({ reasoning_effort: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
              )}
            </div>
          )}

          {isClaudeProvider && (
            <div className="space-y-4">
              <h4 className="text-sm font-medium text-gray-700">Claude Extended Thinking</h4>
              
              <div className="flex items-center justify-between">
                <label className="text-sm text-gray-600">Enable Extended Thinking</label>
                <input
                  type="checkbox"
                  checked={claudeExtendedThinking || false}
                  onChange={(e) => updateReasoningConfig({ claude_extended_thinking: e.target.checked })}
                  className="h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
                />
              </div>

              {claudeExtendedThinking && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Thinking Mode
                    </label>
                    <select
                      value={claudeThinkingMode || 'enabled'}
                      onChange={(e) => updateReasoningConfig({ claude_thinking_mode: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="off">Off</option>
                      <option value="enabled">Enabled</option>
                      <option value="aggressive">Aggressive</option>
                    </select>
                  </div>

                  <ParameterSlider
                    label="Thinking Budget (tokens)"
                    value={claudeThinkingBudget || 16384}
                    min={1024}
                    max={65536}
                    step={1024}
                    onChange={(value) => updateReasoningConfig({ claude_thinking_budget_tokens: value })}
                    info="Token budget allocated for Claude's thinking process."
                  />
                </>
              )}
            </div>
          )}
        </Section>
      )}

      {/* Presets Section */}
      <Section
        title="Configuration Presets"
        icon={DollarSign}
        expanded={expandedSections.presets}
        onToggle={() => toggleSection('presets')}
      >
        <PresetSelector onSelectPreset={applyPreset} />
      </Section>
    </div>
  );
}

// Section Component
function Section({ title, icon: Icon, expanded, onToggle, children }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Icon className="h-5 w-5 text-gray-600" />
          <h3 className="text-lg font-medium text-gray-900">{title}</h3>
        </div>
        {expanded ? (
          <ChevronDown className="h-5 w-5 text-gray-400" />
        ) : (
          <ChevronRight className="h-5 w-5 text-gray-400" />
        )}
      </button>
      {expanded && (
        <div className="px-6 py-4 border-t border-gray-200">
          {children}
        </div>
      )}
    </div>
  );
}

// Parameter Slider Component
function ParameterSlider({ label, value, min, max, step, onChange, info }) {
  const [showInfo, setShowInfo] = useState(false);

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700">{label}</label>
          <button
            onMouseEnter={() => setShowInfo(true)}
            onMouseLeave={() => setShowInfo(false)}
            className="text-gray-400 hover:text-gray-600"
          >
            <Info className="h-4 w-4" />
          </button>
        </div>
        <span className="text-sm text-gray-600">{value}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
      />
      {showInfo && (
        <p className="mt-2 text-xs text-gray-500">{info}</p>
      )}
    </div>
  );
}

// Model Info Card Component
function ModelInfoCard({ modelId, models }) {
  const model = models.find(m => m.model_id === modelId);
  
  if (!model) return null;

  return (
    <div className="mt-4 p-4 bg-gray-50 rounded-lg">
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-gray-500">Context Window:</span>
          <span className="ml-2 font-medium">
            {(model.capabilities?.max_context_window || 0).toLocaleString()} tokens
          </span>
        </div>
        <div>
          <span className="text-gray-500">Max Output:</span>
          <span className="ml-2 font-medium">
            {(model.capabilities?.max_output_tokens || 0).toLocaleString()} tokens
          </span>
        </div>
        {model.cost_per_1k_input_tokens && (
          <div>
            <span className="text-gray-500">Input Cost:</span>
            <span className="ml-2 font-medium">
              ${model.cost_per_1k_input_tokens}/1K tokens
            </span>
          </div>
        )}
        {model.cost_per_1k_output_tokens && (
          <div>
            <span className="text-gray-500">Output Cost:</span>
            <span className="ml-2 font-medium">
              ${model.cost_per_1k_output_tokens}/1K tokens
            </span>
          </div>
        )}
      </div>
      {model.recommended_use_cases && model.recommended_use_cases.length > 0 && (
        <div className="mt-3">
          <span className="text-sm text-gray-500">Best for:</span>
          <div className="mt-1 flex flex-wrap gap-2">
            {model.recommended_use_cases.map(useCase => (
              <span
                key={useCase}
                className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded"
              >
                {useCase}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Preset Selector Component
function PresetSelector({ onSelectPreset }) {
  const presets = [
    {
      id: 'balanced',
      name: 'Balanced',
      description: 'Good balance of quality and speed',
      icon: Settings,
      color: 'blue'
    },
    {
      id: 'creative',
      name: 'Creative',
      description: 'More creative and varied responses',
      icon: Zap,
      color: 'purple'
    },
    {
      id: 'precise',
      name: 'Precise',
      description: 'Focused and deterministic responses',
      icon: Brain,
      color: 'green'
    },
    {
      id: 'fast',
      name: 'Fast',
      description: 'Optimized for quick responses',
      icon: RefreshCw,
      color: 'orange'
    },
    {
      id: 'powerful',
      name: 'Powerful',
      description: 'Maximum capability for complex tasks',
      icon: DollarSign,
      color: 'red'
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {presets.map(preset => {
        const Icon = preset.icon;
        return (
          <button
            key={preset.id}
            onClick={() => onSelectPreset(preset.id)}
            className="p-4 border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-all text-left"
          >
            <div className="flex items-start gap-3">
              <div className={`p-2 rounded-lg bg-${preset.color}-100`}>
                <Icon className={`h-5 w-5 text-${preset.color}-600`} />
              </div>
              <div className="flex-1">
                <h4 className="font-medium text-gray-900">{preset.name}</h4>
                <p className="mt-1 text-sm text-gray-500">{preset.description}</p>
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
```
---
