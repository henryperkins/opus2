// hooks/useKnowledgeContext.ts
import { useState, useEffect, useCallback, useRef } from 'react';
import { searchAPI } from '../api/search';
import { KnowledgeContext, DocumentMatch, CodeChunk, Citation } from '../types/knowledge';
import { useDebounce } from './useDebounce';

interface UseKnowledgeContextOptions {
  projectId: string;
  autoSearch?: boolean;
  searchDelay?: number;
  maxResults?: number;
  minConfidence?: number;
}

interface UseKnowledgeContextReturn {
  context: KnowledgeContext | null;
  loading: boolean;
  error: string | null;
  search: (query: string) => Promise<void>;
  clearContext: () => void;
  addToCitations: (items: DocumentMatch[] | CodeChunk[]) => Citation[];
  citations: Citation[];
  selectedItems: Set<string>;
  toggleItemSelection: (itemId: string) => void;
  clearSelections: () => void;
}

export function useKnowledgeContext({
  projectId,
  autoSearch = true,
  searchDelay = 300,
  maxResults = 10,
  minConfidence = 0.5
}: UseKnowledgeContextOptions): UseKnowledgeContextReturn {
  const [context, setContext] = useState<KnowledgeContext | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [citations, setCitations] = useState<Citation[]>([]);
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());

  const searchAbortController = useRef<AbortController | null>(null);
  const citationCounter = useRef(1);

  const debouncedQuery = useDebounce(searchQuery, searchDelay);

  // Perform knowledge search
  const performSearch = useCallback(async (query: string) => {
    if (!query || query.length < 3) {
      setContext(null);
      return;
    }

    // Cancel previous search
    if (searchAbortController.current) {
      searchAbortController.current.abort();
    }

    searchAbortController.current = new AbortController();

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
        ...docsResponse.results.map(d => d.score),
        ...codeResponse.results.map(c => c.score)
      ];

      const avgScore = allScores.length > 0
        ? allScores.reduce((a, b) => a + b, 0) / allScores.length
        : 0;

      const newContext: KnowledgeContext = {
        relevantDocs: docsResponse.results,
        codeSnippets: codeResponse.results.map(r => ({
          id: r.id,
          documentId: r.documentId || r.id,
          content: r.content,
          start_line: r.start_line || 1,
          end_line: r.end_line || r.content.split('\n').length,
          type: 'other' as const,
          score: r.score
        })),
        totalMatches: docsResponse.total + codeResponse.total,
        searchTime,
        confidence: avgScore
      };

      setContext(newContext);
    } catch (err: any) {
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
  const search = useCallback(async (query: string) => {
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
  const addToCitations = useCallback((items: (DocumentMatch | CodeChunk)[]): Citation[] => {
    const newCitations: Citation[] = items.map(item => {
      const isDoc = 'title' in item;
      return {
        id: item.id,
        number: citationCounter.current++,
        source: {
          title: isDoc ? (item as DocumentMatch).title : `Code snippet`,
          path: isDoc ? (item as DocumentMatch).path : 'code',
          type: isDoc
            ? ((item as DocumentMatch).type === "comment"
                ? "external"
                : (item as DocumentMatch).type as "document" | "code" | "external")
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
  const toggleItemSelection = useCallback((itemId: string) => {
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
  const getSelectedItemsFromContext = useCallback((): (DocumentMatch | CodeChunk)[] => {
    if (!context) return [];

    const items: (DocumentMatch | CodeChunk)[] = [];

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
    clearSelections
  };
}

// Helper hook for integrating knowledge context with chat
export function useKnowledgeChat(projectId: string) {
  const knowledgeContext = useKnowledgeContext({ projectId });
  const [activeQuery, setActiveQuery] = useState('');

  // Update search based on chat input
  const updateContextFromChat = useCallback((message: string) => {
    // Extract meaningful search terms from message
    // This is a simple implementation - could be enhanced with NLP
    const searchTerms = extractSearchTerms(message);
    if (searchTerms && searchTerms !== activeQuery) {
      setActiveQuery(searchTerms);
      knowledgeContext.search(searchTerms);
    }
  }, [knowledgeContext, activeQuery]);

  // Build enhanced message with context
  const buildEnhancedMessage = useCallback((message: string): {
    message: string;
    metadata: any;
  } => {
    const metadata: any = {};

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

// Helper function to extract search terms
function extractSearchTerms(message: string): string {
  // Remove common words and extract key terms
  const stopWords = new Set([
    'the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or', 'but',
    'in', 'with', 'to', 'for', 'of', 'as', 'by', 'that', 'this',
    'what', 'how', 'why', 'when', 'where', 'who'
  ]);

  const words = message.toLowerCase()
    .replace(/[^\w\s]/g, ' ')
    .split(/\s+/)
    .filter(word => word.length > 2 && !stopWords.has(word));

  // Return the most meaningful terms (max 5)
  return words.slice(0, 5).join(' ');
}
