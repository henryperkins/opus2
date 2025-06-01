// Unified search API client for semantic and keyword search
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

  async getDependencyGraph(projectId) {
    const response = await client.get(`/api/projects/${projectId}/dependency-graph`);
    return response.data;
  }
};
