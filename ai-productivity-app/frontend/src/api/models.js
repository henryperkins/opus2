/* eslint-disable */
// api/models.js  
// Model selection and management API - Updated to use unified API

import client from './client';
import { configAPI } from './config';

export const modelsAPI = {
    /**
     * Detect task type from user query
     * @param {string} query - User's input query
     * @returns {Promise<string>} Detected task type (coding, analysis, creative, etc.)
     */
    detectTask: async (query) => {
        // Task detection logic moved to client-side for performance
        // Simple heuristic-based detection
        const taskPatterns = {
            'coding': /code|program|function|class|debug|implement|script|api/i,
            'analysis': /analyze|compare|evaluate|assess|review|examine/i,
            'creative': /write|create|generate|compose|design|story|poem/i,
            'documentation': /document|explain|describe|guide|tutorial|readme/i,
            'testing': /test|unit|integration|spec|verify|validate/i,
            'debugging': /bug|error|fix|issue|problem|broken|fail/i,
            'architecture': /design|architecture|pattern|structure|system|framework/i
        };

        for (const [taskType, pattern] of Object.entries(taskPatterns)) {
            if (pattern.test(query)) {
                return taskType;
            }
        }
        
        return 'general';
    },

    /**
     * Get available models and their capabilities
     * @returns {Promise<Array>} List of models with capabilities
     */
    getAvailableModels: async () => {
        const config = await configAPI.getConfig();
        return config.available_models || [];
    },

    /**
     * Match models to task capabilities
     * @param {string} taskType - Type of task
     * @param {object} modelSettings - Model configuration settings
     * @returns {Promise<Array>} Models capable of handling the task
     */
    matchCapabilities: async (taskType, modelSettings) => {
        const models = await modelsAPI.getAvailableModels();
        
        // Task-specific model recommendations
        const taskModelPreferences = {
            'coding': ['gpt-4o', 'gpt-4-turbo', 'claude-3-5-sonnet'],
            'analysis': ['gpt-4o', 'claude-3-5-sonnet', 'gpt-4-turbo'],
            'creative': ['gpt-4o', 'claude-3-5-sonnet', 'gpt-4'],
            'documentation': ['gpt-4o-mini', 'gpt-3.5-turbo', 'claude-3-haiku'],
            'testing': ['gpt-4o-mini', 'gpt-3.5-turbo'],
            'debugging': ['gpt-4o', 'gpt-4-turbo', 'claude-3-5-sonnet'],
            'architecture': ['gpt-4o', 'claude-3-5-sonnet', 'gpt-4']
        };

        const preferredModels = taskModelPreferences[taskType] || [];
        const availableModelIds = models.map(m => m.model_id);
        
        return models.filter(model => {
            // Check if model is in preferred list or available
            const isPreferred = preferredModels.includes(model.model_id);
            const isAvailable = availableModelIds.includes(model.model_id);
            
            // Check capabilities based on task type
            let hasRequiredCapabilities = true;
            if (taskType === 'coding' && !model.capabilities?.supports_functions) {
                hasRequiredCapabilities = false;
            }
            
            return isAvailable && (isPreferred || hasRequiredCapabilities);
        });
    },

    /**
     * Evaluate cost and performance for model selection
     * @param {Array} models - Models to evaluate
     * @param {object} settings - Model settings including cost limits
     * @returns {Promise<Array>} Models with cost/performance scores
     */
    evaluateCostPerformance: async (models, settings) => {
        return models.map(model => {
            const costPer1k = model.cost_per_1k_tokens || { input: 0.01, output: 0.03 };
            const estimatedCost = (costPer1k.input + costPer1k.output) / 2;
            
            // Simple scoring algorithm
            const costScore = Math.max(0, 1 - (estimatedCost / 0.1)); // Normalize to 0-1
            const performanceScore = model.performance_tier || 0.5; // Default mid-tier
            const score = (costScore + performanceScore) / 2;
            
            return {
                ...model,
                estimated_cost: estimatedCost,
                score: score,
                within_budget: !settings.costLimit || estimatedCost <= settings.costLimit
            };
        });
    },

    /**
     * Select optimal model based on evaluation
     * @param {Array} evaluatedModels - Models with scores
     * @param {object} settings - Model settings
     * @returns {string} Selected model name
     */
    selectOptimalModel: (evaluatedModels, settings) => {
        // This can be done client-side for performance
        const withinBudget = evaluatedModels.filter(m => m.within_budget);
        const candidates = withinBudget.length > 0 ? withinBudget : evaluatedModels;
        return candidates.sort((a, b) => b.score - a.score)[0]?.model_id || settings.default;
    },

    /**
     * Call a specific model with the query
     * @param {string} model - Model name
     * @param {string} query - Query to send
     * @param {object} options - Additional options (temperature, max_tokens, etc.)
     * @returns {Promise<object>} Model response
     */
    callModel: async (model, query, options = {}) => {
        // Use chat API for model calls
        const response = await client.post('/api/chat/send', {
            message: query,
            model_override: model,
            ...options
        });
        return response.data;
    },

    /**
     * Handle fallback when primary model fails
     * @param {string} failedModel - Model that failed
     * @param {string} query - Original query
     * @param {Array} fallbacks - List of fallback models
     * @returns {Promise<object>} Response from fallback model
     */
    handleFallback: async (failedModel, query, fallbacks) => {
        // Try each fallback model in order
        for (const fallbackModel of fallbacks) {
            try {
                const response = await modelsAPI.callModel(fallbackModel, query);
                return {
                    success: true,
                    model: fallbackModel,
                    response: response,
                    failed_model: failedModel
                };
            } catch (error) {
                continue; // Try next fallback
            }
        }
        
        throw new Error(`All fallback models failed for query after ${failedModel} failed`);
    },

    /**
     * Get model usage statistics
     * @param {string} projectId - Project ID
     * @param {object} timeRange - Time range for stats
     * @returns {Promise<object>} Usage statistics
     */
    getUsageStats: async (projectId, timeRange = {}) => {
        const response = await client.get(`/api/analytics/usage`, {
            params: { project_id: projectId, ...timeRange }
        });
        return response.data;
    },

    /**
     * Update model preferences
     * @param {string} projectId - Project ID
     * @param {object} preferences - Model preferences
     * @returns {Promise<object>} Updated preferences
     */
    updatePreferences: async (projectId, preferences) => {
        // Update via config API
        const response = await configAPI.updateModelConfig(preferences);
        return response;
    },

    /**
     * Get real-time model status (availability, latency, etc.)
     * @returns {Promise<object>} Model status information
     */
    getModelStatus: async () => {
        const config = await configAPI.getConfig();
        
        // Build status from available models
        const status = {
            providers: {},
            last_updated: new Date().toISOString()
        };
        
        // Group by provider
        config.available_models?.forEach(model => {
            if (!status.providers[model.provider]) {
                status.providers[model.provider] = {
                    available: true,
                    models: [],
                    latency: Math.random() * 1000 + 500 // Mock latency
                };
            }
            status.providers[model.provider].models.push({
                model_id: model.model_id,
                available: true,
                latency: Math.random() * 500 + 200
            });
        });
        
        return status;
    }
};

export default modelsAPI;
