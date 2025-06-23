// useSearch.js – React-Query powered global search hook
// -----------------------------------------------------
// Provides debounced, cached search results with support for query + filter
// parameters.  Replaces the previous SWR/axios implementation.

import { useState, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useDebounce } from './useDebounce';
import { searchAPI } from '../api/search';

const MIN_QUERY_LENGTH = 2;

function searchFn({ queryKey }) {
  const [_key, { q, filters, types }] = queryKey;
  return searchAPI.search({
    query: q,
    project_ids: filters.projectIds,
    filters: {
      language: filters.language,
      file_type: filters.fileType,
      symbol_type: filters.symbolType,
      tags: filters.tags,
    },
    limit: filters.limit || 20,
    search_types: types,
  });
}

export function useSearch(initialQuery = '', initialFilters = {}) {
  const [query, setQuery] = useState(initialQuery);
  const [filters, setFilters] = useState(initialFilters);
  const [searchTypes, setSearchTypes] = useState(['hybrid']);

  const debouncedQuery = useDebounce(query, 300);

  const enabled = debouncedQuery && debouncedQuery.length >= MIN_QUERY_LENGTH;

  const {
    data,
    isFetching: loading,
    error,
  } = useQuery({
    queryKey: ['search', { q: debouncedQuery, filters, types: searchTypes }],
    queryFn: searchFn,
    enabled,
    keepPreviousData: true,
    staleTime: 60 * 1000,
  });

  const results = data?.results ?? [];
  const totalResults = data?.total ?? 0;

  // Helpers
  const updateQuery = (q) => setQuery(q);
  const updateFilters = (f) => setFilters((prev) => ({ ...prev, ...f }));
  const updateSearchTypes = (types) => setSearchTypes(types);

  const clearSearch = () => {
    setQuery('');
    setFilters({});
    const qc = useQueryClient();
    qc.removeQueries({ queryKey: ['search'] });
  };

  const indexDocument = async (documentId, options) => {
    const res = await searchAPI.indexDocument(documentId, options);
    return res;
  };

  return useMemo(
    () => ({
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
      search: () => {}, // no-op; React-Query handles automatic fetch
      indexDocument,
    }),
    [
      query,
      filters,
      results,
      loading,
      error,
      totalResults,
      searchTypes,
    ]
  );
}
