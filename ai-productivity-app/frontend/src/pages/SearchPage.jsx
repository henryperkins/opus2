// Main search page with unified search interface and results
import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useCodeSearch } from '../hooks/useCodeSearch';
import SearchBar from '../components/search/SearchBar';
import SearchResults from '../components/search/SearchResults';
import SearchFilters from '../components/search/SearchFilters';
import useProjectStore from '../stores/projectStore';
import Header from '../components/common/Header';

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { projects } = useProjectStore();
  const [selectedProjects, setSelectedProjects] = useState([]);

  const {
    query,
    filters,
    results,
    loading,
    error,
    totalResults,
    updateQuery,
    updateFilters,
    clearSearch
  } = useCodeSearch(searchParams.get('q') || '');

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
    useProjectStore.getState().fetchProjects();
  }, []);

  const handleProjectToggle = (projectId) => {
    setSelectedProjects(prev => {
      const newSelection = prev.includes(projectId)
        ? prev.filter(id => id !== projectId)
        : [...prev, projectId];

      updateFilters({ projectIds: newSelection });
      return newSelection;
    });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />

      <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Code Search</h1>
          <p className="text-gray-600 mt-2">
            Search across all your code with semantic understanding
          </p>
        </div>

        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <SearchBar
            value={query}
            onChange={updateQuery}
            placeholder="Search code, functions, classes, or use @project tags..."
            loading={loading}
          />
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
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
