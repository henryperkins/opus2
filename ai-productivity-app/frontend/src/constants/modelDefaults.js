/**
 * Default model configuration constants.
 * Single source of truth for default values across the frontend.
 */

// Default generation parameters - matches backend schemas/generation.py
export const DEFAULT_GENERATION_PARAMS = {
  temperature: 0.7,
  max_tokens: 4000,
  top_p: 1.0,
  presence_penalty: 0,
  frequency_penalty: 0
};

// Default provider and model
export const DEFAULT_PROVIDER = 'openai';
export const DEFAULT_MODEL = 'gpt-4o-mini';

// Default reasoning parameters
export const DEFAULT_REASONING_PARAMS = {
  enable_reasoning: false,
  reasoning_effort: 'medium',
  claude_extended_thinking: true,
  claude_thinking_mode: 'enabled',
  claude_thinking_budget_tokens: 16384,
  claude_show_thinking_process: true,
  claude_adaptive_thinking_budget: true
};

// Default provider config
export const DEFAULT_PROVIDER_CONFIG = {
  use_responses_api: false,
  api_version: null,
  endpoint: null
};

// Combined default configuration
export const DEFAULT_CONFIG = {
  provider: DEFAULT_PROVIDER,
  model_id: DEFAULT_MODEL,
  use_responses_api: DEFAULT_PROVIDER_CONFIG.use_responses_api,
  ...DEFAULT_GENERATION_PARAMS,
  ...DEFAULT_REASONING_PARAMS
};

// Factory function for creating config data with defaults
export const createConfigData = (data = {}) => ({
  providers: data.providers || {},
  current: {
    provider: data.current?.provider || DEFAULT_PROVIDER,
    model_id: data.current?.model_id || data.current?.chat_model || DEFAULT_MODEL,
    use_responses_api: data.current?.use_responses_api ?? DEFAULT_PROVIDER_CONFIG.use_responses_api,
    ...DEFAULT_GENERATION_PARAMS,
    ...data.current
  },
  available: data.available || {
    models: [],
    providers: []
  }
});

// Model performance tracking defaults
export const DEFAULT_MODEL_STATS = new Map();
export const DEFAULT_MODEL_HISTORY = [];

// UI state defaults
export const DEFAULT_UI_STATE = {
  loading: false,
  error: null
};

export default {
  DEFAULT_GENERATION_PARAMS,
  DEFAULT_PROVIDER,
  DEFAULT_MODEL,
  DEFAULT_REASONING_PARAMS,
  DEFAULT_PROVIDER_CONFIG,
  DEFAULT_CONFIG,
  createConfigData,
  DEFAULT_MODEL_STATS,
  DEFAULT_MODEL_HISTORY,
  DEFAULT_UI_STATE
};