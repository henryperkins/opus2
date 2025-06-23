import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useSearch } from '../hooks/useSearch';
import SearchBar from '../components/search/SearchBar';
import SearchResults from '../components/search/SearchResults';
import SearchFilters from '../components/search/SearchFilters';
import DependencyGraph from '../components/knowledge/DependencyGraph';
import useProjectStore from '../stores/projectStore';

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { projects, fetchProjects } = useProjectStore();
  const [selectedProjects, setSelectedProjects] = useState([]);
  const [showGraph, setShowGraph] = useState(false);
  const [graphProjectId, setGraphProjectId] = useState(null);

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

  const handleShowGraph = (projectId) => {
    setGraphProjectId(projectId);
    setShowGraph(true);
  };

  return (
    <div className="min-h-screen bg-gray-50">

      <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Code Search</h1>
          <p className="text-gray-600 mt-2">
            Search across all your code with AI-powered understanding
          </p>
        </div>

        {/* Search Bar */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <SearchBar
            value={query}
            onChange={updateQuery}
            placeholder="Search code, functions, classes, or natural language queries..."
            loading={loading}
            suggestions={true}
          />

          {/* Search Type Toggles */}
          <div className="mt-4 flex items-center space-x-4">
            <span className="text-sm text-gray-600">Search modes:</span>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={searchTypes.includes('semantic')}
                onChange={() => handleSearchTypeChange('semantic')}
                className="mr-2"
              />
              <span className="text-sm">Semantic</span>
            </label>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={searchTypes.includes('keyword')}
                onChange={() => handleSearchTypeChange('keyword')}
                className="mr-2"
              />
              <span className="text-sm">Keyword</span>
            </label>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={searchTypes.includes('structural')}
                onChange={() => handleSearchTypeChange('structural')}
                className="mr-2"
              />
              <span className="text-sm">Structural</span>
            </label>
          </div>
        </div>

        <div className="flex gap-6">
          {/* Filters Sidebar */}
          <div className="w-64 flex-shrink-0">
            <div className="bg-white rounded-lg shadow p-6">
              <SearchFilters
                filters={filters}
                onChange={updateFilters}
                availableLanguages={['python', 'javascript', 'typescript']}
              />

              {/* Project Selection */}
              <div className="mt-6 pt-6 border-t border-gray-200">
                <h3 className="text-sm font-medium text-gray-900 mb-3">Projects</h3>
                <div className="space-y-2">
                  {projects.map(project => (
                    <label key={project.id} className="flex items-center">
                      <input
                        type="checkbox"
                        checked={selectedProjects.includes(project.id)}
                        onChange={() => handleProjectToggle(project.id)}
                        className="mr-2"
                      />
                      <span className="text-sm text-gray-700">{project.title}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Dependency Graph Link */}
              {selectedProjects.length === 1 && (
                <div className="mt-6 pt-6 border-t border-gray-200">
                  <button
                    onClick={() => handleShowGraph(selectedProjects[0])}
                    className="w-full text-sm text-blue-600 hover:text-blue-800"
                  >
                    View Dependency Graph →
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Search Results */}
          <div className="flex-1">
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-6">
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}

            <div className="bg-white rounded-lg shadow">
              <div className="p-6">
                {totalResults > 0 && (
                  <div className="mb-4 flex items-center justify-between">
                    <h2 className="text-lg font-medium text-gray-900">
                      Search Results ({totalResults})
                    </h2>
                    <button
                      onClick={clearSearch}
                      className="text-sm text-blue-600 hover:text-blue-800"
                    >
                      Clear search
                    </button>
                  </div>
                )}

                <SearchResults
                  results={results}
                  query={query}
                  loading={loading}
                  onFileClick={(file) => console.log('Open file:', file)}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Dependency Graph Modal */}
      {showGraph && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75" onClick={() => setShowGraph(false)} />

            <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-6xl sm:w-full">
              <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-medium text-gray-900">
                    Dependency Graph
                  </h3>
                  <button
                    onClick={() => setShowGraph(false)}
                    className="text-gray-400 hover:text-gray-600"
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
