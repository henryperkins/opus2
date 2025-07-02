// Search results display with code previews and navigation
import CodeSnippet from './CodeSnippet';
import LoadingSpinner from '../common/LoadingSpinner';

export default function SearchResults({ results, query, loading }) {
  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <LoadingSpinner label="Searching..." showLabel={true} />
      </div>
    );
  }

  if (!results || results.length === 0) {
    return (
      <div className="text-center py-12">
        <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <h3 className="mt-2 text-sm font-medium text-gray-900">No results found</h3>
        <p className="mt-1 text-sm text-gray-500">
          Try adjusting your search query or filters
        </p>
      </div>
    );
  }

  const highlightQuery = (text) => {
    if (!query) return text;

    const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`(${escapedQuery})`, 'gi');
    const parts = text.split(regex);

    return parts.map((part, i) =>
      regex.test(part) ? <mark key={i} className="bg-yellow-200">{part}</mark> : part
    );
  };

  return (
    <div className="space-y-4">
      <div className="text-sm text-gray-600">
        Found {results.length} result{results.length !== 1 ? 's' : ''}
      </div>

      {results.map((result, index) => {
        // Use a unique, string-safe key: prefer valid id, else file_path+lines, else fallback to index
        let resultKey = `result-${index}`;
        if (result && typeof result.id === 'string' && result.id.trim() && !/[\uFFFD<>]/.test(result.id)) {
          resultKey = result.id;
        } else if (result && typeof result.file_path === 'string' && result.start_line && result.end_line) {
          resultKey = `${result.file_path}:${result.start_line}-${result.end_line}`;
        }
        return (
          <div
            key={resultKey}
            className="bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow"
          >
            <div className="p-4">
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <h4 className="text-sm font-medium text-gray-900">
                    {highlightQuery(result.file_path)}
                  </h4>
                  <div className="flex items-center mt-1 space-x-4 text-xs text-gray-500">
                    <span className="flex items-center">
                      <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                      </svg>
                      {result.language}
                    </span>
                    {result.symbol && (
                      <span className="flex items-center">
                        <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                        </svg>
                        {result.symbol}
                      </span>
                    )}
                    <span className="flex items-center">
                      Lines {result.start_line}-{result.end_line}
                    </span>
                  </div>
                </div>
                <div className="ml-4 flex items-center space-x-2">
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    result.search_type === 'semantic'
                      ? 'bg-purple-100 text-purple-800'
                      : 'bg-green-100 text-green-800'
                  }`}>
                    {result.search_type}
                  </span>
                  <span className="text-xs text-gray-500">
                    {(result.score * 100).toFixed(0)}% match
                  </span>
                </div>
              </div>

              <div className="mt-3">
                <CodeSnippet
                  content={result.content}
                  language={result.language}
                  startLine={result.start_line}
                  highlightLines={[]}
                />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
