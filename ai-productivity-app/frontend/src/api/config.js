// api/config.ts
import client from './client';

interface ModelConfig {
  provider: string;
  chat_model: string;
  temperature?: number;
  maxTokens?: number;
  topP?: number;
  frequencyPenalty?: number;
  presencePenalty?: number;
  systemPrompt?: string;
}

interface ModelStats {
  requestsToday: number;
  estimatedCost: number;
  averageLatency: number;
  errorRate: number;
  lastUsed: Date;
}

interface TestResult {
  success: boolean;
  message?: string;
  latency?: number;
  error?: string;
}

class ConfigAPI {
  private baseURL = '/api/config';

  async getConfig() {
    const response = await client.get(this.baseURL);
    return response.data;
  }

  async updateModelConfig(config: ModelConfig) {
    const response = await client.put(`${this.baseURL}/model`, config);
    return response.data;
  }

  async testModelConfig(config: Partial<ModelConfig>): Promise<TestResult> {
    try {
      const response = await client.post(`${this.baseURL}/test`, config);
      return response.data;
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Test failed'
      };
    }
  }

  async getAvailableModels() {
    const response = await client.get(`${this.baseURL}/models`);
    return response.data;
  }

  async getModelStats(model: string): Promise<ModelStats> {
    const response = await client.get(`${this.baseURL}/models/${model}/stats`);
    return response.data;
  }

  async getModelPricing() {
    const response = await client.get(`${this.baseURL}/pricing`);
    return response.data;
  }

  async validateApiKey(provider: string, apiKey: string): Promise<boolean> {
    try {
      const response = await client.post(`${this.baseURL}/validate-key`, {
        provider,
        apiKey
      });
      return response.data.valid;
    } catch {
      return false;
    }
  }

  async getQuota(provider: string): Promise<{
    used: number;
    limit: number;
    resetDate: Date;
  }> {
    const response = await client.get(`${this.baseURL}/quota/${provider}`);
    return response.data;
  }
}

export const configAPI = new ConfigAPI();

// Prompts API
interface PromptTemplate {
  id?: string;
  name: string;
  description: string;
  category: string;
  systemPrompt: string;
  userPromptTemplate: string;
  variables: Variable[];
  modelPreferences?: Partial<ModelConfig>;
  isPublic: boolean;
  isDefault: boolean;
  usageCount?: number;
  createdAt?: string;
  updatedAt?: string;
}

interface Variable {
  name: string;
  description: string;
  defaultValue?: string;
  required: boolean;
}

class PromptsAPI {
  private baseURL = '/api/prompts';

  async getTemplates(filters?: {
    category?: string;
    search?: string;
    isPublic?: boolean;
  }): Promise<{ templates: PromptTemplate[]; total: number }> {
    const response = await client.get(this.baseURL, { params: filters });
    return response.data;
  }

  async getTemplate(id: string): Promise<PromptTemplate> {
    const response = await client.get(`${this.baseURL}/${id}`);
    return response.data;
  }

  async createTemplate(template: Omit<PromptTemplate, 'id' | 'createdAt' | 'updatedAt'>): Promise<PromptTemplate> {
    const response = await client.post(this.baseURL, template);
    return response.data;
  }

  async updateTemplate(id: string, updates: Partial<PromptTemplate>): Promise<PromptTemplate> {
    const response = await client.put(`${this.baseURL}/${id}`, updates);
    return response.data;
  }

  async deleteTemplate(id: string): Promise<void> {
    await client.delete(`${this.baseURL}/${id}`);
  }

  async duplicateTemplate(id: string, newName: string): Promise<PromptTemplate> {
    const response = await client.post(`${this.baseURL}/${id}/duplicate`, { name: newName });
    return response.data;
  }

  async executeTemplate(id: string, variables: Record<string, string>): Promise<{
    systemPrompt: string;
    userPrompt: string;
    modelConfig?: Partial<ModelConfig>;
  }> {
    const response = await client.post(`${this.baseURL}/${id}/execute`, { variables });
    return response.data;
  }

  async getTemplateStats(id: string): Promise<{
    usageCount: number;
    averageTokens: number;
    averageLatency: number;
    successRate: number;
  }> {
    const response = await client.get(`${this.baseURL}/${id}/stats`);
    return response.data;
  }

  async shareTemplate(id: string, users: string[]): Promise<void> {
    await client.post(`${this.baseURL}/${id}/share`, { users });
  }
}

export const promptAPI = new PromptsAPI();
