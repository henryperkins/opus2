// useProjects.js – React-Query wrappers around project REST API
// -------------------------------------------------------------
// The previous implementation mixed Zustand store and manual axios calls.
// This version keeps the optimistic-update behaviour but delegates network
// work to TanStack Query.  Zustand store is kept for *UI-scoped* state such
// as current filters & pagination because those are not remote-authoritative
// data.

import { useMemo, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { projectAPI } from '../api/projects';

// ----------------------
// Helper keys
// ----------------------
const projectsKey = (filters) => ['projects', filters];
const projectKey = (id) => ['project', id];
const timelineKey = (id) => ['project', id, 'timeline'];

// ----------------------
// Hook: list + filters
// ----------------------
export function useProjects(filters) {
  const {
    data,
    isLoading: loading,
    error,
  } = useQuery(projectsKey(filters), () => projectAPI.list(filters), {
    keepPreviousData: true,
    staleTime: 60 * 1000,
  });

  return {
    projects: data?.items ?? [],
    total: data?.total ?? 0,
    loading,
    error,
  };
}

// ----------------------
// Hook: single project CRUD (optimistic)
// ----------------------
export function useProject(id) {
  const qc = useQueryClient();

  // Fetch
  const {
    data: project,
    isLoading: loading,
    error,
  } = useQuery(projectKey(id), () => projectAPI.get(id), { enabled: !!id });

  // Update
  const updateMutation = useMutation(
    (payload) => projectAPI.update(id, payload),
    {
      onMutate: async (payload) => {
        await qc.cancelQueries(projectKey(id));
        const prev = qc.getQueryData(projectKey(id));
        qc.setQueryData(projectKey(id), { ...prev, ...payload });
        return { prev };
      },
      onError: (_err, _vars, ctx) => qc.setQueryData(projectKey(id), ctx.prev),
      onSettled: () => qc.invalidateQueries(projectKey(id)),
    }
  );

  // Delete
  const deleteMutation = useMutation(() => projectAPI.delete(id), {
    onSuccess: () => {
      qc.invalidateQueries(projectsKey({}));
      qc.removeQueries(projectKey(id));
    },
  });

  return {
    project,
    loading,
    error,
    update: updateMutation.mutateAsync,
    remove: deleteMutation.mutateAsync,
    refresh: () => qc.invalidateQueries(projectKey(id)),
  };
}

// ----------------------
// Hook: search/list with manual trigger (legacy Sidebar API)
// ----------------------
// The sidebar component expects a `useProjectSearch()` hook that behaves like
// the old implementation: it returns the current list, a loading flag and a
// `search()` function that can be invoked manually to (re)fetch the list.  The
// modern `useProjects()` hook fetches automatically, so we wrap it and expose
// an imperative `search` that simply invalidates the underlying query or
// updates the active filters.

export function useProjectSearch(initialFilters = {}) {
  const [filters, setFilters] = useState(initialFilters);
  const qc = useQueryClient();

  const {
    projects,
    total,
    loading,
    error,
  } = useProjects(filters);

  // Imperative search function expected by Sidebar
  const search = (updatedFilters = {}) => {
    const merged = { ...filters, ...updatedFilters };
    setFilters(merged);
    // Force refetch with the newest filters
    qc.invalidateQueries(projectsKey(merged));
  };

  return {
    projects,
    total,
    loading,
    error,
    filters,
    setFilters,
    search,
  };
}

// ----------------------
// Hook: timeline for a project
// ----------------------
export function useProjectTimeline(projectId) {
  const qc = useQueryClient();

  const {
    data: timeline = [],
    isFetching: loading,
    error,
  } = useQuery(timelineKey(projectId), () => projectAPI.getTimeline(projectId), {
    enabled: !!projectId,
    staleTime: 30 * 1000,
  });

  const addEventMutation = useMutation(
    (payload) => projectAPI.addTimelineEvent(projectId, payload),
    {
      onSuccess: () => qc.invalidateQueries(timelineKey(projectId)),
    }
  );

  return useMemo(
    () => ({
      timeline,
      loading,
      error,
      addEvent: addEventMutation.mutateAsync,
      refresh: () => qc.invalidateQueries(timelineKey(projectId)),
    }),
    [timeline, loading, error, addEventMutation.mutateAsync, projectId]
  );
}
