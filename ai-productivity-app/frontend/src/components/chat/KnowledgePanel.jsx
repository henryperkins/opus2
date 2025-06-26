import { useState, useCallback } from 'react';
import { Search, Upload, Clock, X, FileText, Code, Database } from 'lucide-react';
import PropTypes from 'prop-types';

// Simple search panel
function SearchPanel({ projectId, onResultSelect }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;

    setIsSearching(true);
    try {
      // This would integrate with your knowledge search API
      const response = await fetch(`/api/projects/${projectId}/knowledge/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      });

      if (response.ok) {
        const data = await response.json();
        setResults(data.results || []);
      }
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setIsSearching(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <div className="space-y-4">
      {/* Search input */}
      <div className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Search knowledge base..."
          className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
            focus:outline-none focus:ring-2 focus:ring-blue-500
            bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
        />
        <button
          onClick={handleSearch}
          disabled={!query.trim() || isSearching}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700
            disabled:opacity-50 transition-colors"
        >
          {isSearching ? '...' : 'Search'}
        </button>
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {results.map((result, index) => (
            <div
              key={index}
              onClick={() => onResultSelect && onResultSelect(result)}
              className="p-3 border border-gray-200 dark:border-gray-600 rounded-lg
                hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
            >
              <div className="flex items-start gap-2">
                {result.type === 'document' ? (
                  <FileText className="w-4 h-4 text-blue-500 mt-0.5" />
                ) : (
                  <Code className="w-4 h-4 text-green-500 mt-0.5" />
                )}
                <div className="flex-1 min-w-0">
                  <h4 className="font-medium text-sm truncate">{result.title}</h4>
                  <p className="text-xs text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">
                    {result.excerpt}
                  </p>
                  {result.confidence && (
                    <div className="mt-1">
                      <span className="text-xs text-gray-500">
                        {Math.round(result.confidence * 100)}% match
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* No results */}
      {query && results.length === 0 && !isSearching && (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p>No results found for "{query}"</p>
        </div>
      )}
    </div>
  );
}

// Simple upload panel
function UploadPanel({ projectId, onUploadSuccess }) {
  const [isUploading, setIsUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const handleFileUpload = async (files) => {
    if (!files || files.length === 0) return;

    setIsUploading(true);
    try {
      const formData = new FormData();
      Array.from(files).forEach(file => {
        formData.append('files', file);
      });

      const response = await fetch(`/api/projects/${projectId}/knowledge/upload`, {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        onUploadSuccess && onUploadSuccess();
      }
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    handleFileUpload(e.dataTransfer.files);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragActive(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragActive(false);
  };

  return (
    <div className="space-y-4">
      {/* Upload area */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`
          border-2 border-dashed rounded-lg p-8 text-center transition-colors
          ${dragActive
            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
            : 'border-gray-300 dark:border-gray-600'
          }
          ${isUploading ? 'opacity-50 pointer-events-none' : ''}
        `}
      >
        <Upload className="w-8 h-8 mx-auto mb-2 text-gray-400" />
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
          {isUploading ? 'Uploading...' : 'Drag and drop files here, or click to select'}
        </p>
        <input
          type="file"
          multiple
          onChange={(e) => handleFileUpload(e.target.files)}
          className="hidden"
          accept=".txt,.md,.pdf,.doc,.docx,.js,.jsx,.ts,.tsx,.py"
          id="file-upload"
        />
        <label
          htmlFor="file-upload"
          className="inline-block px-4 py-2 bg-blue-600 text-white rounded-lg
            hover:bg-blue-700 cursor-pointer transition-colors"
        >
          Choose Files
        </label>
      </div>

      <div className="text-xs text-gray-500 dark:text-gray-400">
        Supported formats: .txt, .md, .pdf, .doc, .js, .py and more
      </div>
    </div>
  );
}

// Simple recent items panel
function RecentPanel({ onItemSelect }) {

  // This would fetch recent items from your API
  const mockRecentItems = [
    {
      id: '1',
      title: 'Project Documentation',
      type: 'document',
      lastAccessed: '2 hours ago',
      excerpt: 'Main project documentation covering architecture and setup...'
    },
    {
      id: '2',
      title: 'API Routes',
      type: 'code',
      lastAccessed: '1 day ago',
      excerpt: 'Express.js API route definitions and middleware...'
    },
    {
      id: '3',
      title: 'Database Schema',
      type: 'document',
      lastAccessed: '3 days ago',
      excerpt: 'PostgreSQL schema definitions and relationships...'
    }
  ];

  return (
    <div className="space-y-2">
      {mockRecentItems.map((item) => (
        <div
          key={item.id}
          onClick={() => onItemSelect && onItemSelect(item)}
          className="p-3 border border-gray-200 dark:border-gray-600 rounded-lg
            hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
        >
          <div className="flex items-start gap-2">
            {item.type === 'document' ? (
              <FileText className="w-4 h-4 text-blue-500 mt-0.5" />
            ) : (
              <Code className="w-4 h-4 text-green-500 mt-0.5" />
            )}
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <h4 className="font-medium text-sm truncate">{item.title}</h4>
                <span className="text-xs text-gray-500 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {item.lastAccessed}
                </span>
              </div>
              <p className="text-xs text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">
                {item.excerpt}
              </p>
            </div>
          </div>
        </div>
      ))}

      {mockRecentItems.length === 0 && (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <Database className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p>No recent activity</p>
        </div>
      )}
    </div>
  );
}

/**
 * Simplified knowledge panel component
 * Replaces complex KnowledgeAssistant with cleaner, responsive implementation
 */
export default function KnowledgePanel({
  projectId,
  isOpen = true,
  onClose,
  containerMode = 'overlay' // 'overlay' for desktop, 'inline' for mobile
}) {
  const [activeTab, setActiveTab] = useState('search');

  const handleResultSelect = useCallback((result) => {
    // Handle search result selection
    console.log('Selected result:', result);
  }, []);

  const handleUploadSuccess = useCallback(() => {
    // Handle successful upload
    console.log('Upload successful');
  }, []);

  const handleItemSelect = useCallback((item) => {
    // Handle recent item selection
    console.log('Selected item:', item);
  }, []);

  if (!isOpen) return null;

  // Mobile: Full screen modal
  // Desktop: Side panel
  const panelClass = containerMode === 'overlay'
    ? `fixed inset-0 md:relative md:inset-auto md:h-full md:w-full
       bg-white dark:bg-gray-800 z-50 md:z-auto
       ${isOpen ? 'block' : 'hidden md:block'}`
    : 'w-full h-full bg-white dark:bg-gray-800';

  const tabs = [
    { id: 'search', label: 'Search', icon: Search },
    { id: 'upload', label: 'Upload', icon: Upload },
    { id: 'recent', label: 'Recent', icon: Clock }
  ];

  return (
    <div className={panelClass}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <h3 className="font-semibold text-gray-900 dark:text-gray-100">Knowledge Base</h3>
        {containerMode === 'overlay' && (
          <button
            onClick={onClose}
            className="md:hidden p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-lg"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 dark:border-gray-700 overflow-x-auto">
        {tabs.map(tab => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                flex items-center gap-2 px-4 py-3 text-sm whitespace-nowrap transition-colors
                ${activeTab === tab.id
                  ? 'border-b-2 border-blue-600 text-blue-600 dark:text-blue-400'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
                }
              `}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'search' && (
          <SearchPanel
            projectId={projectId}
            onResultSelect={handleResultSelect}
          />
        )}
        {activeTab === 'upload' && (
          <UploadPanel
            projectId={projectId}
            onUploadSuccess={handleUploadSuccess}
          />
        )}
        {activeTab === 'recent' && (
          <RecentPanel
            onItemSelect={handleItemSelect}
          />
        )}
      </div>
    </div>
  );
}

KnowledgePanel.propTypes = {
  projectId: PropTypes.string.isRequired,
  isOpen: PropTypes.bool,
  onClose: PropTypes.func,
  containerMode: PropTypes.oneOf(['overlay', 'inline'])
};

SearchPanel.propTypes = {
  projectId: PropTypes.string.isRequired,
  onResultSelect: PropTypes.func
};

UploadPanel.propTypes = {
  projectId: PropTypes.string.isRequired,
  onUploadSuccess: PropTypes.func
};

RecentPanel.propTypes = {
  onItemSelect: PropTypes.func
};
