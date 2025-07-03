// api/analytics.js
// Enhanced analytics and metrics tracking API with offline support

import client from './client';

// Enhanced analytics service with persistence and offline support
class AnalyticsService {
    constructor() {
        this.pendingMetrics = [];
        this.flushInterval = 5000; // 5 seconds
        this.batchSize = 10;
        this.isOnline = navigator.onLine;
        
        this.loadPendingMetrics();
        this.startPeriodicFlush();
        this.setupConnectivityHandlers();
    }

    // Load pending metrics from localStorage
    loadPendingMetrics() {
        try {
            const stored = localStorage.getItem('pendingAnalytics') || '[]';
            const metrics = JSON.parse(stored);
            
            // Only load recent metrics (last 24 hours)
            const dayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
            this.pendingMetrics = metrics.filter(m => new Date(m.timestamp) > dayAgo);
        } catch (e) {
            console.error('Failed to load pending analytics:', e);
            this.pendingMetrics = [];
        }
    }

    // Store metric locally for offline resilience
    storeLocally(metric) {
        try {
            const stored = localStorage.getItem('pendingAnalytics') || '[]';
            const metrics = JSON.parse(stored);
            metrics.push(metric);

            // Keep only last 100 metrics
            if (metrics.length > 100) {
                metrics.splice(0, metrics.length - 100);
            }

            localStorage.setItem('pendingAnalytics', JSON.stringify(metrics));
        } catch (e) {
            console.error('Failed to store analytics locally:', e);
        }
    }

    // Add metric to queue and optionally flush
    async queueMetric(metric) {
        const enrichedMetric = {
            ...metric,
            timestamp: new Date().toISOString(),
            sessionId: this.getSessionId(),
            userId: this.getUserId()
        };

        this.pendingMetrics.push(enrichedMetric);
        this.storeLocally(enrichedMetric);

        // Flush if batch size reached or if online
        if (this.pendingMetrics.length >= this.batchSize || this.isOnline) {
            await this.flush();
        }
    }

    // Flush pending metrics to server
    async flush() {
        if (this.pendingMetrics.length === 0 || !this.isOnline) return;

        const metricsToSend = [...this.pendingMetrics];
        this.pendingMetrics = [];

        try {
            await client.post('/api/analytics/batch', {
                metrics: metricsToSend,
                metadata: {
                    count: metricsToSend.length,
                    sessionId: this.getSessionId(),
                    timestamp: new Date().toISOString()
                }
            });

            // Clear sent metrics from localStorage
            this.clearLocalMetrics(metricsToSend);
        } catch (error) {
            console.error('Failed to send analytics:', error);
            // Re-add metrics to pending on failure
            this.pendingMetrics.unshift(...metricsToSend);
        }
    }

    clearLocalMetrics(sentMetrics) {
        try {
            const stored = localStorage.getItem('pendingAnalytics') || '[]';
            const metrics = JSON.parse(stored);
            const sentIds = new Set(sentMetrics.map(m => m.timestamp));
            const remaining = metrics.filter(m => !sentIds.has(m.timestamp));
            localStorage.setItem('pendingAnalytics', JSON.stringify(remaining));
        } catch (e) {
            console.error('Failed to clear local metrics:', e);
        }
    }

    startPeriodicFlush() {
        setInterval(() => {
            if (this.isOnline) this.flush();
        }, this.flushInterval);

        // Flush on page unload
        window.addEventListener('beforeunload', () => this.flush());
    }

    setupConnectivityHandlers() {
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.flush(); // Flush when back online
        });

        window.addEventListener('offline', () => {
            this.isOnline = false;
        });
    }

    getSessionId() {
        let sessionId = sessionStorage.getItem('analyticsSessionId');
        if (!sessionId) {
            sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            sessionStorage.setItem('analyticsSessionId', sessionId);
        }
        return sessionId;
    }

    getUserId() {
        // Try to get user ID from auth context or storage
        if (window.__USER_ID__) return window.__USER_ID__;
        
        try {
            const authData = localStorage.getItem('authData') || sessionStorage.getItem('authData');
            if (authData) {
                const parsed = JSON.parse(authData);
                return parsed.user?.id || parsed.userId;
            }
        } catch (e) {
            // Ignore parsing errors
        }
        
        return null;
    }
}

// Create singleton instance
const analyticsService = new AnalyticsService();

export const analyticsAPI = {
    /**
     * Track response quality metrics with offline support
     * @param {object} metrics - Quality metrics data
     * @returns {Promise<object>} Tracking confirmation
     */
    trackQuality: async (metrics) => {
        const enrichedMetrics = {
            ...metrics,
            type: 'response_quality',
            responseTime: metrics.responseTime || performance.now(),
            model: metrics.model || 'unknown'
        };

        // Use persistent service for better reliability
        await analyticsService.queueMetric(enrichedMetrics);
        
        // Also try direct API call if online
        if (analyticsService.isOnline) {
            try {
                const response = await client.post('/api/analytics/quality', enrichedMetrics);
                return response.data;
            } catch (error) {
                console.warn('Direct quality tracking failed, queued for later:', error);
                return { status: 'queued', error: error.message };
            }
        }
        
        return { status: 'queued' };
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
     * Get embedding processing metrics from Prometheus
     * @returns {Promise<object>} Embedding metrics data
     */
    getEmbeddingMetrics: async () => {
        const response = await client.get('/api/analytics/embedding-metrics');
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
