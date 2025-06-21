/* eslint-disable */
// api/knowledge.js
// Knowledge base and context management API

import client from './client';

export const knowledgeAPI = {
    /**
     * Analyze user query for intent, task type, and keywords
     * @param {string} query - User's input query
     * @param {string} projectId - Project context
     * @returns {Promise<object>} Analysis result with intent, taskType, complexity, keywords
     */
    analyzeQuery: async (query, projectId) => {
        const response = await client.post('/api/knowledge/analyze-query', {
            query,
            project_id: projectId
        });
        return response.data;
    },

    /**
     * Retrieve relevant knowledge from the knowledge base
     * @param {object} analysis - Query analysis result
     * @param {string} projectId - Project context
     * @param {object} settings - Knowledge retrieval settings
     * @returns {Promise<Array>} Array of knowledge documents with confidence scores
     */
    retrieveKnowledge: async (analysis, projectId, settings) => {
        const response = await client.post('/api/knowledge/retrieve', {
            analysis,
            project_id: projectId,
            max_docs: settings.maxContextDocs,
            min_confidence: settings.minConfidence,
            auto_context: settings.autoContext
        });
        return response.data;
    },

    /**
     * Inject context into query for better model understanding
     * @param {string} query - Original query
     * @param {Array} knowledge - Retrieved knowledge documents
     * @param {object} settings - Context injection settings
     * @returns {Promise<string>} Contextualized query
     */
    injectContext: async (query, knowledge, settings) => {
        const response = await client.post('/api/knowledge/inject-context', {
            query,
            knowledge,
            citation_style: settings.citationStyle,
            max_context_length: settings.maxContextDocs * 500 // rough estimate
        });
        return response.data.contextualized_query;
    },

    /**
     * Add citations to the model response
     * @param {object} response - Model response
     * @param {Array} knowledge - Knowledge sources used
     * @param {string} citationStyle - 'inline' or 'footnote'
     * @returns {Promise<object>} Response with citations added
     */
    addCitations: async (response, knowledge, citationStyle) => {
        const apiResponse = await client.post('/api/knowledge/add-citations', {
            response,
            knowledge,
            citation_style: citationStyle
        });
        return apiResponse.data;
    },

    /**
     * Get knowledge base statistics for a project
     * @param {string} projectId - Project ID
     * @returns {Promise<object>} Knowledge base stats
     */
    getKnowledgeStats: async (projectId) => {
        const response = await client.get(`/api/knowledge/stats/${projectId}`);
        return response.data;
    },

    /**
     * Search knowledge base with semantic similarity
     * @param {string} projectId - Project ID
     * @param {string} query - Search query
     * @param {object} options - Search options
     * @returns {Promise<Array>} Search results
     */
    semanticSearch: async (projectId, query, options = {}) => {
        const response = await client.post(`/api/knowledge/search/${projectId}`, {
            query,
            ...options
        });
        return response.data;
    },

    /**
     * Get knowledge base summary for a project
     * @param {string} projectId - Project ID
     * @returns {Promise<object>} Knowledge base summary
     */
    getSummary: async (projectId) => {
        const response = await client.get(`/api/knowledge/summary/${projectId}`);
        return response.data;
    }
};

export default knowledgeAPI;
