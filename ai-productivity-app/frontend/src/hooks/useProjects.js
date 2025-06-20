/* eslint-env browser */
/**
 * useProjects.js — Custom hooks for project operations
 *
 * Strict DI: no window/document access, no side-effects on import.
 */

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  useRef,
} from 'react';
import { useAuth } from './useAuth';
import useProjectStore from '../stores/projectStore';

/* ------------------------------------------------------------------------- *
 * 1. Single-project hook
 * ------------------------------------------------------------------------- */

/**
 * Manage a single project’s lifecycle.
 * @param {number|string} id
 * @returns {{
 *   project: object|null,
 *   loading: boolean,
 *   error: string|null,
 *   fetch: () => Promise<void>,
 *   update: (data: object) => Promise<any>,
 *   remove: () => Promise<any>,
 *   clearError: () => void
 * }}
 */
export function useProject(id) {
  const {
    fetchProject,
    updateProject,
    deleteProject,
    clearError,
  } = useProjectStore();

  const currentProject = useProjectStore((s) => s.currentProject);
  const loadingStore = useProjectStore((s) => s.loading);
  const errorStore = useProjectStore((s) => s.error);

  const [isLoading, setIsLoading] = useState(false);
  const [localError, setLocalError] = useState(null);

  const fetch = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    setLocalError(null);

    try {
      await fetchProject(id);
    } catch (err) {
      setLocalError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, [fetchProject, id]);

  const update = useCallback(
    async (data) => {
      if (!id) return;
      try {
        setLocalError(null);
        return await updateProject(id, data);
      } catch (err) {
        setLocalError(err.message);
        throw err;
      }
    },
    [updateProject, id],
  );

  const remove = useCallback(
    async () => {
      if (!id) return;
      try {
        setLocalError(null);
        return await deleteProject(id);
      } catch (err) {
        setLocalError(err.message);
        throw err;
      }
    },
    [deleteProject, id],
  );

  /* stable return object */
  return useMemo(
    () => ({
      project:
        currentProject?.id === Number.parseInt(id, 10)
          ? currentProject
          : null,
      loading: isLoading || loadingStore,
      error: localError || errorStore,
      fetch,
      update,
      remove,
      clearError: () => {
        clearError();
        setLocalError(null);
      },
    }),
    [
      currentProject,
      id,
      isLoading,
      loadingStore,
      localError,
      errorStore,
      fetch,
      update,
      remove,
      clearError,
    ],
  );
}

/* ------------------------------------------------------------------------- *
 * 2. Project-timeline hook
 * ------------------------------------------------------------------------- */

/**
 * Manage timeline events for a project (auto-fetch on projectId change).
 */
