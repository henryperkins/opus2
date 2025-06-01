// Custom hook for code search functionality with caching and state management
import { useState, useEffect, useCallback } from 'react';
import { searchAPI } from '../api/search';
import { useDebounce } from './useDebounce';

export function useCodeSearch(initialQuery = '', initialFilters = {}) {
    const [query, setQuery] = useState(initialQuery);
    const [filters, setFilters] = useState(initialFilters);
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [totalResults, setTotalResults] = useState(0);

    const debouncedQuery = useDebounce(query, 300);

    const search = useCallback(async (searchQuery, searchFilters) => {
        if (!searchQuery || searchQuery.length < 3) {
            setResults([]);
            setTotalResults(0);
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const response = await searchAPI.search({
                query: searchQuery,
                project_ids: searchFilters.projectIds,
                filters: {
                    language: searchFilters.language,
                    file_type: searchFilters.fileType,
                    symbol_type: searchFilters.symbolType
                },
                limit: searchFilters.limit || 20
            });

            setResults(response.results);
            setTotalResults(response.total);
        } catch (err) {
            setError(err.response?.data?.detail || 'Search failed');
            setResults([]);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        search(debouncedQuery, filters);
    }, [debouncedQuery, filters, search]);

    const updateQuery = useCallback((newQuery) => {
        setQuery(newQuery);
    }, []);

    const updateFilters = useCallback((newFilters) => {
        setFilters(prev => ({ ...prev, ...newFilters }));
    }, []);

    const clearSearch = useCallback(() => {
        setQuery('');
        setFilters({});
        setResults([]);
        setTotalResults(0);
        setError(null);
    }, []);

    return {
        query,
        filters,
        results,
        loading,
        error,
        totalResults,
        updateQuery,
        updateFilters,
        clearSearch,
        search: () => search(query, filters)
    };
}
