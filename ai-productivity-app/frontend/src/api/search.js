// frontend/src/api/search.js
import client from './client';

export const searchAPI = {
  async search(params) {
    const response = await client.post('/api/search', params);
    return response.data;
  },

  async getSuggestions(query) {
    const response = await client.get('/api/search/suggestions', {
      params: { q: query }
    });
    return response.data;
  },

  async getHistory(limit = 20) {
    const response = await client.get('/api/search/history', {
      params: { limit }
    });
    return response.data;
  },

  async indexDocument(documentId, options = {}) {
    const response = await client.post('/api/search/index', {
      document_id: documentId,
      ...options
    });
    return response.data;
  },

  async deleteIndex(documentId) {
    const response = await client.delete(`/api/search/index/${documentId}`);
    return response.data;
  },

  async getDependencyGraph(projectId) {
    const response = await client.get(`/api/projects/${projectId}/dependency-graph`);
    return response.data;
  }
};
