// hooks/useKnowledgeContext.js
import { useState, useEffect, useCallback, useRef } from 'react';
import { searchAPI } from '../api/search';
import { useDebounce } from './useDebounce';

/**
 * Hook for managing knowledge base context and search
 * @param {object} options - Configuration options
 * @param {string} options.projectId - Project ID
 * @param {boolean} options.autoSearch - Whether to auto-search on query changes
 * @param {number} options.searchDelay - Debounce delay for searches
 * @param {number} options.maxResults - Maximum number of results
 * @param {number} options.minConfidence - Minimum confidence threshold
 * @returns {object} Knowledge context state and functions
 */
export function useKnowledgeContext({
  projectId,
  autoSearch = true,
  searchDelay = 300,
  maxResults = 10,
  minConfidence = 0.5
}) {
  const [context, setContext] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [citations, setCitations] = useState([]);
  const [selectedItems, setSelectedItems] = useState(new Set());

  const searchAbortController = useRef(null);
  const citationCounter = useRef(1);

  const debouncedQuery = useDebounce(searchQuery, searchDelay);

  // Perform knowledge search
  const performSearch = useCallback(async (query) => {
    if (!query || query.length < 3) {
      setContext(null);
      return;
    }

    // Cancel previous search
    if (searchAbortController.current) {
      searchAbortController.current.abort();
    }

    searchAbortController.current = new window.AbortController();

    setLoading(true);
    setError(null);

    try {
      const startTime = Date.now();

      // Parallel search for documents and code
      const [docsResponse, codeResponse] = await Promise.all([
        searchAPI.searchDocuments(projectId, {
          query,
          limit: Math.floor(maxResults / 2),
          threshold: minConfidence
        }, searchAbortController.current.signal),
        searchAPI.searchCode(projectId, {
          query,
          limit: Math.floor(maxResults / 2),
          threshold: minConfidence
        }, searchAbortController.current.signal)
      ]);

      const searchTime = Date.now() - startTime;

      // Calculate overall confidence
      const allScores = [
        ...(docsResponse.results || []).map(d => d.score),
        ...(codeResponse.results || []).map(c => c.score)
      ];

      const avgScore = allScores.length > 0
        ? allScores.reduce((a, b) => a + b, 0) / allScores.length
        : 0;

      const newContext = {
        relevantDocs: (docsResponse.results || []).map(doc => ({
          ...doc,
          type: doc.type || 'document'
        })),
        codeSnippets: (codeResponse.results || []).map(r => ({
          id: r.id,
          documentId: r.documentId || r.id,
          content: r.content,
          file_path: r.file_path || r.path,
          start_line: r.start_line || 1,
          end_line: r.end_line || r.content.split('\n').length,
          language: r.language || 'text',
          score: r.score
        })),
        totalMatches: (docsResponse.total || 0) + (codeResponse.total || 0),
        searchTime,
        confidence: avgScore
      };

      setContext(newContext);
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError('Failed to search knowledge base');
        console.error('Knowledge search error:', err);
      }
    } finally {
      setLoading(false);
    }
  }, [projectId, maxResults, minConfidence]);

  // Auto-search effect
  useEffect(() => {
    if (autoSearch && debouncedQuery) {
      performSearch(debouncedQuery);
    }
  }, [debouncedQuery, autoSearch, performSearch]);

  // Manual search function
  const search = useCallback(async (query) => {
    setSearchQuery(query);
    if (!autoSearch) {
      await performSearch(query);
    }
  }, [autoSearch, performSearch]);

  // Clear context
  const clearContext = useCallback(() => {
    setContext(null);
    setSearchQuery('');
    setError(null);
    if (searchAbortController.current) {
      searchAbortController.current.abort();
    }
  }, []);

  // Add items to citations
  const addToCitations = useCallback((items) => {
    const newCitations = items.map(item => {
      const isDoc = 'title' in item;
      return {
        id: item.id,
        number: citationCounter.current++,
        source: {
          id: item.id,
          title: isDoc ? item.title : `Code snippet`,
          path: isDoc ? item.path : (item.file_path || 'code'),
          type: isDoc
            ? (item.type === "comment" ? "external" : item.type)
            : "code"
        },
        content: item.content.slice(0, 200),
        confidence: item.score || 0.8
      };
    });

    setCitations(prev => [...prev, ...newCitations]);
    return newCitations;
  }, []);

  // Toggle item selection
  const toggleItemSelection = useCallback((itemId) => {
    setSelectedItems(prev => {
      const newSet = new Set(prev);
      if (newSet.has(itemId)) {
        newSet.delete(itemId);
      } else {
        newSet.add(itemId);
      }
      return newSet;
    });
  }, []);

  // Clear all selections
  const clearSelections = useCallback(() => {
    setSelectedItems(new Set());
  }, []);

  // Get selected items from context
  const getSelectedItemsFromContext = useCallback(() => {
    if (!context) return [];

    const items = [];

    context.relevantDocs.forEach(doc => {
      if (selectedItems.has(doc.id)) {
        items.push(doc);
      }
    });

    context.codeSnippets.forEach(snippet => {
      if (selectedItems.has(snippet.id)) {
        items.push(snippet);
      }
    });

    return items;
  }, [context, selectedItems]);

  return {
    context,
    loading,
    error,
    search,
    clearContext,
    addToCitations,
    citations,
    selectedItems,
    toggleItemSelection,
    clearSelections,
    getSelectedItemsFromContext
  };
}

/**
 * Helper hook for integrating knowledge context with chat
 * @param {string} projectId - Project ID
 * @returns {object} Enhanced knowledge context with chat integration
 */
export function useKnowledgeChat(projectId) {
  const knowledgeContext = useKnowledgeContext({ projectId });
  const [activeQuery, setActiveQuery] = useState('');

  // Update search based on chat input
  const updateContextFromChat = useCallback((message) => {
    // Extract meaningful search terms from message
    const searchTerms = extractSearchTerms(message);
    if (searchTerms && searchTerms !== activeQuery) {
      setActiveQuery(searchTerms);
      knowledgeContext.search(searchTerms);
    }
  }, [knowledgeContext, activeQuery]);

  // Build enhanced message with context
  const buildEnhancedMessage = useCallback((message) => {
    const metadata = {};

    // Add citations if any
    if (knowledgeContext.citations.length > 0) {
      metadata.citations = knowledgeContext.citations;
    }

    // Add context summary if available
    if (knowledgeContext.context) {
      metadata.contextSummary = {
        documentsFound: knowledgeContext.context.relevantDocs.length,
        codeSnippetsFound: knowledgeContext.context.codeSnippets.length,
        confidence: knowledgeContext.context.confidence
      };
    }

    return { message, metadata };
  }, [knowledgeContext]);

  return {
    ...knowledgeContext,
    updateContextFromChat,
    buildEnhancedMessage,
    activeQuery
  };
}

/**
 * Helper function to extract search terms from a message
 * @param {string} message - Chat message
 * @returns {string} Extracted search terms
 */
function extractSearchTerms(message) {
  // Remove common chat words and extract meaningful terms
  const stopWords = new Set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'how', 'what', 'when', 'where', 'why', 'can', 'could', 'should', 'would', 'i', 'you', 'we', 'they', 'it', 'this', 'that', 'these', 'those']);

  const words = message
    .toLowerCase()
    .replace(/[^\w\s]/g, ' ')
    .split(/\s+/)
    .filter(word => word.length > 2 && !stopWords.has(word));

  // Take first 3-5 meaningful words
  return words.slice(0, 5).join(' ');
}
