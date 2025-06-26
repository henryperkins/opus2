// contexts/KnowledgeContext.jsx
import { createContext, useContext, useReducer, useCallback, useEffect } from 'react';
import PropTypes from 'prop-types';

// Knowledge context for unified state management
const KnowledgeContext = createContext();

// Action types for knowledge state reducer
const KNOWLEDGE_ACTIONS = {
  SET_CITATIONS: 'SET_CITATIONS',
  ADD_CITATION: 'ADD_CITATION',
  REMOVE_CITATION: 'REMOVE_CITATION',
  CLEAR_CITATIONS: 'CLEAR_CITATIONS',
  SET_ACTIVE_QUERY: 'SET_ACTIVE_QUERY',
  SET_SEARCH_RESULTS: 'SET_SEARCH_RESULTS',
  SET_CONTEXT: 'SET_CONTEXT',
  SET_SELECTED_ITEMS: 'SET_SELECTED_ITEMS',
  ADD_SELECTED_ITEM: 'ADD_SELECTED_ITEM',
  REMOVE_SELECTED_ITEM: 'REMOVE_SELECTED_ITEM',
  SET_LOADING: 'SET_LOADING',
  SET_ERROR: 'SET_ERROR',
  SET_SUGGESTIONS: 'SET_SUGGESTIONS',
  CLEAR_SUGGESTIONS: 'CLEAR_SUGGESTIONS',
  RESET_ERROR: 'RESET_ERROR'
};

// Initial state for knowledge context
const initialState = {
  // Citations and context
  citations: [],
  currentContext: [],

  // Search state
  activeQuery: '',
  searchResults: [],
  searchHistory: [],

  // Selection state
  selectedItems: new Set(),

  // AI suggestions
  suggestions: [],
  suggestionContext: null,

  // UI state
  loading: false,
  error: null,

  // Panel state
  isVisible: true,
  isMinimized: false
};

// Reducer for knowledge state management
function knowledgeReducer(state, action) {
  switch (action.type) {
    case KNOWLEDGE_ACTIONS.SET_CITATIONS:
      return {
        ...state,
        citations: action.payload,
        error: null
      };

    case KNOWLEDGE_ACTIONS.ADD_CITATION: {
      const newCitations = [...state.citations];
      const existingIndex = newCitations.findIndex(c => c.id === action.payload.id);
      if (existingIndex >= 0) {
        newCitations[existingIndex] = action.payload;
      } else {
        newCitations.push(action.payload);
      }
      return {
        ...state,
        citations: newCitations,
        error: null
      };
    }

    case KNOWLEDGE_ACTIONS.REMOVE_CITATION:
      return {
        ...state,
        citations: state.citations.filter(c => c.id !== action.payload),
        error: null
      };

    case KNOWLEDGE_ACTIONS.CLEAR_CITATIONS:
      return {
        ...state,
        citations: [],
        currentContext: [],
        selectedItems: new Set(),
        error: null
      };

    case KNOWLEDGE_ACTIONS.SET_ACTIVE_QUERY:
      return {
        ...state,
        activeQuery: action.payload,
        searchHistory: action.payload && !state.searchHistory.includes(action.payload)
          ? [action.payload, ...state.searchHistory.slice(0, 9)] // Keep last 10
          : state.searchHistory,
        error: null
      };

    case KNOWLEDGE_ACTIONS.SET_SEARCH_RESULTS:
      return {
        ...state,
        searchResults: action.payload,
        error: null
      };

    case KNOWLEDGE_ACTIONS.SET_CONTEXT:
      return {
        ...state,
        currentContext: action.payload,
        error: null
      };

    case KNOWLEDGE_ACTIONS.SET_SELECTED_ITEMS:
      return {
        ...state,
        selectedItems: new Set(action.payload),
        error: null
      };

    case KNOWLEDGE_ACTIONS.ADD_SELECTED_ITEM: {
      const newSelected = new Set(state.selectedItems);
      newSelected.add(action.payload);
      return {
        ...state,
        selectedItems: newSelected,
        error: null
      };
    }

    case KNOWLEDGE_ACTIONS.REMOVE_SELECTED_ITEM: {
      const filteredSelected = new Set(state.selectedItems);
      filteredSelected.delete(action.payload);
      return {
        ...state,
        selectedItems: filteredSelected,
        error: null
      };
    }

    case KNOWLEDGE_ACTIONS.SET_LOADING:
      return {
        ...state,
        loading: action.payload
      };

    case KNOWLEDGE_ACTIONS.SET_ERROR:
      return {
        ...state,
        error: action.payload,
        loading: false
      };

    case KNOWLEDGE_ACTIONS.SET_SUGGESTIONS:
      return {
        ...state,
        suggestions: action.payload.suggestions || [],
        suggestionContext: action.payload.context || null,
        error: null
      };

    case KNOWLEDGE_ACTIONS.CLEAR_SUGGESTIONS:
      return {
        ...state,
        suggestions: [],
        suggestionContext: null
      };

    case KNOWLEDGE_ACTIONS.RESET_ERROR:
      return {
        ...state,
        error: null
      };

    default:
      return state;
  }
}

