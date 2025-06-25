// components/knowledge/SmartKnowledgeSearch.jsx
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Search, Filter, X, FileText, Code, Tag, Calendar, TrendingUp } from 'lucide-react';
import { searchAPI } from '../../api/search';
import { useDebounce } from '../../hooks/useDebounce';

export default function SmartKnowledgeSearch({
  projectId,
  onResultSelect,
  onClose,
  defaultQuery = ''
}) {
  const [query, setQuery] = useState(defaultQuery);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    type: 'all',
    minScore: 0.5
  });
  const [showFilters, setShowFilters] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [searchHistory, setSearchHistory] = useState([]);
  const [popularQueries, setPopularQueries] = useState([]);

  const searchInputRef = useRef(null);
  const resultsRef = useRef(null);

  const debouncedQuery = useDebounce(query, 300);

  // Load search history and popular queries
  useEffect(() => {
    const loadSearchData = async () => {
      try {
        const [history, popular] = await Promise.all([
          searchAPI.getSearchHistory(projectId),
          searchAPI.getPopularQueries(projectId)
        ]);
        setSearchHistory(history.slice(0, 5));
        setPopularQueries(popular.slice(0, 5));
      } catch (error) {
        console.error('Failed to load search data:', error);
      }
    };

    loadSearchData();
  }, [projectId]);

  // Perform search
  useEffect(() => {
    if (!debouncedQuery || debouncedQuery.length < 2) {
      setResults([]);
      return;
    }

    const performSearch = async () => {
      setLoading(true);
      try {
        const searchParams = {
          query: debouncedQuery,
          type: filters.type,
          language: filters.language,
          min_score: filters.minScore,
          max_results: 20
        };

        const response = await searchAPI.smartSearch(projectId, searchParams);
        setResults(response.results || []);
        setSelectedIndex(-1);

        // Save to search history
        await searchAPI.addToHistory(projectId, debouncedQuery);
      } catch (error) {
        console.error('Search failed:', error);
        setResults([]);
      } finally {
        setLoading(false);
      }
    };

    performSearch();
  }, [debouncedQuery, filters, projectId]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose?.();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(prev =>
          prev < results.length - 1 ? prev + 1 : prev
        );
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(prev => prev > 0 ? prev - 1 : -1);
      } else if (e.key === 'Enter' && selectedIndex >= 0) {
        e.preventDefault();
        handleResultSelect(results[selectedIndex]);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [results, selectedIndex, onClose]);

  // Focus input on mount
  useEffect(() => {
    searchInputRef.current?.focus();
  }, []);

  const handleResultSelect = useCallback((result) => {
    onResultSelect(result);
    onClose?.();
  }, [onResultSelect, onClose]);

  const handleFilterChange = (newFilters) => {
    setFilters(prev => ({ ...prev, ...newFilters }));
  };

  const handleHistorySelect = (historyQuery) => {
    setQuery(historyQuery);
  };

  const renderResult = (result, index) => {
    const isSelected = index === selectedIndex;
    const icon = result.type === 'code' ? Code :
                 result.type === 'document' ? FileText : Tag;
    const IconComponent = icon;

    return (
      <div
        key={result.id}
        className={`p-4 cursor-pointer border-b border-gray-200 hover:bg-gray-50 ${
          isSelected ? 'bg-blue-50 border-blue-200' : ''
        }`}
        onClick={() => handleResultSelect(result)}
        onMouseEnter={() => setSelectedIndex(index)}
      >
        <div className="flex items-start space-x-3">
          <IconComponent className="w-5 h-5 text-gray-500 mt-0.5 shrink-0" />

          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-1">
              <h3 className="text-sm font-medium text-gray-900 truncate">
                {result.title}
              </h3>
              <span className="text-xs text-gray-500 ml-2">
                {Math.round(result.score * 100)}%
              </span>
            </div>

            <p className="text-xs text-gray-600 mb-2">{result.path}</p>

            {result.highlights && result.highlights.length > 0 ? (
              <div className="space-y-1">
                {result.highlights.slice(0, 2).map((highlight, idx) => (
                  <p key={idx} className="text-sm text-gray-700">
                    <span dangerouslySetInnerHTML={{ __html: highlight }} />
                  </p>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-700">
                {result.content.slice(0, 150)}...
              </p>
            )}

            {result.metadata && (
              <div className="flex items-center space-x-3 mt-2 text-xs text-gray-500">
                {result.metadata.language && (
                  <span className="px-2 py-1 bg-gray-100 rounded">
                    {result.metadata.language}
                  </span>
                )}
                {result.metadata.author && (
                  <span>by {result.metadata.author}</span>
                )}
                {result.metadata.lastModified && (
                  <span>{new Date(result.metadata.lastModified).toLocaleDateString()}</span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-16 px-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black bg-opacity-50"
        onClick={onClose}
      />

      {/* Search Modal */}
      <div className="relative w-full max-w-2xl bg-white rounded-lg shadow-xl">
        {/* Header */}
        <div className="flex items-center space-x-3 p-4 border-b border-gray-200">
          <Search className="w-5 h-5 text-gray-400" />
          <input
            ref={searchInputRef}
            type="text"
            placeholder="Search knowledge base..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="flex-1 text-lg border-none outline-none"
          />
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`p-2 rounded-lg transition-colors ${
              showFilters ? 'bg-blue-100 text-blue-600' : 'text-gray-400 hover:text-gray-600'
            }`}
          >
            <Filter className="w-5 h-5" />
          </button>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 rounded-lg"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Filters */}
        {showFilters && (
          <div className="p-4 border-b border-gray-200 bg-gray-50">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Content Type
                </label>
                <select
                  value={filters.type}
                  onChange={(e) => handleFilterChange({ type: e.target.value })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                >
                  <option value="all">All Types</option>
                  <option value="code">Code</option>
                  <option value="docs">Documents</option>
                  <option value="comments">Comments</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Min Score
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={filters.minScore}
                  onChange={(e) => handleFilterChange({ minScore: parseFloat(e.target.value) })}
                  className="w-full"
                />
                <span className="text-xs text-gray-500">
                  {Math.round(filters.minScore * 100)}%
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Content */}
        <div className="max-h-96 overflow-y-auto" ref={resultsRef}>
          {loading && (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          )}

          {!loading && query && results.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No results found for "{query}"</p>
            </div>
          )}

          {!loading && !query && (
            <div className="p-4 space-y-4">
              {/* Search History */}
              {searchHistory.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center">
                    <Calendar className="w-4 h-4 mr-1" />
                    Recent Searches
                  </h4>
                  <div className="space-y-1">
                    {searchHistory.map((item, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleHistorySelect(item.query)}
                        className="block w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded"
                      >
                        {item.query}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Popular Queries */}
              {popularQueries.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center">
                    <TrendingUp className="w-4 h-4 mr-1" />
                    Popular Searches
                  </h4>
                  <div className="space-y-1">
                    {popularQueries.map((item, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleHistorySelect(item.query)}
                        className="block w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded"
                      >
                        {item.query}
                        <span className="text-xs text-gray-500 ml-2">
                          ({item.count} searches)
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Results */}
          {!loading && results.length > 0 && (
            <div>
              {results.map((result, index) => renderResult(result, index))}
            </div>
          )}
        </div>

        {/* Footer */}
        {results.length > 0 && (
          <div className="p-3 border-t border-gray-200 bg-gray-50 text-xs text-gray-600">
            {results.length} results • Use ↑↓ to navigate, Enter to select, Esc to close
          </div>
        )}
      </div>
    </div>
  );
}
