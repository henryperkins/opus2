/* global AbortController, setTimeout, clearTimeout */

import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { searchAPI } from '../../api/search';
import { ChevronRight, ChevronDown, FileText, Code, Link, AlertCircle } from 'lucide-react';

// Custom hook for search logic
function useKnowledgeSearch(projectId, query) {
  const [state, setState] = useState({
    results: null,
    loading: false,
    error: null
  });

  useEffect(() => {
    if (!query || query.length < 3) {
      setState({ results: null, loading: false, error: null });
      return;
    }

    let cancelled = false;
    const controller = new AbortController();

    const search = async () => {
      setState(prev => ({ ...prev, loading: true, error: null }));

      try {
        const results = await searchAPI.searchProject(projectId, query, {
          include_code: true,
          include_docs: true,
          max_results: 10,
          signal: controller.signal
        });

        if (!cancelled) {
          setState({
            results: processResults(results, query),
            loading: false,
            error: null
          });
        }
      } catch (err) {
        if (!cancelled && err.name !== 'AbortError') {
          setState({
            results: null,
            loading: false,
            error: err.message || 'Search failed'
          });
        }
      }
    };

    const timer = setTimeout(search, 300);

    return () => {
      cancelled = true;
      controller.abort();
      clearTimeout(timer);
    };
  }, [projectId, query]);

  return state;
}

// Process search results
function processResults(results, query) {
  const documents = (results.documents || []).map(doc => ({
    ...doc,
    type: 'document',
    highlights: extractHighlights(doc.content, query)
  }));

  const code = (results.code_snippets || []).map(snippet => ({
    ...snippet,
    type: 'code'
  }));

  const allItems = [...documents, ...code].sort((a, b) => (b.score || 0) - (a.score || 0));

  return {
    items: allItems,
    totalCount: allItems.length
  };
}

// Extract text highlights
function extractHighlights(content, query) {
  if (!content || !query) return [];

  const terms = query.toLowerCase().split(/\s+/);
  const sentences = content.split(/[.!?]+/).filter(s => s.trim());

  return sentences
    .filter(sentence => {
      const lower = sentence.toLowerCase();
      return terms.some(term => lower.includes(term));
    })
    .slice(0, 3)
    .map(sentence => {
      let highlighted = sentence.trim();
      terms.forEach(term => {
        const regex = new RegExp(`(${term})`, 'gi');
        highlighted = highlighted.replace(regex, '<mark>$1</mark>');
      });
      return highlighted;
    });
}

// Empty state component
function EmptyState({ icon: Icon, message }) {
  return (
    <div className="flex items-center justify-center h-32 text-gray-500">
      <div className="text-center">
        <Icon className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">{message}</p>
      </div>
    </div>
  );
}
EmptyState.propTypes = {
  icon: PropTypes.elementType.isRequired,
  message: PropTypes.string.isRequired
};
// Loading component
function LoadingState() {
  return (
    <div className="flex items-center justify-center h-32">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
        <p className="text-sm text-gray-600">Searching knowledge base...</p>
      </div>
    </div>
  );
}

