// useProjects.js – React-Query wrappers around project REST API
// -------------------------------------------------------------
// The previous implementation mixed Zustand store and manual axios calls.
// This version keeps the optimistic-update behaviour but delegates network
// work to TanStack Query.  Zustand store is kept for *UI-scoped* state such
// as current filters & pagination because those are not remote-authoritative
// data.

import { useMemo, useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { projectAPI } from "../api/projects";

// ----------------------
// Helper keys
// ----------------------
const projectsKey = (filters) => ["projects", filters];
const projectKey = (id) => ["project", id];
const timelineKey = (id) => ["project", id, "timeline"];

// ----------------------
// Hook: list + filters
// ----------------------
export function useProjects(filters) {
  const {
    data,
    isLoading: loading,
    error,
  } = useQuery({
    queryKey: projectsKey(filters),
    queryFn: () => projectAPI.list(filters),
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
  } = useQuery({
    queryKey: projectKey(id),
    queryFn: () => projectAPI.get(id),
    enabled: !!id,
  });

  // Update
  const updateMutation = useMutation({
    mutationFn: (payload) => projectAPI.update(id, payload),
    onMutate: async (payload) => {
      await qc.cancelQueries({ queryKey: projectKey(id) });
      const prev = qc.getQueryData(projectKey(id));
      qc.setQueryData(projectKey(id), { ...prev, ...payload });
      return { prev };
    },
    onError: (_err, _vars, ctx) => qc.setQueryData(projectKey(id), ctx.prev),
    onSettled: () => qc.invalidateQueries({ queryKey: projectKey(id) }),
  });

  // Delete
  const deleteMutation = useMutation({
    mutationFn: () => projectAPI.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: projectsKey({}) });
      qc.removeQueries({ queryKey: projectKey(id) });
    },
  });

  return {
    project,
    loading,
    error,
    update: updateMutation.mutateAsync,
    remove: deleteMutation.mutateAsync,
    refresh: () => qc.invalidateQueries({ queryKey: projectKey(id) }),
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

  const { projects, total, loading, error } = useProjects(filters);

  // Imperative search function expected by Sidebar – memoised so that its
  // reference stays *stable* across renders and does not inadvertently cause
  // effects in consuming components to re-run.
  const search = useCallback(
    (updatedFilters = {}) => {
      setFilters((prev) => {
        const merged = { ...prev, ...updatedFilters };
        qc.invalidateQueries({ queryKey: projectsKey(merged) });
        return merged;
      });
    },
    [qc],
  );

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
  } = useQuery({
    queryKey: timelineKey(projectId),
    queryFn: () => projectAPI.getTimeline(projectId),
    enabled: !!projectId,
    staleTime: 30 * 1000,
  });

  const addEventMutation = useMutation({
    mutationFn: (payload) => projectAPI.addTimelineEvent(projectId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: timelineKey(projectId) }),
  });

  return useMemo(
    () => ({
      timeline,
      loading,
      error,
      addEvent: addEventMutation.mutateAsync,
      refresh: () => qc.invalidateQueries({ queryKey: timelineKey(projectId) }),
    }),
    // Include qc to satisfy exhaustive-deps; invalidateQueries reference stable for same qc
    [timeline, loading, error, addEventMutation.mutateAsync, projectId, qc],
  );
}
