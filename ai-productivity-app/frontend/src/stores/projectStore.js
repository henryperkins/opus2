/**
 * Project state management with Zustand
 *
 * Handles project CRUD operations, filtering, and optimistic updates
 * for a responsive user experience.
 */
import { create } from 'zustand';
import { projectAPI } from '../api/projects';

const useProjectStore = create((set, get) => ({
  // State
  projects: [],
  currentProject: null,
  timeline: [],
  loading: false,
  timelineLoading: false,
  error: null,
  timelineError: null,
  filters: {
    status: null,
    tags: [],
    search: '',
    page: 1,
    per_page: 20
  },
  totalProjects: 0,
  lastFetch: null,
  fetchInProgress: false,

  // Actions (flattened to root level for easier access)
  setFilters: (newFilters) => {
    set(state => ({
      filters: { ...state.filters, ...newFilters, page: 1 }
    }));
  },

  setPage: (page) => {
    set(state => ({
      filters: { ...state.filters, page }
    }));
  },

  fetchProjects: async (force = false) => {
    const { filters, fetchInProgress, lastFetch } = get();
    
    // Prevent duplicate calls within 30 seconds unless forced
    const now = Date.now();
    if (!force && fetchInProgress) {
      console.log('Project fetch already in progress, skipping...');
      return;
    }
    if (!force && lastFetch && (now - lastFetch) < 30000) {
      console.log('Recent project fetch found, skipping...');
      return;
    }

    set({ loading: true, error: null, fetchInProgress: true });

    try {
      const response = await projectAPI.list(filters);
      set({
        projects: response.items,
        totalProjects: response.total,
        loading: false,
        fetchInProgress: false,
        lastFetch: now
      });
    } catch (error) {
      set({
        error: error.response?.data?.detail || 'Failed to fetch projects',
        loading: false,
        fetchInProgress: false
      });
      throw error;
    }
  },

  fetchProject: async (id) => {
    set({ loading: true, error: null });

    try {
      const project = await projectAPI.get(id);
      set({
        currentProject: project,
        loading: false
      });
      return project;
    } catch (error) {
      set({
        error: error.response?.data?.detail || 'Failed to fetch project',
        loading: false
      });
      throw error;
    }
  },

  createProject: async (data) => {
    set({ loading: true, error: null });

    // Optimistic update
    const tempId = `temp_${Date.now()}`;
    const tempProject = {
      ...data,
      id: tempId,
      status: data.status || 'active',
      owner: { id: 0, username: 'You' },
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };

    set(state => ({
      projects: [tempProject, ...state.projects],
      totalProjects: state.totalProjects + 1
    }));

    try {
      const project = await projectAPI.create(data);

      // Replace temp with real project
      set(state => ({
        projects: state.projects.map(p =>
          p.id === tempId ? project : p
        ),
        loading: false
      }));

      return project;
    } catch (error) {
      // Rollback optimistic update
      set(state => ({
        projects: state.projects.filter(p => p.id !== tempId),
        totalProjects: state.totalProjects - 1,
        error: error.response?.data?.detail || 'Failed to create project',
        loading: false
      }));
      throw error;
    }
  },

  updateProject: async (id, data) => {
    set({ loading: true, error: null });

    // Store original for rollback
    const { projects } = get();
    const original = projects.find(p => p.id === id);

    if (!original) {
      set({ error: 'Project not found', loading: false });
      return;
    }

    // Optimistic update
    set(state => ({
      projects: state.projects.map(p =>
        p.id === id ? { ...p, ...data, updated_at: new Date().toISOString() } : p
      )
    }));

    try {
      const updated = await projectAPI.update(id, data);

      // Replace with server response
      set(state => ({
        projects: state.projects.map(p => p.id === id ? updated : p),
        currentProject: state.currentProject?.id === id ? updated : state.currentProject,
        loading: false
      }));

      return updated;
    } catch (error) {
      // Rollback
      set(state => ({
        projects: state.projects.map(p => p.id === id ? original : p),
        error: error.response?.data?.detail || 'Failed to update project',
        loading: false
      }));
      throw error;
    }
  },

  deleteProject: async (id) => {
    set({ loading: true, error: null });

    // Store for rollback
    const { projects, totalProjects } = get();
    const original = projects.find(p => p.id === id);
    const originalIndex = projects.findIndex(p => p.id === id);

    // Optimistic delete
    set(state => ({
      projects: state.projects.filter(p => p.id !== id),
      totalProjects: state.totalProjects - 1
    }));

    try {
      await projectAPI.delete(id);
      set({ loading: false });
    } catch (error) {
      // Rollback
      if (original && originalIndex >= 0) {
        set(state => {
          const newProjects = [...state.projects];
          newProjects.splice(originalIndex, 0, original);
          return {
            projects: newProjects,
            totalProjects: totalProjects,
            error: error.response?.data?.detail || 'Failed to delete project',
            loading: false
          };
        });
      }
      throw error;
    }
  },

  archiveProject: async (id) => {
    const { updateProject } = get();
    return updateProject(id, { status: 'archived' });
  },

  unarchiveProject: async (id) => {
    const { updateProject } = get();
    return updateProject(id, { status: 'active' });
  },

  fetchTimeline: async (projectId) => {
    set({ timelineLoading: true, timelineError: null });

    try {
      const timeline = await projectAPI.getTimeline(projectId);
      set({
        timeline,
        timelineLoading: false
      });
    } catch (error) {
      set({
        timelineError: error.response?.data?.detail || 'Failed to fetch timeline',
        timelineLoading: false
      });
      throw error; // Re-throw to allow caller to handle
    }
  },

  addTimelineEvent: async (projectId, eventData) => {
    // Don't set loading state for adding events - it's non-blocking
    try {
      const newEvent = await projectAPI.addTimelineEvent(projectId, eventData);
      set(state => ({
        timeline: [...state.timeline, newEvent].sort((a, b) => new Date(b.created_at || b.timestamp) - new Date(a.created_at || a.timestamp))
      }));
      return newEvent;
    } catch (error) {
      set({
        timelineError: error.response?.data?.detail || 'Failed to add timeline event'
      });
      throw error;
    }
  },

  clearError: () => set({ error: null }),
  clearTimelineError: () => set({ timelineError: null }),
  clearTimeline: () => set({ timeline: [], timelineError: null, timelineLoading: false })
}));

export default useProjectStore;
