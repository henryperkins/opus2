# Unified AI Configuration System - Critical Fixes

This document outlines the critical fixes needed for the unified AI configuration system based on the second-pass audit. Items are organized by criticality level and include concrete implementation steps.

## Critical Priority Fixes (🚨 Must-fix before rollout)

### 1. RuntimeConfig Key Collision Fix

**Problem**: Migration writes snake_case keys but old rows may contain both snake_case and camelCase versions, causing duplicate key conflicts.

**Solution**: Implement comprehensive Alembic data migration:

```python
# alembic/versions/xxx_fix_runtime_config_keys.py
def upgrade():
    # Create backup first
    op.execute("CREATE TABLE runtime_config_backup AS SELECT * FROM runtime_config")
    
    # Convert all camelCase keys to snake_case
    op.execute("""
        UPDATE runtime_config
        SET key = lower(regexp_replace(key, '([A-Z])', '_\\1', 'g'))
        WHERE key ~ '[A-Z]'
    """)
    
    # Remove duplicate keys (keep the most recent)
    op.execute("""
        DELETE FROM runtime_config a
        USING runtime_config b
        WHERE a.id < b.id 
        AND a.key = b.key
        AND a.user_id = b.user_id
    """)
    
    # Add unique constraint if not exists
    op.create_unique_constraint('uq_runtime_config_key_user', 
                                'runtime_config', ['key', 'user_id'])

def downgrade():
    op.drop_constraint('uq_runtime_config_key_user', 'runtime_config')
    # Restore from backup if needed
```

### 2. PromptTemplate LLM Preferences Deserialization

**Problem**: Existing JSON uses camelCase (`maxTokens`, `topP`) but new `GenerationParams` expects snake_case.

**Solution**: One-time migration script:

```python
# scripts/migrate_prompt_templates.py
import asyncio
from sqlalchemy import select
from app.database import async_session
from app.models import PromptTemplate
from app.schemas.generation import GenerationParams

FIELD_MAPPING = {
    'maxTokens': 'max_tokens',
    'topP': 'top_p',
    'topK': 'top_k',
    'frequencyPenalty': 'frequency_penalty',
    'presencePenalty': 'presence_penalty',
    'stopSequences': 'stop_sequences',
}

async def migrate_prompt_templates():
    async with async_session() as session:
        templates = await session.execute(select(PromptTemplate))
        
        for template in templates.scalars():
            if template.llm_preferences:
                # Convert camelCase to snake_case
                migrated = {}
                for old_key, new_key in FIELD_MAPPING.items():
                    if old_key in template.llm_preferences:
                        migrated[new_key] = template.llm_preferences[old_key]
                
                # Validate against schema
                try:
                    validated = GenerationParams(**migrated)
                    template.llm_preferences = validated.model_dump()
                except ValidationError as e:
                    print(f"Template {template.id} validation failed: {e}")
                    # Apply defaults for invalid values
                    template.llm_preferences = GenerationParams().model_dump()
        
        await session.commit()

if __name__ == "__main__":
    asyncio.run(migrate_prompt_templates())
```

### 3. Stale Worker Cache Mitigation

**Problem**: LLMClient caches config per process; multi-worker deployments serve outdated params.

**Solution A - TTL-based (Quick fix)**:
```python
# app/services/llm_client.py
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

class LLMClient:
    def __init__(self):
        self._config_cache: Dict[str, tuple[Any, datetime]] = {}
        self._cache_ttl = timedelta(seconds=5)
    
    async def _get_config(self, key: str) -> Any:
        # Check cache with TTL
        if key in self._config_cache:
            value, timestamp = self._config_cache[key]
            if datetime.utcnow() - timestamp < self._cache_ttl:
                return value
        
        # Fetch fresh config
        value = await self.config_service.get_config(key)
        self._config_cache[key] = (value, datetime.utcnow())
        return value
```

**Solution B - Redis Pub/Sub (Robust)**:
```python
# app/services/config_invalidation.py
import redis.asyncio as redis
from app.core.config import settings

class ConfigInvalidator:
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL)
        self.pubsub = self.redis.pubsub()
        
    async def publish_change(self, key: str):
        await self.redis.publish('config_changes', f'{key}:invalidate')
    
    async def subscribe_changes(self, callback):
        await self.pubsub.subscribe('config_changes')
        async for message in self.pubsub.listen():
            if message['type'] == 'message':
                key = message['data'].decode().split(':')[0]
                await callback(key)
```

### 4. Provider Interface Backward Compatibility

**Problem**: Changing `LLMProvider.complete()` signature breaks all adapters.

**Solution**: Implement shim with deprecation warning:

```python
# app/providers/base.py
import warnings
from typing import Union

class LLMProvider:
    def complete(self, *args, **kwargs):
        """Backward compatibility shim"""
        if len(args) == 6:  # Old signature
            warnings.warn(
                "LLMProvider.complete() old signature is deprecated. "
                "Use complete(messages, model, generation_params, reasoning_params) instead.",
                DeprecationWarning,
                stacklevel=2
            )
            messages, model, temperature, max_tokens, stream, tools = args
            gen_params = GenerationParams(
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                tools=tools
            )
            return self._complete_new(messages, model, gen_params)
        else:
            # New signature
            return self._complete_new(*args, **kwargs)
    
    def _complete_new(self, messages, model: str, 
                     generation_params: GenerationParams,
                     reasoning_params: Optional[ReasoningParams] = None):
        """New implementation"""
        raise NotImplementedError
```

