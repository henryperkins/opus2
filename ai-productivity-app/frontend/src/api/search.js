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
      // Use global search history since project-specific doesn't exist yet
      const response = await client.get('/api/search/history', {
        params: { limit: 10 }
      });
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
    // Return mock popular queries for now since backend endpoint doesn't exist
    return [
      { query: 'function definitions', count: 15 },
      { query: 'API endpoints', count: 12 },
      { query: 'error handling', count: 8 },
      { query: 'database models', count: 6 },
      { query: 'authentication', count: 4 }
    ];
  }

  // -----------------------------------------------------------------------
  // Global search across multiple projects (used by the new <SearchPage>)
  // -----------------------------------------------------------------------
  /**
   * Perform a global search across one or more projects.
   *
   * Expected payload structure (see useSearch hook):
   *   {
   *     query: string,
   *     project_ids?: number[],
   *     filters?: {
   *       language?: string,
   *       file_type?: string,
   *       symbol_type?: string,
   *       tags?: string[],
   *     },
   *     limit?: number,
   *     search_types?: string[]
   *   }
   *
   * The backend exposes POST /api/search endpoint that accepts the same body.
   */
  async search(options) {
    const response = await client.post(`${this._baseURL}/search`, options);
    return response.data;
  }

  /**
   * Smart search method (used by SmartKnowledgeSearch component)
   * @param {string} projectId
   * @param {object} options
   * @returns {Promise<object>}
   */
  async smartSearch(projectId, options) {
    const searchOptions = {
      query: options.query,
      project_ids: [parseInt(projectId)],
      limit: options.max_results || 20,
      filters: {
        language: options.language,
        file_type: options.type !== 'all' ? options.type : undefined
      },
      search_types: ['hybrid']
    };

    const response = await this.search(searchOptions);
    
    // Map backend field names to frontend expectations
    const mappedResults = response.results.map(result => ({
      ...result,
      path: result.file_path, // Map file_path to path
      highlights: result.content ? [result.content] : []
    }));

    return {
      ...response,
      results: mappedResults
    };
  }

  /**
   * Add search to history
   * @param {string} projectId
   * @param {string} query
   * @returns {Promise<void>}
   */
  async addToHistory(projectId, query) {
    // For now, just log - could be implemented to save local history
    console.log('Adding to search history:', { projectId, query });
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
