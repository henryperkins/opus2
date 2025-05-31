/**
 * useProjects.js: Custom hooks for project operations
 * 
 * Provides convenient hooks for common project operations including
 * single project fetching, timeline management, and search functionality.
 */
import { useCallback, useEffect, useState } from "react";
import useProjectStore from "../stores/projectStore";

/**
 * Hook for managing a single project with caching
 */
export function useProject(id) {
  const { 
    currentProject, 
    fetchProject, 
    updateProject, 
    deleteProject,
    loading,
    error 
  } = useProjectStore();
  
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

  const update = useCallback(async (data) => {
    if (!id) return;
    
    try {
      setLocalError(null);
      return await updateProject(id, data);
    } catch (err) {
      setLocalError(err.message);
      throw err;
    }
  }, [updateProject, id]);

  const remove = useCallback(async () => {
    if (!id) return;
    
    try {
      setLocalError(null);
      return await deleteProject(id);
    } catch (err) {
      setLocalError(err.message);
      throw err;
    }
  }, [deleteProject, id]);

  return {
    project: currentProject?.id === parseInt(id) ? currentProject : null,
    loading: isLoading || loading,
    error: localError || error,
    fetch,
    update,
    delete: remove,
    clearError: () => setLocalError(null)
  };
}

/**
 * Hook for managing project timeline events
 */
export function useProjectTimeline(projectId) {
  const { 
    timeline, 
    fetchTimeline, 
    addTimelineEvent,
    loading,
    error 
  } = useProjectStore();
  
  const [isLoading, setIsLoading] = useState(false);
  const [localError, setLocalError] = useState(null);

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

  const addEvent = useCallback(async (eventData) => {
    if (!projectId) return;
    
    try {
      setLocalError(null);
      return await addTimelineEvent(projectId, eventData);
    } catch (err) {
      setLocalError(err.message);
      throw err;
    }
  }, [addTimelineEvent, projectId]);

  // Auto-fetch timeline when projectId changes
  useEffect(() => {
    if (projectId) {
      fetch();
    }
  }, [projectId, fetch]);

  return {
    timeline,
    loading: isLoading || loading,
    error: localError || error,
    fetch,
    addEvent,
    clearError: () => setLocalError(null)
  };
}

/**
 * Hook for project search and filtering with debouncing
 */
export function useProjectSearch() {
  const { 
    projects, 
    totalProjects,
    fetchProjects, 
    setFilters,
    filters,
    loading,
    error 
  } = useProjectStore();
  
  const [searchTerm, setSearchTerm] = useState(filters.search || '');
  const [debouncedSearch, setDebouncedSearch] = useState(searchTerm);

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchTerm);
    }, 300);

    return () => clearTimeout(timer);
  }, [searchTerm]);

  // Update filters when debounced search changes
  useEffect(() => {
    if (debouncedSearch !== filters.search) {
      setFilters({ search: debouncedSearch });
    }
  }, [debouncedSearch, filters.search, setFilters]);

  const search = useCallback((newFilters = {}) => {
    setFilters(newFilters);
    return fetchProjects();
  }, [setFilters, fetchProjects]);

  const clearSearch = useCallback(() => {
    setSearchTerm('');
    setFilters({ 
      search: '', 
      tags: [], 
      status: null,
      page: 1 
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
    setFilters
  };
}

/**
 * Hook for project creation with validation
 */
export function useProjectCreation() {
  const { createProject, loading, error } = useProjectStore();
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

  const create = useCallback(async (data) => {
    if (!validateProjectData(data)) {
      throw new Error('Validation failed');
    }
    
    try {
      return await createProject(data);
    } catch (err) {
      throw err;
    }
  }, [createProject, validateProjectData]);

  return {
    create,
    loading,
    error,
    validationErrors,
    validateProjectData,
    clearValidationErrors: () => setValidationErrors({})
  };
}