## High Priority Fixes (⚠️ Post-launch pain points)

### 5. Maintain CamelCase API Responses

**Problem**: Frontend expects camelCase but backend uses snake_case internally.

**Solution**: Use Pydantic alias generation:

```python
# app/schemas/generation.py
from pydantic import BaseModel, ConfigDict
from app.utils.naming import to_camel

class GenerationParamsResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        json_schema_extra={
            "example": {
                "temperature": 0.7,
                "maxTokens": 1000,
                "topP": 0.9
            }
        }
    )
    
    temperature: float
    max_tokens: int
    top_p: float
    # ... other fields
```

### 6. Model Catalogue Seeding

**Problem**: Frontend shows empty dropdown until database is seeded.

**Solution**: Create seeding mechanism:

```python
# app/cli/seed_models.py
import asyncio
import json
from pathlib import Path
from app.database import async_session
from app.models import ModelCatalog

MODELS_FIXTURE = Path(__file__).parent / "fixtures" / "models.json"

async def seed_models():
    async with async_session() as session:
        # Check if already seeded
        existing = await session.execute(select(func.count(ModelCatalog.id)))
        if existing.scalar() > 0:
            print("Models already seeded")
            return
        
        # Load fixture
        with open(MODELS_FIXTURE) as f:
            models = json.load(f)
        
        # Insert models
        for model_data in models:
            model = ModelCatalog(**model_data)
            session.add(model)
        
        await session.commit()
        print(f"Seeded {len(models)} models")

# Add to alembic migration
def upgrade():
    # ... structural changes ...
    
    # Seed initial data
    from app.cli.seed_models import seed_models
    asyncio.run(seed_models())
```

### 7. Fix Async Context Startup

**Problem**: Running sync SQL in async context causes deadlocks.

**Solution**: Proper async initialization:

```python
# app/core/startup.py
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    from app.cli.seed_models import seed_models
    await seed_models()
    
    # Initialize caches
    from app.services.config_cache import ConfigCache
    await ConfigCache.initialize()
    
    yield
    
    # Shutdown
    await ConfigCache.cleanup()

app = FastAPI(lifespan=lifespan)
```

### 8. Feature Flag Implementation

**Problem**: No rollback mechanism if migration fails.

**Solution**: Environment-based feature flag:

```python
# app/core/config.py
class Settings(BaseSettings):
    ENABLE_UNIFIED_CONFIG: bool = Field(default=False, env="ENABLE_UNIFIED_CONFIG")
    
# app/routers/__init__.py
from app.core.config import settings

if settings.ENABLE_UNIFIED_CONFIG:
    from app.routers.unified_config import router as unified_router
    app.include_router(unified_router, prefix="/api/config")
else:
    from app.routers.legacy_config import router as legacy_router
    app.include_router(legacy_router, prefix="/api/models")
```

## Quick Wins (✓)

### 9. Secret Encryption Pathway

Ensure snake_case keys work with encryption:

```python
# app/services/config_service.py
SECRET_KEYS = {
    'openai_api_key',
    'anthropic_api_key', 
    'azure_api_key',
    # Add all secret keys in snake_case
}

def _get_value_type(self, key: str) -> ValueType:
    # Normalize to snake_case for comparison
    snake_key = to_snake_case(key)
    if snake_key in SECRET_KEYS:
        return ValueType.SECRET
    return ValueType.STRING
```

### 10. Complete Schema Mixins

Add missing parameters:

```python
# app/schemas/generation.py
class ChatParams(BaseModel):
    """Extended chat parameters"""
    system_prompt: Optional[str] = None
    stop_sequences: Optional[List[str]] = None
    stream: bool = False
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    parallel_tool_calls: bool = True
    
class ReasoningParams(BaseModel):
    """Extended reasoning parameters for all providers"""
    # Azure
    reasoning_effort: Optional[str] = None
    
    # Anthropic Claude thinking
    thinking_mode: Optional[bool] = None
    thinking_tokens: Optional[int] = None
    
    # Future providers
    chain_of_thought: Optional[bool] = None
```

## Implementation Sequence

1. **Week 1**: Implement all 🚨 critical fixes (1-4)
2. **Week 2**: Deploy with feature flag disabled, run migrations
3. **Week 3**: Enable feature flag for 10% traffic, monitor
4. **Week 4**: Fix any issues, roll out to 100%
5. **Week 5**: Implement remaining ⚠️ fixes
6. **Week 6**: Documentation and deprecation notices

## Testing Checklist

- [ ] Unit tests for all migration scripts
- [ ] Integration tests for config service with cache
- [ ] E2E tests for configuration updates
- [ ] Load tests for cache invalidation
- [ ] Rollback procedure tested
- [ ] Frontend compatibility verified
- [ ] API backward compatibility confirmed

## Monitoring Setup

```python
# app/monitoring/config_metrics.py
from prometheus_client import Counter, Histogram

config_changes = Counter('config_changes_total', 
                        'Total configuration changes',
                        ['key', 'user'])
                        
config_cache_hits = Counter('config_cache_hits_total',
                           'Configuration cache hits')
                           
config_load_time = Histogram('config_load_seconds',
                            'Time to load configuration')
```