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
  } = useProjectStore((s) => s.actions);

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
  const { fetchTimeline, addTimelineEvent } = useProjectStore(
    (s) => s.actions,
  );
  const timeline = useProjectStore((s) => s.timeline);
  const loadingStore = useProjectStore((s) => s.loading);
  const errorStore = useProjectStore((s) => s.error);

  const [isLoading, setIsLoading] = useState(false);
  const [localError, setLocalError] = useState(null);
  const lastFetchedRef = useRef(null);

  const fetch = useCallback(async () => {
    if (!projectId) return;
    setIsLoading(true);
    setLocalError(null);
    try {
      await fetchTimeline(projectId);
    } catch (err) {
      setLocalError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, [fetchTimeline, projectId]);

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

  /* auto-fetch with abort safety */
  useEffect(() => {
    if (!projectId || lastFetchedRef.current === projectId) return;

    const abort = new AbortController();
    const load = async () => {
      setIsLoading(true);
      setLocalError(null);
      lastFetchedRef.current = projectId;
      try {
        await fetchTimeline(projectId, { signal: abort.signal });
      } catch (err) {
        if (!abort.signal.aborted) setLocalError(err.message);
      } finally {
        if (!abort.signal.aborted) setIsLoading(false);
      }
    };

    load();
    return () => abort.abort();
  }, [projectId, fetchTimeline]);

  return {
    timeline,
    loading: isLoading || loadingStore,
    error: localError || errorStore,
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
    const t = setTimeout(() => setDebounced(value), delay);
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
  const { fetchProjects, setFilters } = useProjectStore((s) => s.actions);

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
  const { createProject } = useProjectStore((s) => s.actions);
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
