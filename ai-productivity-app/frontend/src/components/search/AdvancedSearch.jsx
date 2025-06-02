// frontend/src/components/search/AdvancedSearch.jsx
import React, { useState, useEffect } from 'react';
import { useSearch } from '../../hooks/useSearch';
import SearchBar from './SearchBar';
import SearchResults from './SearchResults';
import SearchFilters from './SearchFilters';
import { searchAPI } from '../../api/search';

export default function AdvancedSearch({ projectId }) {
    const [searchMode, setSearchMode] = useState('hybrid');
    const [savedSearches, setSavedSearches] = useState([]);
    const [showHistory, setShowHistory] = useState(false);

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
    } = useSearch('', { projectIds: projectId ? [projectId] : [] });

    // Load saved searches
    useEffect(() => {
        const saved = localStorage.getItem('savedSearches');
        if (saved) {
            setSavedSearches(JSON.parse(saved));
        }
    }, []);

    const handleSaveSearch = () => {
        const newSearch = {
            id: Date.now(),
            query,
            filters,
            timestamp: new Date().toISOString()
        };

        const updated = [newSearch, ...savedSearches].slice(0, 10);
        setSavedSearches(updated);
        localStorage.setItem('savedSearches', JSON.stringify(updated));
    };

    const handleLoadSearch = (search) => {
        updateQuery(search.query);
        updateFilters(search.filters);
        setShowHistory(false);
    };

    const handleModeChange = (mode) => {
        setSearchMode(mode);
        updateFilters({ ...filters, searchTypes: [mode] });
    };

    return (
        <div className="h-full flex flex-col bg-white">
            <div className="p-4 border-b">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold text-gray-900">Advanced Search</h2>
                    <div className="flex items-center space-x-2">
                        <button
                            onClick={() => setShowHistory(!showHistory)}
                            className="text-sm text-gray-600 hover:text-gray-900"
                        >
                            History
                        </button>
                        {query && (
                            <button
                                onClick={handleSaveSearch}
                                className="text-sm text-blue-600 hover:text-blue-800"
                            >
                                Save Search
                            </button>
                        )}
                    </div>
                </div>

                <SearchBar
                    value={query}
                    onChange={updateQuery}
                    placeholder="Search code, symbols, or use natural language..."
                    loading={loading}
                />

                {/* Search Mode Selector */}
                <div className="mt-4 flex items-center space-x-4">
                    <span className="text-sm text-gray-600">Mode:</span>
                    <div className="flex bg-gray-100 rounded-lg p-1">
                        {['hybrid', 'semantic', 'keyword', 'structural'].map(mode => (
                            <button
                                key={mode}
                                onClick={() => handleModeChange(mode)}
                                className={`px-3 py-1 rounded text-sm ${searchMode === mode
                                        ? 'bg-white text-gray-900 shadow-sm'
                                        : 'text-gray-600'
                                    }`}
                            >
                                {mode.charAt(0).toUpperCase() + mode.slice(1)}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Quick Examples */}
                <div className="mt-4 flex flex-wrap gap-2">
                    <span className="text-xs text-gray-500">Try:</span>
                    {[
                        'func:handleSubmit',
                        'class:UserAuth',
                        'import:react',
                        'TODO',
                        'how does authentication work?'
                    ].map(example => (
                        <button
                            key={example}
                            onClick={() => updateQuery(example)}
                            className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded hover:bg-gray-200"
                        >
                            {example}
                        </button>
                    ))}
                </div>
            </div>

            <div className="flex-1 flex overflow-hidden">
                {/* Filters Sidebar */}
                <div className="w-64 border-r p-4 overflow-y-auto">
                    <SearchFilters
                        filters={filters}
                        onChange={updateFilters}
                        availableLanguages={['python', 'javascript', 'typescript']}
                    />
                </div>

                {/* Results Area */}
                <div className="flex-1 overflow-y-auto">
                    {showHistory ? (
                        <div className="p-4">
                            <h3 className="text-sm font-medium text-gray-900 mb-4">Search History</h3>
                            {savedSearches.length > 0 ? (
                                <ul className="space-y-2">
                                    {savedSearches.map(search => (
                                        <li key={search.id}>
                                            <button
                                                onClick={() => handleLoadSearch(search)}
                                                className="w-full text-left p-3 bg-gray-50 rounded hover:bg-gray-100"
                                            >
                                                <div className="font-medium text-sm">{search.query}</div>
                                                <div className="text-xs text-gray-500">
                                                    {new Date(search.timestamp).toLocaleString()}
                                                </div>
                                            </button>
                                        </li>
                                    ))}
                                </ul>
                            ) : (
                                <p className="text-sm text-gray-500">No saved searches</p>
                            )}
                        </div>
                    ) : (
                        <div className="p-4">
                            {error && (
                                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded">
                                    <p className="text-sm text-red-600">{error}</p>
                                </div>
                            )}

                            {totalResults > 0 && (
                                <div className="mb-4 flex items-center justify-between">
                                    <span className="text-sm text-gray-600">
                                        Found {totalResults} result{totalResults !== 1 ? 's' : ''}
                                    </span>
                                    <button
                                        onClick={clearSearch}
                                        className="text-sm text-blue-600 hover:text-blue-800"
                                    >
                                        Clear
                                    </button>
                                </div>
                            )}

                            <SearchResults
                                results={results}
                                query={query}
                                loading={loading}
                            />
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
