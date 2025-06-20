/* eslint-disable */
// api/models.js
// Model selection and management API

import client from './client';

export const modelsAPI = {
    /**
     * Detect task type from user query
     * @param {string} query - User's input query
     * @returns {Promise<string>} Detected task type (coding, analysis, creative, etc.)
     */
    detectTask: async (query) => {
        const response = await client.post('/api/models/detect-task', {
            query
        });
        return response.data.task_type;
    },

    /**
     * Get available models and their capabilities
     * @returns {Promise<Array>} List of models with capabilities
     */
    getAvailableModels: async () => {
        const response = await client.get('/api/models/available');
        return response.data;
    },

    /**
     * Match models to task capabilities
     * @param {string} taskType - Type of task
     * @param {object} modelSettings - Model configuration settings
     * @returns {Promise<Array>} Models capable of handling the task
     */
    matchCapabilities: async (taskType, modelSettings) => {
        const response = await client.post('/api/models/match-capabilities', {
            task_type: taskType,
            available_models: [modelSettings.default, ...modelSettings.fallbacks],
            auto_switch: modelSettings.autoSwitch
        });
        return response.data;
    },

    /**
     * Evaluate cost and performance for model selection
     * @param {Array} models - Models to evaluate
     * @param {object} settings - Model settings including cost limits
     * @returns {Promise<Array>} Models with cost/performance scores
     */
    evaluateCostPerformance: async (models, settings) => {
        const response = await client.post('/api/models/evaluate-cost-performance', {
            models,
            cost_limit: settings.costLimit,
            auto_switch: settings.autoSwitch
        });
        return response.data;
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
        return candidates.sort((a, b) => b.score - a.score)[0]?.model || settings.default;
    },

    /**
     * Call a specific model with the query
     * @param {string} model - Model name
     * @param {string} query - Query to send
     * @param {object} options - Additional options (temperature, max_tokens, etc.)
     * @returns {Promise<object>} Model response
     */
    callModel: async (model, query, options = {}) => {
        const response = await client.post('/api/models/call', {
            model,
            query,
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
        const response = await client.post('/api/models/fallback', {
            failed_model: failedModel,
            query,
            fallback_models: fallbacks
        });
        return response.data;
    },

    /**
     * Get model usage statistics
     * @param {string} projectId - Project ID
     * @param {object} timeRange - Time range for stats
     * @returns {Promise<object>} Usage statistics
     */
    getUsageStats: async (projectId, timeRange = {}) => {
        const response = await client.get(`/api/models/usage-stats/${projectId}`, {
            params: timeRange
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
        const response = await client.put(`/api/models/preferences/${projectId}`, preferences);
        return response.data;
    },

    /**
     * Get real-time model status (availability, latency, etc.)
     * @returns {Promise<object>} Model status information
     */
    getModelStatus: async () => {
        const response = await client.get('/api/models/status');
        return response.data;
    }
};

export default modelsAPI;
