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
  error: null,
  filters: {
    status: null,
    tags: [],
    search: '',
    page: 1,
    per_page: 20
  },
  totalProjects: 0,

  // Actions
  actions: {
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

    fetchProjects: async () => {
      const { filters } = get();
      set({ loading: true, error: null });

      try {
        const response = await projectAPI.list(filters);
        set({
          projects: response.items,
          totalProjects: response.total,
          loading: false
        });
      } catch (error) {
        set({
          error: error.response?.data?.detail || 'Failed to fetch projects',
          loading: false
        });
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
      const { actions } = get();
      return actions.updateProject(id, { status: 'archived' });
    },

    fetchTimeline: async (projectId) => {
      set({ loading: true, error: null });

      try {
        const timeline = await projectAPI.timeline(projectId);
        set({
          timeline,
          loading: false
        });
      } catch (error) {
        set({
          error: error.response?.data?.detail || 'Failed to fetch timeline',
          loading: false
        });
      }
    },

    addTimelineEvent: async (projectId, eventData) => {
      set({ loading: true, error: null });

      try {
        const newEvent = await projectAPI.addTimelineEvent(projectId, eventData);
        set(state => ({
          timeline: [...state.timeline, newEvent].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)),
          loading: false
        }));
        return newEvent;
      } catch (error) {
        set({
          error: error.response?.data?.detail || 'Failed to add timeline event',
          loading: false
        });
        throw error;
      }
    },

    clearError: () => set({ error: null }),
  }
}));

export default useProjectStore;
