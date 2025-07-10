# Plan to Address Configuration Layer Issues

## Phase 1: Critical Database & Data Consistency Fixes (Priority: HIGH)

### 1.1 Fix ModelConfiguration Capabilities Column
**Issue**: Column default is `[]` (array) but services expect dictionary
**Actions**:
1. Create new Alembic migration to fix the default:
   ```python
   # alembic/versions/007_fix_capabilities_default.py
   def upgrade():
       op.alter_column('model_configurations', 'capabilities',
                      server_default=text('{}::jsonb'))
   ```
2. Update the model definition in `app/models/config.py`:
   ```python
   capabilities = Column(JSONB, nullable=False, default=dict,
                        comment="Model capabilities as key-value pairs")
   ```
3. Run a data migration to convert any existing array values to objects

### 1.2 Fix RuntimeConfig Value Storage
**Issue**: Mixing JSON strings and Python objects in value column
**Actions**:
1. Standardize on JSONB native storage - no JSON strings
2. Update `_save_config` method to store values directly:
   ```python
   # Don't use json.dumps() - PostgreSQL JSONB handles it
   existing.value = value  # Store dict/list directly
   ```
3. Update `_load_all_config` to handle values consistently

### 1.3 Fix client_factory._optional() Helper
**Issue**: Returns `{"dummy": value}` instead of proper kwargs
**Actions**:
1. Fix the helper to return proper keyword arguments:
   ```python
   def _optional(key: str, value: Any) -> Dict[str, Any]:
       """Return {key: value} if value is truthy, else {}."""
       return {key: value} if value else {}
   ```
2. Update all usages to pass the key name:
   ```python
   kwargs.update(_optional("base_url", base_url))
   kwargs.update(_optional("organization", org))
   ```

## Phase 2: Service Layer Completion (Priority: HIGH)

### 2.1 Complete UnifiedConfigService Field Mappings
**Issue**: Missing camelCase mappings for frontend fields
**Actions**:
1. Add missing field mappings:
   ```python
   field_mappings = {
       # Existing mappings...
       "responseFormat": "response_format",
       "systemPrompt": "system_prompt",
       "thinkingBudgetTokens": "thinking_budget_tokens",
       "showThinkingProcess": "show_thinking_process",
       "adaptiveThinkingBudget": "adaptive_thinking_budget",
       "parallelToolCalls": "parallel_tool_calls",
   }
   ```

### 2.2 Implement Missing Service Methods
**Issue**: Stub methods returning empty results
**Actions**:
1. Implement `get_presets()`:
   ```python
   def get_presets(self) -> List[Dict[str, Any]]:
       """Return predefined configuration presets."""
       return [
           {"name": "fast", "config": {...}},
           {"name": "balanced", "config": {...}},
           {"name": "powerful", "config": {...}},
       ]
   ```
2. Implement `get_defaults()` to return authoritative defaults
3. Remove or complete the `/presets` endpoint

### 2.3 Fix Model Service Cache Invalidation
**Issue**: Negative lookups cached forever
**Actions**:
1. Add TTL to cache entries:
   ```python
   self._cache[cache_key] = {
       'value': capabilities,
       'timestamp': datetime.utcnow()
   }
   ```
2. Add cache invalidation method
3. Call invalidation when models are added/updated

## Phase 3: Provider Consolidation (Priority: MEDIUM)

### 3.1 Consolidate Pattern Lists
**Issue**: Duplicate pattern lists across providers and services
**Actions**:
1. Keep patterns only in ModelService as the single source of truth
2. Remove pattern lists from AzureOpenAIProvider
3. Ensure all providers use ModelService static methods

### 3.2 Fix Azure Provider Responses API Flag
**Issue**: `use_responses_api` not updated after auto-detection
**Actions**:
1. Update the flag after auto-detection:
   ```python
   if auto_responses and not self.use_responses_api:
       self.use_responses_api = True
   ```

### 3.3 Extract Common Provider Utilities
**Issue**: Duplicate implementations of validate_tools, extract_content, etc.
**Actions**:
1. Move all common methods to `providers/utils.py`
2. Update all providers to use shared utilities
3. Remove duplicate implementations

## Phase 4: Frontend Integration (Priority: HIGH)

### 4.1 Remove Legacy API Calls
**Issue**: Frontend calling non-existent `/api/models/*` endpoints
**Actions**:
1. Update `frontend/src/api/models.js` to use `/api/v1/ai-config`
2. Remove or redirect legacy endpoint references
3. Update all hooks to use the unified API

### 4.2 Fix Frontend Field Names
**Issue**: Inconsistent field naming between frontend and backend
**Actions**:
1. Audit all frontend components for field names
2. Ensure consistent use of either camelCase or snake_case
3. Update components to use normalized field names

### 4.3 Wire Claude Thinking Settings
**Issue**: Settings defined but not sent in updates
**Actions**:
1. Update ThinkingConfiguration.jsx to include all settings in update payload
2. Ensure all 7 Claude settings are properly mapped and sent

## Phase 5: Complete Claude Thinking Implementation (Priority: MEDIUM)

### 5.1 Implement All Claude Thinking Flags
**Issue**: Only 2 of 7 settings are used
**Actions**:
1. Update AnthropicProvider to use all settings:
   - `claude_thinking_budget_tokens` ✓ (already used)
   - `claude_show_thinking_process` → Include in response
   - `claude_adaptive_thinking_budget` → Implement budget adjustment
   - `claude_max_thinking_budget` → Set upper limit
2. Add thinking process visibility controls
3. Implement adaptive budget logic

### 5.2 Add OpenAI Provider Tool Streaming
**Issue**: Tool call deltas ignored in streaming
**Actions**:
1. Update OpenAIProvider.stream() to handle tool deltas
2. Add tool streaming support similar to Azure provider

## Phase 6: Testing & Validation (Priority: HIGH)

### 6.1 Add Integration Tests
**Actions**:
1. Test capability detection from database
2. Test configuration updates with all field variations
3. Test provider selection and auto-configuration
4. Test tool calling with all providers

### 6.2 Add Migration Tests
**Actions**:
1. Test data migration for capabilities column
2. Test RuntimeConfig value type handling
3. Verify seed data loads correctly

### 6.3 End-to-End Testing
**Actions**:
1. Test frontend → API → provider flow
2. Test all configuration updates
3. Test Claude thinking features
4. Test model switching and provider changes

## Implementation Order

1. **Week 1**: Phase 1 (Database fixes) + Phase 2.1 (Field mappings)
2. **Week 2**: Phase 4.1 (Remove legacy APIs) + Phase 2.2-2.3 (Service completion)
3. **Week 3**: Phase 3 (Provider consolidation) + Phase 5 (Claude thinking)
4. **Week 4**: Phase 6 (Testing) + remaining frontend fixes

## Success Criteria

- [ ] All database columns have consistent types between schema and usage
- [ ] No mixed JSON string/object storage in RuntimeConfig
- [ ] All frontend fields properly mapped and persisted
- [ ] No duplicate pattern lists or utility functions
- [ ] All Claude thinking settings functional
- [ ] Frontend exclusively uses unified API endpoints
- [ ] Comprehensive test coverage for configuration flow
- [ ] No placeholder or stub implementations remain

## Risk Mitigation

1. **Database Migration**: Test thoroughly on staging before production
2. **API Changes**: Maintain backward compatibility during transition
3. **Frontend Updates**: Deploy behind feature flags if needed
4. **Provider Changes**: Add extensive logging for debugging

This plan addresses all identified issues while minimizing disruption to the running system. Each phase can be implemented independently, allowing for incremental progress and testing.
