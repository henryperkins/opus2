// api/config.js
import client from './client';

// ---------------------------------------------------------------------------
// Factory helpers (keep in sync with backend pydantic models where possible)
// ---------------------------------------------------------------------------

export const createModelConfig = (data = {}) => ({
  provider: data.provider || 'openai',
  model_id: data.model_id || data.modelId || data.chat_model || 'gpt-4o-mini',
  temperature: data.temperature,
  max_tokens: data.max_tokens || data.maxTokens,
  top_p: data.top_p || data.topP,
  frequency_penalty: data.frequency_penalty || data.frequencyPenalty,
  presence_penalty: data.presence_penalty || data.presencePenalty,
  system_prompt: data.system_prompt || data.systemPrompt,
});

export const createModelStats = (data = {}) => ({
  requestsToday: data.requestsToday || 0,
  estimatedCost: data.estimatedCost || 0,
  averageLatency: data.averageLatency || 0,
  errorRate: data.errorRate || 0,
  lastUsed: data.lastUsed || new Date(),
});

export const createTestResult = (data = {}) => ({
  success: data.success || false,
  message: data.message,
  latency: data.latency,
  error: data.error,
});

class ConfigAPI {
  constructor() {
    this.baseURL = '/api/v1/ai-config';
  }

  async getConfig() {
    const response = await client.get(this.baseURL);
    return response.data;
  }

  // ---------------------------------------------------------------------
  // Runtime configuration updates
  // ---------------------------------------------------------------------
  async updateModelConfig(config) {
    // Strip the special `__noRetry` flag from the JSON payload – keep it only
    // in the Axios request config so the interceptor can honour it.
    const { __noRetry, ...payload } = config ?? {};
    const axiosCfg = __noRetry ? { __noRetry } : undefined;
    const response = await client.put(this.baseURL, payload, axiosCfg);

    // The unified API returns the full updated config directly
    const fullConfig = response.data;

    if (typeof window !== 'undefined') {
      try {
        window.dispatchEvent(
          new CustomEvent('configUpdate', {
            detail: {
              config: fullConfig,
              requested: true,
            },
          }),
        );
      } catch (_) {
        /* noop */
      }
    }

    return fullConfig;
  }

  async testModelConfig(config) {
    try {
      const response = await client.post(`${this.baseURL}/test`, config);
      return response.data;
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Test failed',
      };
    }
  }

  async getAvailableModels() {
    const response = await client.get(`${this.baseURL}/models`);
    return response.data;
  }

  async getModelInfo(modelId) {
    const response = await client.get(`${this.baseURL}/models/${modelId}`);
    return response.data;
  }

  async validateConfiguration(config) {
    const response = await client.post(`${this.baseURL}/validate`, config);
    return response.data;
  }

  async getConfigurationPresets() {
    const response = await client.get(`${this.baseURL}/presets`);
    return response.data;
  }
}

export const configAPI = new ConfigAPI();

// ---------------------------------------------------------------------------
// Prompt template helpers (unrelated to issue but kept for backwards-compat)
// ---------------------------------------------------------------------------

export const createVariable = (data = {}) => ({
  name: data.name || '',
  description: data.description || '',
  defaultValue: data.defaultValue,
  required: data.required || false,
});

export const createPromptTemplate = (data = {}) => ({
  id: data.id,
  name: data.name || '',
  description: data.description || '',
  category: data.category || 'general',
  systemPrompt: data.systemPrompt || '',
  userPromptTemplate: data.userPromptTemplate || '',
  variables: data.variables || [],
  modelPreferences: data.modelPreferences,
  isPublic: data.isPublic || false,
  isDefault: data.isDefault || false,
  usageCount: data.usageCount || 0,
  createdAt: data.createdAt,
  updatedAt: data.updatedAt,
});

class PromptsAPI {
  constructor() {
    this.baseURL = '/api/prompts';
  }

  async getTemplates(filters = {}) {
    const response = await client.get(this.baseURL, { params: filters });
    return response.data;
  }

  async getTemplate(id) {
    const response = await client.get(`${this.baseURL}/${id}`);
    return response.data;
  }

  async createTemplate(template) {
    const response = await client.post(this.baseURL, template);
    return response.data;
  }

  async updateTemplate(id, updates) {
    const response = await client.put(`${this.baseURL}/${id}`, updates);
    return response.data;
  }

  async deleteTemplate(id) {
    await client.delete(`${this.baseURL}/${id}`);
  }

  async duplicateTemplate(id, newName) {
    const response = await client.post(`${this.baseURL}/${id}/duplicate`, {
      name: newName,
    });
    return response.data;
  }

  async executeTemplate(id, variables) {
    const response = await client.post(`${this.baseURL}/${id}/execute`, {
      variables,
    });
    return response.data;
  }

  async getTemplateStats(id) {
    const response = await client.get(`${this.baseURL}/${id}/stats`);
    return response.data;
  }

  async shareTemplate(id, users) {
    await client.post(`${this.baseURL}/${id}/share`, {
      users,
    });
  }
}

export const promptAPI = new PromptsAPI();