export function useProjectTimeline(projectId) {
  const { fetchTimeline, addTimelineEvent, clearTimeline } = useProjectStore();
  const { user, loading: authLoading } = useAuth();
  const timeline = useProjectStore((s) => s.timeline);
  const timelineLoadingStore = useProjectStore((s) => s.timelineLoading);
  const timelineErrorStore = useProjectStore((s) => s.timelineError);

  const [isLoading, setIsLoading] = useState(false);
  const [localError, setLocalError] = useState(null);
  const lastFetchedRef = useRef(null);
  const authFailedRef = useRef(false);

  // Stable reference to fetchTimeline to avoid unnecessary re-renders
  const stableFetchTimeline = useCallback(fetchTimeline, []);

  const fetch = useCallback(async () => {
    if (!projectId) return;
    setIsLoading(true);
    setLocalError(null);
    try {
      await stableFetchTimeline(projectId);
    } catch (err) {
      setLocalError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, [stableFetchTimeline, projectId]);

  const addEvent = useCallback(
    async (eventData) => {
      if (!projectId) return;
      try {
        setLocalError(null);
        return await addTimelineEvent(projectId, eventData);
      } catch (err) {
        setLocalError(err.message);
        throw err;
      }
    },
    [addTimelineEvent, projectId],
  );

  /* auto-fetch with abort safety, only on projectId change */
  useEffect(() => {
    if (!projectId) {
      setIsLoading(false);
      setLocalError(null);
      clearTimeline(); // Clear timeline when no project
      return;
    }
    
    // Clear timeline when switching to a different project
    if (lastFetchedRef.current && lastFetchedRef.current !== projectId) {
      clearTimeline();
    }
    
    // Wait for auth to complete but don't block indefinitely
    if (authLoading) {
      console.log('Skipping timeline fetch for projectId:', projectId, '– auth loading');
      return;
    }
    
    // If not authenticated, don't fail permanently - just skip this attempt
    if (!user) {
      console.log('Skipping timeline fetch for projectId:', projectId, '– unauthenticated');
      setIsLoading(false);
      // Don't set authFailedRef here - user might authenticate later
      return;
    }

    console.log(
      'useProjectTimeline useEffect triggered for projectId:',
      projectId,
      'lastFetched:', lastFetchedRef.current,
      'authFailed:', authFailedRef.current,
    );

    const abort = new AbortController();
    const load = async () => {
      setIsLoading(true);
      setLocalError(null);
      lastFetchedRef.current = projectId;
      
      try {
        await stableFetchTimeline(projectId, { signal: abort.signal });
        authFailedRef.current = false; // Reset on successful fetch
        console.log('Timeline fetch successful for projectId:', projectId);
      } catch (err) {
        if (!abort.signal.aborted) {
          const errorMessage = err.response?.data?.detail || err.message || 'Failed to fetch timeline';
          setLocalError(errorMessage);
          
          // Only block future requests for persistent auth failures, not transient errors
          if (err.response?.status === 401) {
            console.log('Authentication failed (401) for projectId:', projectId);
            authFailedRef.current = true;
          } else {
            console.log('Timeline fetch failed (non-auth error):', errorMessage);
            // Don't block future attempts for non-auth errors
          }
        }
      } finally {
        if (!abort.signal.aborted) setIsLoading(false);
      }
    };

    // Reset auth failed flag when switching projects or when user changes
    if (lastFetchedRef.current !== projectId) {
      authFailedRef.current = false;
    }

    // Don't fetch if permanently blocked by auth failure for this session
    if (authFailedRef.current) {
      console.log('Skipping timeline fetch due to auth failure for projectId:', projectId);
      setIsLoading(false);
      setLocalError('Authentication required');
    } else if (lastFetchedRef.current !== projectId) {
      console.log('Fetching timeline for projectId:', projectId);
      load();
    } else {
      console.log('Skipping timeline fetch, already fetched for projectId:', projectId);
      setIsLoading(false);
    }

    return () => abort.abort();
  }, [projectId, stableFetchTimeline, authLoading, user]);

  return {
    timeline,
    loading: isLoading || timelineLoadingStore,
    error: localError || timelineErrorStore,
    fetch,
    addEvent,
    clearError: () => setLocalError(null),
  };
}

/* ------------------------------------------------------------------------- *
 * 3. Project-search hook
 * ------------------------------------------------------------------------- */

/* tiny util for debounce without extra deps */
function useDebouncedValue(value, delay = 300) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    // eslint-disable-next-line no-undef
    const t = setTimeout(() => setDebounced(value), delay);
    // eslint-disable-next-line no-undef
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

/**
 * Search & filter projects (debounced).
 */
export function useProjectSearch() {
  const {
    projects,
    totalProjects,
    filters,
    loading,
    error,
  } = useProjectStore((s) => ({
    projects: s.projects,
    totalProjects: s.totalProjects,
    filters: s.filters,
    loading: s.loading,
    error: s.error,
  }));
  const { fetchProjects, setFilters } = useProjectStore();

  const [searchTerm, setSearchTerm] = useState(filters.search || '');
  const debouncedSearch = useDebouncedValue(searchTerm);

  /* push debounced value into global filters */
  useEffect(() => {
    if (debouncedSearch !== filters.search) {
      setFilters({ search: debouncedSearch });
    }
  }, [debouncedSearch, filters.search, setFilters]);

  const search = useCallback(
    (newFilters = {}) => {
      setFilters(newFilters);
      return fetchProjects();
    },
    [setFilters, fetchProjects],
  );

  const clearSearch = useCallback(() => {
    setSearchTerm('');
    setFilters({
      search: '',
      tags: [],
      status: null,
      page: 1,
    });
  }, [setFilters]);

  return {
    projects,
    totalProjects,
    filters,
    loading,
    error,
    searchTerm,
    setSearchTerm,
    search,
    clearSearch,
    setFilters,
  };
}

/* ------------------------------------------------------------------------- *
 * 4. Project-creation hook
 * ------------------------------------------------------------------------- */

/**
 * Validate and create projects.
 */
export function useProjectCreation() {
  const { createProject } = useProjectStore();
  const { loading, error } = useProjectStore((s) => ({
    loading: s.loading,
    error: s.error,
  }));
  const [validationErrors, setValidationErrors] = useState({});

  const validateProjectData = useCallback((data) => {
    const errors = {};

    if (!data.title?.trim()) {
      errors.title = 'Title is required';
    } else if (data.title.length > 200) {
      errors.title = 'Title must be 200 characters or less';
    }

    if (data.description && data.description.length > 2000) {
      errors.description = 'Description must be 2000 characters or less';
    }

    if (data.color && !/^#[0-9A-Fa-f]{6}$/.test(data.color)) {
      errors.color = 'Invalid color format';
    }

    if (data.tags && data.tags.length > 20) {
      errors.tags = 'Maximum 20 tags allowed';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  }, []);

  const create = useCallback(
    async (data) => {
      if (!validateProjectData(data)) {
        throw new Error('Validation failed');
      }
      return createProject(data);
    },
    [createProject, validateProjectData],
  );

  return {
    create,
    loading,
    error,
    validationErrors,
    validateProjectData,
    clearValidationErrors: () => setValidationErrors({}),
  };
}
