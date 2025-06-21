// api/search.js
import client from './client';
// Type imports removed (SearchOptions, SearchResults, DocumentMatch, KnowledgeSource)

class SearchAPI {
  constructor() {
    // Base URL is already set in client.js, we just need the API path
    this._baseURL = 'api';
  }

  /**
   * Search documents in the knowledge base
   * @param {string} projectId
   * @param {object} options
   * @param {AbortSignal} [signal]
   * @returns {Promise<object>}
   */
  async searchDocuments(projectId, options, signal) {
    const response = await client.post(
      `${this._baseURL}/projects/${projectId}/search/documents`,
      options,
      { signal }
    );
    return response.data;
  }

  /**
   * Search code in the knowledge base
   * @param {string} projectId
   * @param {object} options
   * @param {AbortSignal} [signal]
   * @returns {Promise<object>}
   */
  async searchCode(projectId, options, signal) {
    const response = await client.post(
      `${this._baseURL}/projects/${projectId}/search/code`,
      options,
      { signal }
    );
    return response.data;
  }

  /**
   * Hybrid search across all content types
   * @param {string} projectId
   * @param {object} options
   * @param {AbortSignal} [signal]
   * @returns {Promise<object>}
   */
  async hybridSearch(projectId, options, signal) {
    const response = await client.post(
      `${this._baseURL}/projects/${projectId}/search/hybrid`,
      options,
      { signal }
    );
    return response.data;
  }

  /**
   * Find similar content based on a text sample
   * @param {string} projectId
   * @param {object} options - { content: string, type?: 'all'|'code'|'docs', limit?: number, threshold?: number }
   * @param {AbortSignal} [signal]
   * @returns {Promise<{ items: Array, total: number }>}
   */
  async findSimilar(projectId, options, signal) {
    const response = await client.post(
      `${this._baseURL}/projects/${projectId}/search/similar`,
      options,
      { signal }
    );
    return response.data;
  }

  /**
   * Get document by ID
   * @param {string} projectId
   * @param {string} documentId
   * @returns {Promise<object>}
   */
  async getDocument(projectId, documentId) {
    const response = await client.get(
      `${this._baseURL}/projects/${projectId}/documents/${documentId}`
    );
    return response.data;
  }

  /**
   * Index new content
   * @param {string} projectId
   * @param {object} content - { type: 'document'|'code'|'comment', title: string, path: string, content: string, metadata?: object }
   * @returns {Promise<{ id: string, status: string }>}
   */
  async indexContent(projectId, content) {
    const response = await client.post(
      `${this._baseURL}/projects/${projectId}/knowledge/index`,
      content
    );
    return response.data;
  }

  /**
   * Update existing document
   * @param {string} projectId
   * @param {string} documentId
   * @param {object} updates
   * @returns {Promise<object>}
   */
  async updateDocument(projectId, documentId, updates) {
    const response = await client.patch(
      `${this._baseURL}/projects/${projectId}/documents/${documentId}`,
      updates
    );
    return response.data;
  }

  /**
   * Delete document from knowledge base
   * @param {string} projectId
   * @param {string} documentId
   * @returns {Promise<void>}
   */
  async deleteDocument(projectId, documentId) {
    await client.delete(
      `${this._baseURL}/projects/${projectId}/documents/${documentId}`
    );
  }

  /**
   * Get search suggestions based on partial query
   * @param {string} projectId
   * @param {string} query
   * @param {number} [limit=5]
   * @returns {Promise<Array<string>>}
   */
  async getSuggestions(projectId, query, limit = 5) {
    const response = await client.get(
      `${this._baseURL}/projects/${projectId}/search/suggestions`,
      { params: { q: query, limit } }
    );
    return response.data.suggestions;
  }

  /**
   * Get search facets for filtering
   * @param {string} projectId
   * @returns {Promise<object>}
   */
  async getFacets(projectId) {
    const response = await client.get(
      `${this._baseURL}/projects/${projectId}/search/facets`
    );
    return response.data;
  }

  /**
   * Fetch global search history (most recent queries)
   * @param {number} [limit=100]
   * @returns {Promise<Array<{ id: string, query: string, ts: string }>>}
   */
  async getHistory(limit = 100) {
    const response = await client.get('/api/search/history', {
      params: { limit },
    });
    return response.data;
  }

  /**
   * Reindex all content for a project
   * @param {string} projectId
   * @returns {Promise<{ status: string, jobId: string }>}
   */
  async reindexProject(projectId) {
    const response = await client.post(
      `${this._baseURL}/projects/${projectId}/knowledge/reindex`
    );
    return response.data;
  }

  /**
   * Get indexing status
   * @param {string} projectId
   * @param {string} [jobId]
   * @returns {Promise<object>}
   */
  async getIndexingStatus(projectId, jobId) {
    const response = await client.get(
      `${this._baseURL}/projects/${projectId}/knowledge/status`,
      { params: { jobId } }
    );
    return response.data;
  }

  /**
   * Get search history for a project
   * @param {string} projectId
   * @returns {Promise<Array<string>>}
   */
  async getSearchHistory(projectId) {
    try {
      const response = await client.get(
        `${this._baseURL}/projects/${projectId}/search/history`
      );
      return response.data.history || [];
    } catch (error) {
      console.warn('Search history not available:', error);
      return [];
    }
  }

  /**
   * Get popular search queries for a project
   * @param {string} projectId
   * @returns {Promise<Array<string>>}
   */
  async getPopularQueries(projectId) {
    try {
      const response = await client.get(
        `${this._baseURL}/projects/${projectId}/search/popular`
      );
      return response.data.queries || [];
    } catch (error) {
      console.warn('Popular queries not available:', error);
      return [];
    }
  }

  /**
   * Search project content (legacy method for backward compatibility)
   * @param {string} projectId
   * @param {string} query
   * @param {object} options
   * @returns {Promise<object>}
   */
  async searchProject(projectId, query, options = {}) {
    const searchOptions = {
      query,
      limit: options.max_results || 10,
      threshold: options.min_score || 0.5,
      ...options
    };

    try {
      // Use hybrid search as fallback
      return await this.hybridSearch(projectId, searchOptions);
    } catch (error) {
      console.error('Search failed:', error);
      return {
        documents: [],
        code_snippets: [],
        total: 0,
        results: []
      };
    }
  }
}

export const searchAPI = new SearchAPI();
