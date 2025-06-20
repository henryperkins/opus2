// components/knowledge/KnowledgeContextPanel.jsx
import React, { useState, useEffect, useMemo } from 'react';
import { useProject } from '../../hooks/useProjects';
import { searchAPI } from '../../api/search';
import { ChevronRight, ChevronDown, FileText, Code, Link, AlertCircle } from 'lucide-react';

export default function KnowledgeContextPanel({
  query,
  projectId,
  onDocumentSelect,
  onCodeSelect,
  maxHeight = '400px'
}) {
  const [context, setContext] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedItems, setExpandedItems] = useState(new Set());
  const [selectedItems, setSelectedItems] = useState(new Set());

  const { project } = useProject(projectId);

  // Search for relevant context when query changes
  useEffect(() => {
    if (!query || query.length < 3) {
      setContext(null);
      return;
    }

    const searchContext = async () => {
      setLoading(true);
      setError(null);
      try {
        const startTime = Date.now();
        const results = await searchAPI.searchProject(projectId, query, {
          include_code: true,
          include_docs: true,
          max_results: 10
        });

        const searchTime = Date.now() - startTime;

        // Process and score results
        const relevantDocs = results.documents?.map(doc => ({
          ...doc,
          type: doc.type || 'document',
          highlights: extractHighlights(doc.content, query)
        })) || [];

        const codeSnippets = results.code_snippets || [];

        // Calculate confidence based on scores and relevance
        const avgScore = [...relevantDocs, ...codeSnippets]
          .reduce((sum, item) => sum + (item.score || 0), 0) /
          (relevantDocs.length + codeSnippets.length);

        setContext({
          relevantDocs,
          codeSnippets,
          totalMatches: relevantDocs.length + codeSnippets.length,
          searchTime,
          confidence: Math.min(avgScore || 0, 1)
        });
      } catch (err) {
        console.error('Failed to search context:', err);
        setError(err.message || 'Failed to search knowledge base');
      } finally {
        setLoading(false);
      }
    };

    const debounceTimer = setTimeout(searchContext, 300);
    return () => clearTimeout(debounceTimer);
  }, [query, projectId]);

  const toggleExpanded = (itemId) => {
    setExpandedItems(prev => {
      const newSet = new Set(prev);
      if (newSet.has(itemId)) {
        newSet.delete(itemId);
      } else {
        newSet.add(itemId);
      }
      return newSet;
    });
  };

  const toggleSelected = (itemId) => {
    setSelectedItems(prev => {
      const newSet = new Set(prev);
      if (newSet.has(itemId)) {
        newSet.delete(itemId);
      } else {
        newSet.add(itemId);
      }
      return newSet;
    });
  };

  const handleDocumentClick = (doc) => {
    toggleSelected(doc.id);
    onDocumentSelect?.(doc);
  };

  const handleCodeClick = (snippet) => {
    toggleSelected(snippet.id);
    onCodeSelect?.(snippet);
  };

  // Group and sort items by relevance
  const sortedItems = useMemo(() => {
    if (!context) return [];

    const allItems = [
      ...context.relevantDocs.map(doc => ({ ...doc, itemType: 'document' })),
      ...context.codeSnippets.map(snippet => ({ ...snippet, itemType: 'code' }))
    ];

    return allItems.sort((a, b) => (b.score || 0) - (a.score || 0));
  }, [context]);

  if (!query || query.length < 3) {
    return (
      <div className="flex items-center justify-center h-32 text-gray-500">
        <div className="text-center">
          <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">Enter a search query to find relevant context</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
          <p className="text-sm text-gray-600">Searching knowledge base...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-32 text-red-600">
        <div className="text-center">
          <AlertCircle className="w-8 h-8 mx-auto mb-2" />
          <p className="text-sm">{error}</p>
        </div>
      </div>
    );
  }

  if (!context || context.totalMatches === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-gray-500">
        <div className="text-center">
          <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No relevant context found</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4" style={{ maxHeight, overflow: 'auto' }}>
      {/* Context Summary */}
      <div className="px-4 py-3 bg-blue-50 rounded-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <FileText className="w-4 h-4 text-blue-600" />
            <span className="text-sm font-medium text-blue-900">
              Found {context.totalMatches} relevant items
            </span>
          </div>
          <div className="flex items-center space-x-2 text-xs text-blue-700">
            <span>{context.searchTime}ms</span>
            <span>•</span>
            <span>{Math.round(context.confidence * 100)}% confidence</span>
          </div>
        </div>
      </div>

      {/* Results */}
      <div className="space-y-2">
        {sortedItems.map(item => (
          <div
            key={item.id}
            className={`border rounded-lg overflow-hidden transition-all ${
              selectedItems.has(item.id)
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            {/* Item Header */}
            <div
              className="px-4 py-3 cursor-pointer hover:bg-gray-50"
              onClick={() => {
                if (item.itemType === 'document') {
                  handleDocumentClick(item);
                } else {
                  handleCodeClick(item);
                }
              }}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3 flex-1 min-w-0">
                  {item.itemType === 'document' ? (
                    <FileText className="w-4 h-4 text-gray-500 flex-shrink-0" />
                  ) : (
                    <Code className="w-4 h-4 text-gray-500 flex-shrink-0" />
                  )}

                  <div className="flex-1 min-w-0">
                    <h4 className="text-sm font-medium text-gray-900 truncate">
                      {item.title || item.file_path?.split('/').pop() || 'Untitled'}
                    </h4>
                    <p className="text-xs text-gray-600 truncate">
                      {item.path || item.file_path}
                    </p>
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <span className="text-xs text-gray-500">
                    {Math.round((item.score || 0) * 100)}%
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleExpanded(item.id);
                    }}
                    className="p-1 hover:bg-gray-200 rounded"
                  >
                    {expandedItems.has(item.id) ? (
                      <ChevronDown className="w-4 h-4" />
                    ) : (
                      <ChevronRight className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>
            </div>

            {/* Expanded Content */}
            {expandedItems.has(item.id) && (
              <div className="px-4 py-3 border-t border-gray-200 bg-gray-50">
                {item.itemType === 'document' ? (
                  <div className="space-y-2">
                    {item.highlights && item.highlights.length > 0 ? (
                      <div className="space-y-1">
                        {item.highlights.slice(0, 3).map((highlight, idx) => (
                          <div key={idx} className="text-sm text-gray-700">
                            <span dangerouslySetInnerHTML={{ __html: highlight }} />
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-gray-700">
                        {item.content.slice(0, 200)}...
                      </p>
                    )}
                  </div>
                ) : (
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2 text-xs text-gray-600">
                      <span>Lines {item.start_line}-{item.end_line}</span>
                      <span>•</span>
                      <span>{item.language}</span>
                    </div>
                    <pre className="text-sm bg-gray-100 p-2 rounded overflow-x-auto">
                      <code>{item.content.slice(0, 300)}...</code>
                    </pre>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex items-center justify-between mt-3 pt-2 border-t border-gray-300">
                  <div className="text-xs text-gray-500">
                    Click to {selectedItems.has(item.id) ? 'deselect' : 'select'}
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      // Open in external viewer
                    }}
                    className="p-1 text-gray-500 hover:text-gray-700 rounded"
                    title="Open source"
                  >
                    <Link className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// Helper function to extract highlights
function extractHighlights(content, query) {
  if (!content || !query) return [];

  const terms = query.toLowerCase().split(/\s+/);
  const sentences = content.split(/[.!?]+/);
  const highlights = [];

  sentences.forEach(sentence => {
    const lowerSentence = sentence.toLowerCase();
    const hasMatch = terms.some(term => lowerSentence.includes(term));

    if (hasMatch) {
      let highlighted = sentence;
      terms.forEach(term => {
        const regex = new RegExp(`(${term})`, 'gi');
        highlighted = highlighted.replace(regex, '<mark>$1</mark>');
      });
      highlights.push(highlighted.trim());
    }
  });

  return highlights.slice(0, 5); // Max 5 highlights
}