// Result item component
function ResultItem({ item, isExpanded, isSelected, onToggleExpanded, onSelect }) {
  const isDocument = item.type === 'document';
  const title = item.title || item.file_path?.split('/').pop() || 'Untitled';
  const path = item.path || item.file_path || '';
  const score = Math.round((item.score || 0) * 100);

  return (
    <div className={`border rounded-lg overflow-hidden transition-colors ${
      isSelected ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
    }`}>
      {/* Header */}
      <div className="px-4 py-3 cursor-pointer hover:bg-gray-50" onClick={onSelect}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3 flex-1 min-w-0">
            {isDocument ? (
              <FileText className="w-4 h-4 text-gray-500 flex-shrink-0" />
            ) : (
              <Code className="w-4 h-4 text-gray-500 flex-shrink-0" />
            )}
            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-medium text-gray-900 truncate">{title}</h4>
              <p className="text-xs text-gray-600 truncate">{path}</p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-xs text-gray-500">{score}%</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onToggleExpanded();
              }}
              className="p-1 hover:bg-gray-200 rounded"
            >
              {isExpanded ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="px-4 py-3 border-t border-gray-200 bg-gray-50">
          {isDocument ? (
            <DocumentContent item={item} />
          ) : (
            <CodeContent item={item} />
          )}

          <div className="flex items-center justify-between mt-3 pt-2 border-t border-gray-300">
            <div className="text-xs text-gray-500">
              Click to {isSelected ? 'deselect' : 'select'}
            </div>
            <button className="p-1 text-gray-500 hover:text-gray-700 rounded" title="Open source">
              <Link className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
ResultItem.propTypes = {
  item: PropTypes.shape({
    type: PropTypes.string,
    title: PropTypes.string,
    file_path: PropTypes.string,
    path: PropTypes.string,
    score: PropTypes.number,
    content: PropTypes.string,
    highlights: PropTypes.arrayOf(PropTypes.string),
    id: PropTypes.any,
    language: PropTypes.string,
    start_line: PropTypes.number,
    end_line: PropTypes.number,
  }).isRequired,
  isExpanded: PropTypes.bool.isRequired,
  isSelected: PropTypes.bool.isRequired,
  onToggleExpanded: PropTypes.func.isRequired,
  onSelect: PropTypes.func.isRequired,
};
// Document content component
function DocumentContent({ item }) {
  if (item.highlights && item.highlights.length > 0) {
    return (
      <div className="space-y-1">
        {item.highlights.map((highlight, idx) => (
          <div key={idx} className="text-sm text-gray-700">
            <span dangerouslySetInnerHTML={{ __html: highlight }} />
          </div>
        ))}
      </div>
    );
  }

  return (
    <p className="text-sm text-gray-700">
      {item.content?.slice(0, 200)}...
    </p>
  );
}
DocumentContent.propTypes = {
  item: PropTypes.shape({
    highlights: PropTypes.arrayOf(PropTypes.string),
    content: PropTypes.string,
  }).isRequired,
};
// Code content component
function CodeContent({ item }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center space-x-2 text-xs text-gray-600">
        <span>Lines {item.start_line}-{item.end_line}</span>
        <span>•</span>
        <span>{item.language}</span>
      </div>
      <pre className="text-sm bg-gray-100 p-2 rounded overflow-x-auto">
        <code>{item.content?.slice(0, 300)}...</code>
      </pre>
    </div>
  );
}
CodeContent.propTypes = {
  item: PropTypes.shape({
    start_line: PropTypes.number,
    end_line: PropTypes.number,
    language: PropTypes.string,
    content: PropTypes.string,
  }).isRequired,
};

// Main component
export default function KnowledgeContextPanel({
  query,
  projectId,
  onDocumentSelect,
  onCodeSelect,
  maxHeight = '400px'
}) {
  const [expanded, setExpanded] = useState(new Set());
  const [selected, setSelected] = useState(new Set());
  const { results, loading, error } = useKnowledgeSearch(projectId, query);

  const toggleExpanded = (id) => {
    setExpanded(prev => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const handleSelect = (item) => {
    const newSelected = new Set(selected);
    if (newSelected.has(item.id)) {
      newSelected.delete(item.id);
    } else {
      newSelected.add(item.id);
    }
    setSelected(newSelected);

    // Call appropriate callback
    if (item.type === 'document') {
      onDocumentSelect?.(item);
    } else {
      onCodeSelect?.(item);
    }
  };

  // Reset state when query changes
  useEffect(() => {
    setExpanded(new Set());
    setSelected(new Set());
  }, [query]);

  if (!query || query.length < 3) {
    return <EmptyState icon={FileText} message="Enter a search query to find relevant context" />;
  }

  if (loading) {
    return <LoadingState />;
  }

  if (error) {
    return <EmptyState icon={AlertCircle} message={error} />;
  }

  if (!results || results.totalCount === 0) {
    return <EmptyState icon={FileText} message="No relevant context found" />;
  }

  return (
    <div className="space-y-4" style={{ maxHeight, overflow: 'auto' }}>
      {/* Summary */}
      <div className="px-4 py-3 bg-blue-50 rounded-lg">
        <div className="flex items-center space-x-2">
          <FileText className="w-4 h-4 text-blue-600" />
          <span className="text-sm font-medium text-blue-900">
            Found {results.totalCount} relevant items
          </span>
        </div>
      </div>

      {/* Results */}
      <div className="space-y-2">
        {results.items.map(item => (
          <ResultItem
            key={item.id}
            item={item}
            isExpanded={expanded.has(item.id)}
            isSelected={selected.has(item.id)}
            onToggleExpanded={() => toggleExpanded(item.id)}
            onSelect={() => handleSelect(item)}
          />
        ))}
      </div>
    </div>
  );
}
KnowledgeContextPanel.propTypes = {
  query: PropTypes.string,
  projectId: PropTypes.any,
  onDocumentSelect: PropTypes.func,
  onCodeSelect: PropTypes.func,
  maxHeight: PropTypes.string,
};
