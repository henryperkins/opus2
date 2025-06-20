/* eslint-disable */
// api/analytics.js
// Analytics and metrics tracking API

import client from './client';

export const analyticsAPI = {
    /**
     * Track response quality metrics
     * @param {object} metrics - Quality metrics data
     * @returns {Promise<object>} Tracking confirmation
     */
    trackQuality: async (metrics) => {
        const response = await client.post('/api/analytics/quality', metrics);
        return response.data;
    },

    /**
     * Record user feedback on responses
     * @param {string} responseId - Response identifier
     * @param {object} feedback - User feedback data
     * @returns {Promise<object>} Feedback confirmation
     */
    recordFeedback: async (responseId, feedback) => {
        const response = await client.post(`/api/analytics/feedback/${responseId}`, feedback);
        return response.data;
    },

    /**
     * Get quality metrics for a project
     * @param {string} projectId - Project ID
     * @param {object} timeRange - Time range for metrics
     * @returns {Promise<object>} Quality metrics
     */
    getQualityMetrics: async (projectId, timeRange = {}) => {
        const response = await client.get(`/api/analytics/quality/${projectId}`, {
            params: timeRange
        });
        return response.data;
    },

    /**
     * Track flow performance metrics
     * @param {object} flowMetrics - Flow execution metrics
     * @returns {Promise<object>} Tracking confirmation
     */
    trackFlowMetrics: async (flowMetrics) => {
        const response = await client.post('/api/analytics/flow-metrics', flowMetrics);
        return response.data;
    },

    /**
     * Get flow performance analytics
     * @param {string} projectId - Project ID
     * @param {string} flowType - Type of flow (knowledge, model, rendering)
     * @returns {Promise<object>} Flow analytics
     */
    getFlowAnalytics: async (projectId, flowType) => {
        const response = await client.get(`/api/analytics/flows/${projectId}/${flowType}`);
        return response.data;
    },

    /**
     * Track user interactions with interactive elements
     * @param {object} interaction - Interaction data
     * @returns {Promise<object>} Tracking confirmation
     */
    trackInteraction: async (interaction) => {
        const response = await client.post('/api/analytics/interactions', interaction);
        return response.data;
    },

    /**
     * Get usage statistics dashboard data
     * @param {string} projectId - Project ID
     * @returns {Promise<object>} Dashboard metrics
     */
    getDashboardMetrics: async (projectId) => {
        const response = await client.get(`/api/analytics/dashboard/${projectId}`);
        return response.data;
    }
};

export default analyticsAPI;
