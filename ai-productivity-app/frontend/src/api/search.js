// api/search.js
import axios from '../utils/axios';
// Type imports removed (SearchOptions, SearchResults, DocumentMatch, KnowledgeSource)

class SearchAPI {
  constructor() {
    this._baseURL = '/api';
  }

  /**
   * Search documents in the knowledge base
   * @param {string} projectId
   * @param {object} options
   * @param {AbortSignal} [signal]
   * @returns {Promise<object>}
   */
  async searchDocuments(projectId, options, signal) {
    const response = await axios.post(
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
    const response = await axios.post(
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
    const response = await axios.post(
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
    const response = await axios.post(
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
    const response = await axios.get(
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
    const response = await axios.post(
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
    const response = await axios.patch(
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
    await axios.delete(
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
    const response = await axios.get(
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
    const response = await axios.get(
      `${this._baseURL}/projects/${projectId}/search/facets`
    );
    return response.data;
  }

  /**
   * Reindex all content for a project
   * @param {string} projectId
   * @returns {Promise<{ status: string, jobId: string }>}
   */
  async reindexProject(projectId) {
    const response = await axios.post(
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
    const response = await axios.get(
      `${this._baseURL}/projects/${projectId}/knowledge/status`,
      { params: { jobId } }
    );
    return response.data;
  }
}

export const searchAPI = new SearchAPI();
