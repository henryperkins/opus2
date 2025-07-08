/**
 * Default model configuration constants.
 * Single source of truth for default values across the frontend.
 */

// Default generation parameters - matches backend schemas/generation.py
export const DEFAULT_GENERATION_PARAMS = {
  temperature: 0.7,
  maxTokens: 4000,
  topP: 1.0,
  presencePenalty: 0,
  frequencyPenalty: 0
};

// Default provider and model
export const DEFAULT_PROVIDER = 'openai';
export const DEFAULT_MODEL = 'gpt-4o-mini';

// Default reasoning parameters
export const DEFAULT_REASONING_PARAMS = {
  enableReasoning: false,
  reasoningEffort: 'medium',
  claudeExtendedThinking: true,
  claudeThinkingMode: 'enabled',
  claudeThinkingBudgetTokens: 16384,
  claudeShowThinkingProcess: true,
  claudeAdaptiveThinkingBudget: true
};

// Default provider config
export const DEFAULT_PROVIDER_CONFIG = {
  useResponsesApi: false,
  apiVersion: null,
  endpoint: null
};

// Combined default configuration
export const DEFAULT_CONFIG = {
  provider: DEFAULT_PROVIDER,
  chat_model: DEFAULT_MODEL,
  model_id: DEFAULT_MODEL,
  useResponsesApi: DEFAULT_PROVIDER_CONFIG.useResponsesApi,
  ...DEFAULT_GENERATION_PARAMS,
  ...DEFAULT_REASONING_PARAMS
};

// Factory function for creating config data with defaults
export const createConfigData = (data = {}) => ({
  providers: data.providers || {},
  current: {
    provider: data.current?.provider || DEFAULT_PROVIDER,
    chat_model: data.current?.chat_model || data.current?.model_id || DEFAULT_MODEL,
    model_id: data.current?.model_id || data.current?.chat_model || DEFAULT_MODEL,
    useResponsesApi: data.current?.useResponsesApi ?? DEFAULT_PROVIDER_CONFIG.useResponsesApi,
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