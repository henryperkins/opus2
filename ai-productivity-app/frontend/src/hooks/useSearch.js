// frontend/src/hooks/useSearch.js
import { useState, useEffect, useCallback, useRef } from 'react';
import { searchAPI } from '../api/search';
import { useDebounce } from './useDebounce';

export function useSearch(initialQuery = '', initialFilters = {}) {
    const [query, setQuery] = useState(initialQuery);
    const [filters, setFilters] = useState(initialFilters);
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [totalResults, setTotalResults] = useState(0);
    const [searchTypes, setSearchTypes] = useState(['hybrid']);

    const debouncedQuery = useDebounce(query, 300);
    const abortControllerRef = useRef();

    const search = useCallback(async (searchQuery, searchFilters, types) => {
        // Abort previous request
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        if (!searchQuery || searchQuery.length < 2) {
            setResults([]);
            setTotalResults(0);
            return;
        }

        setLoading(true);
        setError(null);

        // Create new abort controller
        abortControllerRef.current = new AbortController();

        try {
            const response = await searchAPI.search({
                query: searchQuery,
                project_ids: searchFilters.projectIds,
                filters: {
                    language: searchFilters.language,
                    file_type: searchFilters.fileType,
                    symbol_type: searchFilters.symbolType,
                    tags: searchFilters.tags
                },
                limit: searchFilters.limit || 20,
                search_types: types
            });

            setResults(response.results);
            setTotalResults(response.total);
            setSearchTypes(response.search_types);
        } catch (err) {
            if (err.name !== 'AbortError') {
                setError(err.response?.data?.detail || 'Search failed');
                setResults([]);
            }
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        search(debouncedQuery, filters, searchTypes);
    }, [debouncedQuery, filters, searchTypes, search]);

    const updateQuery = useCallback((newQuery) => {
        setQuery(newQuery);
    }, []);

    const updateFilters = useCallback((newFilters) => {
        setFilters(prev => ({ ...prev, ...newFilters }));
    }, []);

    const updateSearchTypes = useCallback((types) => {
        setSearchTypes(types);
    }, []);

    const clearSearch = useCallback(() => {
        setQuery('');
        setFilters({});
        setResults([]);
        setTotalResults(0);
        setError(null);
    }, []);

    const indexDocument = useCallback(async (documentId, options) => {
        try {
            const response = await searchAPI.indexDocument(documentId, options);
            return response;
        } catch (err) {
            throw new Error(err.response?.data?.detail || 'Indexing failed');
        }
    }, []);

    return {
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
        clearSearch,
        search: () => search(query, filters, searchTypes),
        indexDocument
    };
}
