// Search results display with code previews and navigation
import React from 'react';
import CodeSnippet from './CodeSnippet';
import LoadingSpinner from '../common/LoadingSpinner';

export default function SearchResults({ results, query, loading, onFileClick }) {
  if (loading) {
    return (
      <div className="h-full flex flex-col">
        {/* Mobile loading */}
        <div className="lg:hidden space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="bg-white dark:bg-gray-800 rounded-2xl p-4 animate-pulse">
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-2">
                    <div className="w-12 h-5 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
                    <div className="w-16 h-4 bg-gray-200 dark:bg-gray-700 rounded"></div>
                  </div>
                  <div className="w-32 h-4 bg-gray-200 dark:bg-gray-700 rounded mb-1"></div>
                  <div className="w-48 h-3 bg-gray-200 dark:bg-gray-700 rounded"></div>
                </div>
                <div className="w-10 h-10 bg-gray-200 dark:bg-gray-700 rounded-xl"></div>
              </div>
              <div className="bg-gray-100 dark:bg-gray-900 rounded-xl p-3">
                <div className="space-y-2">
                  <div className="w-full h-3 bg-gray-200 dark:bg-gray-700 rounded"></div>
                  <div className="w-3/4 h-3 bg-gray-200 dark:bg-gray-700 rounded"></div>
                  <div className="w-1/2 h-3 bg-gray-200 dark:bg-gray-700 rounded"></div>
                </div>
              </div>
            </div>
          ))}
          <div className="text-center py-4">
            <div className="inline-flex items-center space-x-2 text-sm text-blue-500">
              <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
              <span>Searching your codebase...</span>
            </div>
          </div>
        </div>
        
        {/* Desktop loading */}
        <div className="hidden lg:block flex justify-center items-center py-12">
          <LoadingSpinner label="Searching..." showLabel={true} />
        </div>
      </div>
    );
  }

  if (!results || results.length === 0) {
    return (
      <div className="text-center py-12">
        {/* Mobile empty state */}
        <div className="lg:hidden">
          <div className="w-20 h-20 mx-auto mb-4 bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-700 rounded-2xl flex items-center justify-center">
            <span className="text-3xl">🔍</span>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">No results found</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4 px-4">
            Try adjusting your search query or filters
          </p>
          <div className="space-y-2 px-4">
            <p className="text-xs text-gray-400 dark:text-gray-500">💡 Tips:</p>
            <div className="space-y-1 text-xs text-gray-500 dark:text-gray-400">
              <p>• Use broader keywords</p>
              <p>• Check your spelling</p>
              <p>• Try different search modes</p>
            </div>
          </div>
        </div>
        
        {/* Desktop empty state */}
        <div className="hidden lg:block">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-gray-100">No results found</h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Try adjusting your search query or filters
          </p>
        </div>
      </div>
    );
  }

  /**
   * Highlight occurrences of the current search query inside a piece of text.
   * This version is defensive: it tolerates undefined / non-string inputs.
   */
  const highlightQuery = (text) => {
    // If no query or text is not a string, just return it untouched
    if (!query || typeof text !== 'string') {
      return text ?? '';
    }

    // Escape RegExp metacharacters before building the pattern
    const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`(${escapedQuery})`, 'gi');

    // Split into alternating unmatched/matched parts
    const parts = text.split(regex);

    return parts.map((part, i) =>
      regex.test(part) ? (
        <mark key={i} className="bg-yellow-200 dark:bg-yellow-900/50 rounded px-1">
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  return (
    <div className="h-full flex flex-col">
      {/* Mobile results */}
      <div className="lg:hidden space-y-3">
        {results.map((result, index) => {
          if (!result || typeof result !== 'object') {
            return null;
          }

          let resultKey = `result-${index}`;
          if (result && typeof result.id === 'string' && result.id.trim() && !/[\uFFFD<>]/.test(result.id)) {
            resultKey = result.id;
          } else if (result && typeof result.file_path === 'string' && result.start_line && result.end_line) {
            resultKey = `${result.file_path}:${result.start_line}-${result.end_line}`;
          }

          return (
            <div
              key={resultKey}
              onClick={() => {
                const filePath = result.file_path || result?.file_path;
                const startLine = result.start_line ?? 1;
                if (filePath && typeof filePath === 'string' && filePath.trim()) {
                  onFileClick?.(filePath, startLine);
                }
              }}
              className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg border border-gray-200/50 dark:border-gray-700/50 p-4 hover:shadow-xl transition-all duration-300 cursor-pointer active:scale-98 group"
            >
              {/* Header with file info */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2 mb-1">
                    {/* Language badge */}
                    <div className={`flex items-center space-x-1 px-2 py-1 rounded-lg text-xs font-medium ${
                      result.language === 'javascript' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400' :
                      result.language === 'python' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400' :
                      result.language === 'typescript' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400' :
                      'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400'
                    }`}>
                      <span className={`w-2 h-2 rounded-full ${
                        result.language === 'javascript' ? 'bg-yellow-500' :
                        result.language === 'python' ? 'bg-blue-500' :
                        result.language === 'typescript' ? 'bg-blue-500' :
                        'bg-gray-500'
                      }`}></span>
                      <span>{result.language || 'text'}</span>
                    </div>
                    {/* Match score */}
                    <div className="flex items-center space-x-1 text-xs text-gray-500 dark:text-gray-400">
                      <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                      <span>{((result.score || 0) * 100).toFixed(0)}% match</span>
                    </div>
                  </div>
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100 text-sm leading-tight mb-1">
                    {highlightQuery(result.file_path?.split('/').pop() || 'unknown')}
                  </h3>
                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                    {result.file_path || 'unknown path'}
                  </p>
                </div>
                <div className="ml-3 flex-shrink-0">
                  <div className={`p-2 rounded-xl ${
                    (result.search_type || result.type) === 'semantic' ? 'bg-purple-100 dark:bg-purple-900/30' :
                    (result.search_type || result.type) === 'keyword' ? 'bg-green-100 dark:bg-green-900/30' :
                    'bg-blue-100 dark:bg-blue-900/30'
                  }`}>
                    <span className="text-lg">
                      {(result.search_type || result.type) === 'semantic' ? '🎯' :
                       (result.search_type || result.type) === 'keyword' ? '📝' :
                       '⚡'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Symbol info */}
              {result.symbol && (
                <div className="mb-3 p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <div className="flex items-center space-x-2">
                    <div className="w-4 h-4 bg-blue-500 rounded flex items-center justify-center">
                      <span className="text-xs text-white font-bold">f</span>
                    </div>
                    <span className="text-sm font-medium text-blue-900 dark:text-blue-100">{result.symbol}</span>
                  </div>
                </div>
              )}

              {/* Code preview */}
              <div className="bg-gray-50 dark:bg-gray-900 rounded-xl p-3 relative overflow-hidden">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">Lines {result.start_line || 1}-{result.end_line || result.start_line || 1}</span>
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-red-400 rounded-full"></div>
                    <div className="w-2 h-2 bg-yellow-400 rounded-full"></div>
                    <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                  </div>
                </div>
                <pre className="text-xs font-mono text-gray-800 dark:text-gray-200 whitespace-pre-wrap break-words leading-relaxed">
                  {highlightQuery((result.content || '').slice(0, 150))}
                  {(result.content || '').length > 150 && (
                    <span className="text-gray-400 dark:text-gray-500">... see more</span>
                  )}
                </pre>
                {/* Tap to view indicator */}
                <div className="absolute bottom-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <div className="bg-blue-500 text-white text-xs px-2 py-1 rounded-lg flex items-center space-x-1">
                    <span>Tap to view</span>
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Desktop results */}
      <div className="hidden lg:block flex-1 overflow-y-auto space-y-4 scrollbar-thin">
        {results.map((result, index) => {
          if (!result || typeof result !== 'object') {
            return null;
          }

          let resultKey = `result-${index}`;
          if (result && typeof result.id === 'string' && result.id.trim() && !/[\uFFFD<>]/.test(result.id)) {
            resultKey = result.id;
          } else if (result && typeof result.file_path === 'string' && result.start_line && result.end_line) {
            resultKey = `${result.file_path}:${result.start_line}-${result.end_line}`;
          }

          return (
            <button
              type="button"
              key={resultKey}
              onClick={() => {
                const filePath = result.file_path || result?.file_path;
                const startLine = result.start_line ?? 1;
                if (filePath && typeof filePath === 'string' && filePath.trim()) {
                  onFileClick?.(filePath, startLine);
                }
              }}
              className="w-full text-left bg-white/80 dark:bg-gray-800/80 backdrop-blur-xl border border-gray-200/50 dark:border-gray-700/50 rounded-2xl shadow-lg hover:shadow-xl transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              <div className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1 min-w-0">
                    <h4 className="text-lg font-semibold text-gray-900 dark:text-gray-100 truncate pr-2">
                      {highlightQuery(result.file_path || result?.file_path || 'unknown')}
                    </h4>
                    <div className="flex items-center mt-2 space-x-4 text-sm text-gray-500 dark:text-gray-400">
                      <span className="flex items-center">
                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                        </svg>
                        {result.language || 'unknown'}
                      </span>
                      {result.symbol && (
                        <span className="flex items-center">
                          <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                          </svg>
                          {result.symbol}
                        </span>
                      )}
                      <span>Lines {result.start_line || 1}-{result.end_line || result.start_line || 1}</span>
                    </div>
                  </div>
                  <div className="ml-4 flex items-center space-x-3">
                    <span className={`px-3 py-1 text-sm rounded-full font-medium ${
                      (result.search_type || result.type) === 'semantic'
                        ? 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400'
                        : 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                    }`}>
                      {result.search_type || result.type || 'unknown'}
                    </span>
                    <span className="text-sm text-gray-500 dark:text-gray-400 font-medium">
                      {((result.score || 0) * 100).toFixed(0)}% match
                    </span>
                  </div>
                </div>

                <div className="mt-4">
                  <CodeSnippet
                    content={result.content || ''}
                    language={result.language || 'text'}
                    startLine={result.start_line || 1}
                    highlightLines={[]}
                  />
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}