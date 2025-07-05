import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useSearch } from '../hooks/useSearch';
import SearchBar from '../components/search/SearchBar';
import SearchResults from '../components/search/SearchResults';
import SearchFilters from '../components/search/SearchFilters';
import DependencyGraph from '../components/knowledge/DependencyGraph';
import useProjectStore from '../stores/projectStore';

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { projects, fetchProjects } = useProjectStore();
  const [selectedProjects, setSelectedProjects] = useState([]);
  const [showGraph, setShowGraph] = useState(false);
  const [graphProjectId, setGraphProjectId] = useState(null);
  const [showFilters, setShowFilters] = useState(false);
  const [activeSearchMode, setActiveSearchMode] = useState('hybrid');

  const {
    query,
    filters,
    results,
    loading,
    error,
    totalResults,
    searchTypes,
    updateQuery,
    updateFilters,
    updateSearchTypes,
    clearSearch
  } = useSearch(searchParams.get('q') || '');

  const hasActiveFilters = Object.values(filters).some(v => v && (Array.isArray(v) ? v.length > 0 : true)) || selectedProjects.length > 0;

  const searchModes = [
    { id: 'hybrid', label: 'Smart', icon: '🧠', description: 'AI + Keyword' },
    { id: 'semantic', label: 'AI', icon: '🎯', description: 'Meaning-based' },
    { id: 'keyword', label: 'Text', icon: '📝', description: 'Exact matches' },
    { id: 'structural', label: 'Code', icon: '⚡', description: 'AST patterns' }
  ];

  // Update URL when query changes
  useEffect(() => {
    if (query) {
      setSearchParams({ q: query });
    } else {
      setSearchParams({});
    }
  }, [query, setSearchParams]);

  // Load projects on mount
  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const handleProjectToggle = (projectId) => {
    setSelectedProjects(prev => {
      const newSelection = prev.includes(projectId)
        ? prev.filter(id => id !== projectId)
        : [...prev, projectId];

      updateFilters({ projectIds: newSelection });
      return newSelection;
    });
  };

  const handleSearchTypeChange = (type) => {
    const newTypes = searchTypes.includes(type)
      ? searchTypes.filter(t => t !== type)
      : [...searchTypes, type];
    updateSearchTypes(newTypes.length > 0 ? newTypes : ['hybrid']);
  };

  const handleModeChange = (mode) => {
    setActiveSearchMode(mode);
    handleSearchTypeChange(mode);
  };

  const handleShowGraph = (projectId) => {
    setGraphProjectId(projectId);
    setShowGraph(true);
  };

  const handleFileClick = (path, line) => {
    if (!path || typeof path !== 'string' || !path.trim()) {
      console.warn('Invalid file path provided to handleFileClick:', path);
      return;
    }
    
    const lineParam = Number.isInteger(line) && line > 0 ? line : 1;
    const projectParam = selectedProjects.length > 0 ? `&project_id=${selectedProjects[0]}` : '';
    navigate(`/files/${encodeURIComponent(path.trim())}?line=${lineParam}${projectParam}`);
  };

  return (
    <div className="h-full bg-gradient-to-br from-gray-50 via-white to-blue-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      {/* Mobile-First Layout */}
      <div className="lg:hidden h-full flex flex-col">
        {/* Mobile Header with Search */}
        <div className="bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl border-b border-gray-200/50 dark:border-gray-700/50 safe-top">
          <div className="px-4 pt-4 pb-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                  Code Search
                </h1>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  AI-powered code discovery
                </p>
              </div>
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`relative p-3 rounded-xl transition-all duration-200 ${
                  hasActiveFilters 
                    ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/25' 
                    : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'
                }`}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4" />
                </svg>
                {hasActiveFilters && (
                  <div className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center font-bold">
                    {[filters.language, filters.fileType, filters.symbolType].filter(Boolean).length + selectedProjects.length}
                  </div>
                )}
              </button>
            </div>

            {/* Search Bar */}
            <div className="mb-4">
              <SearchBar
                value={query}
                onChange={updateQuery}
                placeholder="Search your codebase..."
                loading={loading}
                projectId={selectedProjects.length > 0 ? selectedProjects[0] : null}
              />
            </div>

            {/* Search Mode Pills */}
            <div className="flex space-x-2 overflow-x-auto pb-2 scrollbar-hide">
              {searchModes.map(mode => (
                <button
                  key={mode.id}
                  onClick={() => handleModeChange(mode.id)}
                  className={`flex-shrink-0 flex items-center space-x-2 px-4 py-2.5 rounded-xl transition-all duration-200 ${
                    searchTypes.includes(mode.id)
                      ? 'bg-gradient-to-r from-blue-500 to-purple-500 text-white shadow-lg shadow-blue-500/25'
                      : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700'
                  }`}
                >
                  <span className="text-lg">{mode.icon}</span>
                  <div className="text-left">
                    <div className="text-sm font-medium">{mode.label}</div>
                    <div className="text-xs opacity-75">{mode.description}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Mobile Results */}
        <div className="flex-1 min-h-0 px-4 py-4">
          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-2xl p-4 mb-4 flex items-center space-x-3">
              <div className="w-8 h-8 bg-red-100 dark:bg-red-900/40 rounded-full flex items-center justify-center">
                <svg className="w-4 h-4 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
            </div>
          )}

          {totalResults > 0 && (
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {totalResults} results found
                </span>
              </div>
              <button
                onClick={clearSearch}
                className="text-sm text-blue-500 font-medium hover:text-blue-600 transition-colors"
              >
                Clear all
              </button>
            </div>
          )}

          <SearchResults
            results={results}
            query={query}
            loading={loading}
            onFileClick={handleFileClick}
          />
        </div>
      </div>

      {/* Desktop Layout */}
      <div className="hidden lg:block h-full">
        <div className="px-4 sm:px-6 lg:px-8 py-8 h-full">
          <div className="max-w-7xl mx-auto h-full flex flex-col">
            {/* Desktop Header */}
            <div className="mb-8">
              <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-2">
                Code Search
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                Search across all your code with AI-powered understanding
              </p>
            </div>

            {/* Desktop Search Bar */}
            <div className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-xl rounded-2xl shadow-xl border border-gray-200/50 dark:border-gray-700/50 p-6 mb-6">
              <SearchBar
                value={query}
                onChange={updateQuery}
                placeholder="Search code, functions, classes, or natural language queries..."
                loading={loading}
                projectId={selectedProjects.length > 0 ? selectedProjects[0] : null}
              />

              {/* Desktop Search Type Toggles */}
              <div className="mt-6 flex items-center space-x-6">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Search modes:</span>
                {searchModes.map(mode => (
                  <label key={mode.id} className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={searchTypes.includes(mode.id)}
                      onChange={() => handleSearchTypeChange(mode.id)}
                      className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-700 dark:text-gray-300">{mode.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Desktop Content Layout */}
            <div className="flex-1 flex gap-6 min-h-0">
              {/* Desktop Filters Sidebar */}
              <div className="w-64 shrink-0">
                <div className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-xl rounded-2xl shadow-xl border border-gray-200/50 dark:border-gray-700/50 p-6 h-fit">
                  <SearchFilters
                    filters={filters}
                    onChange={updateFilters}
                    availableLanguages={['python', 'javascript', 'typescript']}
                  />

                  {/* Project Selection */}
                  <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
                    <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">Projects</h3>
                    <div className="space-y-2">
                      {projects.map(project => (
                        <label key={project.id} className="flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            checked={selectedProjects.includes(project.id)}
                            onChange={() => handleProjectToggle(project.id)}
                            className="mr-2 w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                          />
                          <span className="text-sm text-gray-700 dark:text-gray-300">{project.title}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Dependency Graph Link */}
                  {selectedProjects.length === 1 && (
                    <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
                      <button
                        onClick={() => handleShowGraph(selectedProjects[0])}
                        className="w-full text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-xl transition-colors"
                      >
                        View Dependency Graph →
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Desktop Search Results */}
              <div className="flex-1 min-h-0">
                {error && (
                  <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-2xl p-4 mb-4">
                    <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
                  </div>
                )}

                <div className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-xl rounded-2xl shadow-xl border border-gray-200/50 dark:border-gray-700/50 h-full flex flex-col">
                  <div className="p-6 flex-1 flex flex-col">
                    {totalResults > 0 && (
                      <div className="mb-4 flex items-center justify-between">
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                          Search Results ({totalResults})
                        </h2>
                        <button
                          onClick={clearSearch}
                          className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 font-medium"
                        >
                          Clear search
                        </button>
                      </div>
                    )}

                    <div className="flex-1 min-h-0">
                      <SearchResults
                        results={results}
                        query={query}
                        loading={loading}
                        onFileClick={handleFileClick}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Enhanced Mobile Filters Modal */}
      {showFilters && (
        <div className="lg:hidden fixed inset-0 z-50 flex items-end">
          {/* Backdrop */}
          <div 
            className="absolute inset-0 bg-black/60 backdrop-blur-sm" 
            onClick={() => setShowFilters(false)}
          />
          
          {/* Modal Content */}
          <div className="relative w-full bg-white dark:bg-gray-900 rounded-t-3xl max-h-[85vh] overflow-hidden animate-slide-up">
            {/* Handle */}
            <div className="flex justify-center pt-4 pb-2">
              <div className="w-12 h-1 bg-gray-300 dark:bg-gray-600 rounded-full"></div>
            </div>
            
            {/* Header */}
            <div className="px-6 pb-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100">Filters & Projects</h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Refine your search</p>
                </div>
                <button
                  onClick={() => setShowFilters(false)}
                  className="p-2 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            
            {/* Content */}
            <div className="px-6 py-6 overflow-y-auto max-h-[60vh] space-y-8">
              <SearchFilters
                filters={filters}
                onChange={updateFilters}
                availableLanguages={['python', 'javascript', 'typescript']}
              />

              {/* Project Selection */}
              <div className="space-y-4">
                <div className="flex items-center space-x-2">
                  <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg flex items-center justify-center">
                    <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                    </svg>
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-900 dark:text-gray-100">Projects</h4>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Select which projects to search</p>
                  </div>
                </div>
                
                <div className="grid grid-cols-1 gap-3">
                  {projects.map(project => (
                    <label 
                      key={project.id} 
                      className="flex items-center p-4 bg-gray-50 dark:bg-gray-800 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedProjects.includes(project.id)}
                        onChange={() => handleProjectToggle(project.id)}
                        className="mr-4 h-5 w-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                      />
                      <div className="flex-1">
                        <div className="font-medium text-gray-900 dark:text-gray-100">{project.title}</div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">Last updated 2 days ago</div>
                      </div>
                      <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    </label>
                  ))}
                </div>
              </div>

              {/* Dependency Graph Link */}
              {selectedProjects.length === 1 && (
                <div className="pt-6 border-t border-gray-200 dark:border-gray-700">
                  <button
                    onClick={() => {
                      handleShowGraph(selectedProjects[0]);
                      setShowFilters(false);
                    }}
                    className="w-full p-4 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-xl font-medium hover:from-blue-600 hover:to-purple-700 transition-all duration-200 shadow-lg shadow-blue-500/25"
                  >
                    <div className="flex items-center justify-center space-x-2">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                      </svg>
                      <span>View Dependency Graph</span>
                    </div>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Dependency Graph Modal */}
      {showGraph && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75" onClick={() => setShowGraph(false)} />

            <div className="inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-6xl sm:w-full">
              <div className="bg-white dark:bg-gray-800 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                    Dependency Graph
                  </h3>
                  <button
                    onClick={() => setShowGraph(false)}
                    className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>

                <DependencyGraph projectId={graphProjectId} />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}