// KnowledgeProvider component
export function KnowledgeProvider({ children }) {
  const [state, dispatch] = useReducer(knowledgeReducer, initialState);

  // Add citation to knowledge context
  const addToCitations = useCallback((citations) => {
    try {
      if (Array.isArray(citations)) {
        citations.forEach(citation => {
          if (citation && citation.id) {
            dispatch({ type: KNOWLEDGE_ACTIONS.ADD_CITATION, payload: citation });
          }
        });
      } else if (citations && citations.id) {
        dispatch({ type: KNOWLEDGE_ACTIONS.ADD_CITATION, payload: citations });
      }
    } catch (error) {
      console.error('Failed to add citations:', error);
      dispatch({ type: KNOWLEDGE_ACTIONS.SET_ERROR, payload: error.message });
    }
  }, []);

  // Remove citation from knowledge context
  const removeCitation = useCallback((citationId) => {
    try {
      dispatch({ type: KNOWLEDGE_ACTIONS.REMOVE_CITATION, payload: citationId });
    } catch (error) {
      console.error('Failed to remove citation:', error);
      dispatch({ type: KNOWLEDGE_ACTIONS.SET_ERROR, payload: error.message });
    }
  }, []);

  // Clear all citations
  const clearCitations = useCallback(() => {
    dispatch({ type: KNOWLEDGE_ACTIONS.CLEAR_CITATIONS });
  }, []);

  // Set active search query
  const setActiveQuery = useCallback((query) => {
    dispatch({ type: KNOWLEDGE_ACTIONS.SET_ACTIVE_QUERY, payload: query });
  }, []);

  // Update search results
  const setSearchResults = useCallback((results) => {
    dispatch({ type: KNOWLEDGE_ACTIONS.SET_SEARCH_RESULTS, payload: results });
  }, []);

  // Build context from current citations and selected items
  const buildContext = useCallback(() => {
    try {
      const context = [];
      const seen = new Map(); // key -> context object (prevents duplicates)

      // 1. Citations coming back from backend (already scored)
      state.citations.forEach((c) => {
        if (!c) return;
        const key = c.id || c.source || `${c.file_path}-${c.line_start}`;
        if (seen.has(key)) return;

        const ctxItem = {
          id: c.id,
          type: c.type || 'document',
          content: c.content || c.excerpt || c.code,
          source: c.source || c.file_path || c.filename,
          language: c.language,
          relevance: c.relevance ?? c.score ?? 0.8,
          metadata: { ...c.metadata },
        };
        seen.set(key, ctxItem);
        context.push(ctxItem);
      });

      // 2. User-selected search results
      state.selectedItems.forEach((itemId) => {
        const item = state.searchResults.find((r) => r.id === itemId);
        if (!item) return;
        const key = item.id || item.source;
        if (seen.has(key)) return;

        const ctxItem = {
          id: item.id,
          type: item.type || 'document',
          content: item.content || item.excerpt,
          source: item.source || item.filename,
          language: item.language,
          relevance: item.relevance ?? item.score ?? 0.7,
          metadata: { ...item.metadata },
        };
        seen.set(key, ctxItem);
        context.push(ctxItem);
      });

      // 3. Sort descending by relevance so the most important snippets appear first
      context.sort((a, b) => (b.relevance || 0) - (a.relevance || 0));

      dispatch({ type: KNOWLEDGE_ACTIONS.SET_CONTEXT, payload: context });
      return context;
    } catch (error) {
      console.error('Failed to build context:', error);
      dispatch({ type: KNOWLEDGE_ACTIONS.SET_ERROR, payload: error.message });
      return [];
    }
  }, [state.citations, state.selectedItems, state.searchResults]);

  // Analyze message and generate suggestions
  const analyzeMessage = useCallback(async (message, projectId) => {
    try {
      dispatch({ type: KNOWLEDGE_ACTIONS.SET_LOADING, payload: true });

      // This would typically call an API endpoint
      // For now, we'll simulate the analysis
      const mockSuggestions = [];

      if (message.toLowerCase().includes('error') || message.toLowerCase().includes('bug')) {
        mockSuggestions.push('Check error logs and stack traces');
        mockSuggestions.push('Review recent code changes');
      }

      if (message.toLowerCase().includes('implement') || message.toLowerCase().includes('add')) {
        mockSuggestions.push('Search for similar implementations');
        mockSuggestions.push('Review architectural patterns');
      }

      dispatch({
        type: KNOWLEDGE_ACTIONS.SET_SUGGESTIONS,
        payload: {
          suggestions: mockSuggestions,
          context: { message, projectId, timestamp: new Date().toISOString() }
        }
      });

    } catch (error) {
      console.error('Failed to analyze message:', error);
      dispatch({ type: KNOWLEDGE_ACTIONS.SET_ERROR, payload: error.message });
    } finally {
      dispatch({ type: KNOWLEDGE_ACTIONS.SET_LOADING, payload: false });
    }
  }, []);

  // Clear suggestions
  const clearSuggestions = useCallback(() => {
    dispatch({ type: KNOWLEDGE_ACTIONS.CLEAR_SUGGESTIONS });
  }, []);

  // Select/deselect items
  const toggleSelectedItem = useCallback((itemId) => {
    if (state.selectedItems.has(itemId)) {
      dispatch({ type: KNOWLEDGE_ACTIONS.REMOVE_SELECTED_ITEM, payload: itemId });
    } else {
      dispatch({ type: KNOWLEDGE_ACTIONS.ADD_SELECTED_ITEM, payload: itemId });
    }
  }, [state.selectedItems]);

  // Clear selected items
  const clearSelectedItems = useCallback(() => {
    dispatch({ type: KNOWLEDGE_ACTIONS.SET_SELECTED_ITEMS, payload: [] });
    // ensure context rebuilds immediately
    buildContext();
  }, [buildContext]);

  // Reset error state
  const resetError = useCallback(() => {
    dispatch({ type: KNOWLEDGE_ACTIONS.RESET_ERROR });
  }, []);

  // Auto-build context when citations or selected items change
  useEffect(() => {
    buildContext();
  }, [buildContext]);

  // Context value
  const value = {
    // State
    citations: state.citations,
    currentContext: state.currentContext,
    activeQuery: state.activeQuery,
    searchResults: state.searchResults,
    searchHistory: state.searchHistory,
    selectedItems: state.selectedItems,
    suggestions: state.suggestions,
    suggestionContext: state.suggestionContext,
    loading: state.loading,
    error: state.error,
    isVisible: state.isVisible,
    isMinimized: state.isMinimized,

    // Actions
    addToCitations,
    removeCitation,
    clearCitations,
    setActiveQuery,
    setSearchResults,
    buildContext,
    analyzeMessage,
    clearSuggestions,
    toggleSelectedItem,
    clearSelectedItems,
    resetError
  };

  return (
    <KnowledgeContext.Provider value={value}>
      {children}
    </KnowledgeContext.Provider>
  );
}

// PropTypes validation
KnowledgeProvider.propTypes = {
  children: PropTypes.node.isRequired
};

// Hook to use knowledge context
// eslint-disable-next-line react-refresh/only-export-components
export function useKnowledgeContext() {
  const context = useContext(KnowledgeContext);
  if (!context) {
    throw new Error('useKnowledgeContext must be used within a KnowledgeProvider');
  }
  return context;
}

// Export for easier imports
// eslint-disable-next-line react-refresh/only-export-components
export { KnowledgeContext, KNOWLEDGE_ACTIONS };
