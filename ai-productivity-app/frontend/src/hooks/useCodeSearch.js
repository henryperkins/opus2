// useCodeSearch.js – Code-aware search hook built on React-Query
// -------------------------------------------------------------
// Very similar to generic `useSearch`, but enforces a longer minimum query
// length (3) and omits hybrid/semantic toggling.

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { searchAPI } from '../api/search';
import { useDebounce } from './useDebounce';

const MIN_QUERY_LENGTH = 3;

function searchCode({ queryKey }) {
  const [, { q, filters }] = queryKey;
  return searchAPI.search({
    query: q,
    project_ids: filters.projectIds,
    filters: {
      language: filters.language,
      file_type: filters.fileType,
      symbol_type: filters.symbolType,
    },
    limit: filters.limit || 20,
    search_types: ['code'],
  });
}

export function useCodeSearch(initialQuery = '', initialFilters = {}) {
  const [query, setQuery] = useState(initialQuery);
  const [filters, setFilters] = useState(initialFilters);

  const debouncedQuery = useDebounce(query, 500);
  // Ensure `enabled` is always a boolean. Using a raw logical-AND with a
  // string can leak the string value (""), which React-Query rejects.
  const enabled = !!debouncedQuery && debouncedQuery.length >= MIN_QUERY_LENGTH;

  const { data, isFetching: loading, error } = useQuery({
    queryKey: ['codeSearch', { q: debouncedQuery, filters }],
    queryFn: searchCode,
    enabled,
    keepPreviousData: true,
    staleTime: 60 * 1000,
  });

  const updateQuery = (q) => setQuery(q);
  const updateFilters = (f) => setFilters((prev) => ({ ...prev, ...f }));

  const clearSearch = () => {
    setQuery('');
    setFilters({});
  };

  return useMemo(
    () => {
      const results = data?.results ?? [];
      const totalResults = data?.total ?? 0;
      
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
      };
    },
    [query, filters, data, loading, error]
  );
}
