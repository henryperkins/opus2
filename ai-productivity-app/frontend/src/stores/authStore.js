/* Authentication Store (Zustand)
 *
 * Purpose
 * -------
 * Persistent auth state management with Zustand for:
 *  " User session persistence across page refreshes
 *  " User preferences and settings
 *  " Last login timestamp tracking
 *  " Remember me functionality
 *
 * This complements the React Context by providing persistent storage
 * for user preferences that should survive page reloads.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const useAuthStore = create(
  persist(
    (set, get) => ({
      // Persistent user preferences
      preferences: {
        rememberMe: false,
        lastUsername: '',
        theme: 'light',
        language: 'en',
        sidebarPinned: false,
        sidebarWidth: 280, // Default sidebar width in pixels
        // Use Map-like object for flexible section state management
        collapsedSections: {},
      },

      // Session metadata
      sessionMetadata: {
        lastLoginTime: null,
        sessionStartTime: null,
        deviceId: null,
      },

      // Actions to update preferences
      setPreference: (key, value) => {
        set((state) => ({
          preferences: {
            ...state.preferences,
            [key]: value,
          },
        }));
      },

      setPreferences: (newPreferences) => {
        set((state) => ({
          preferences: {
            ...state.preferences,
            ...newPreferences,
          },
        }));
      },

      // Session management
      startSession: (username) => {
        const now = new Date().toISOString();
        set((state) => ({
          preferences: {
            ...state.preferences,
            lastUsername: username,
          },
          sessionMetadata: {
            ...state.sessionMetadata,
            lastLoginTime: now,
            sessionStartTime: now,
          },
        }));
      },

      endSession: () => {
        set((state) => ({
          sessionMetadata: {
            ...state.sessionMetadata,
            sessionStartTime: null,
          },
        }));
      },

      // Generate or get device ID for security tracking
      getDeviceId: () => {
        const state = get();
        if (!state.sessionMetadata.deviceId) {
          const deviceId = 'device_' + Math.random().toString(36).substr(2, 9);
          set((state) => ({
            sessionMetadata: {
              ...state.sessionMetadata,
              deviceId,
            },
          }));
          return deviceId;
        }
        return state.sessionMetadata.deviceId;
      },

      // Helper to check if user should be remembered
      shouldRememberUser: () => {
        const state = get();
        return state.preferences.rememberMe && state.preferences.lastUsername;
      },

      // Sidebar-specific preference setters
      setSidebarPinned: (pinned) => {
        set((state) => ({
          preferences: {
            ...state.preferences,
            sidebarPinned: pinned,
          },
        }));
      },

      setSidebarWidth: (width) => {
        // Ensure width is within reasonable bounds
        const clampedWidth = Math.max(200, Math.min(600, width));
        set((state) => ({
          preferences: {
            ...state.preferences,
            sidebarWidth: clampedWidth,
          },
        }));
      },

      setCollapsedSection: (section, collapsed) => {
        set((state) => ({
          preferences: {
            ...state.preferences,
            collapsedSections: {
              ...state.preferences.collapsedSections,
              [section]: collapsed,
            },
          },
        }));
      },

      // Helper to get collapsed state with sensible defaults
      getSectionCollapsed: (section) => {
        const state = get();
        // Ensure we handle legacy persisted data where collapsedSections
        // may be undefined by providing a safe fallback object.
        const collapsedSections = state?.preferences?.collapsedSections || {};
        const defaults = {
          recent: false,
          starred: true,
          projects: false,
          help: true,
        };
        return collapsedSections[section] ?? defaults[section] ?? false;
      },

      // Clear all stored data (for logout)
      clearStore: () => {
        set({
          preferences: {
            rememberMe: false,
            lastUsername: '',
            theme: 'light',
            language: 'en',
            sidebarPinned: false,
            collapsedSections: {},
          },
          sessionMetadata: {
            lastLoginTime: null,
            sessionStartTime: null,
            deviceId: null,
          },
        });
      },

      // Helper to get last login info for display
      getLastLoginInfo: () => {
        const state = get();
        return {
          username: state.preferences.lastUsername,
          timestamp: state.sessionMetadata.lastLoginTime,
        };
      },
    }),
    {
      name: 'ai-productivity-auth',
      version: 1,
      // Only persist preferences and session metadata, not sensitive data
      partialize: (state) => ({
        preferences: state.preferences,
        sessionMetadata: {
          lastLoginTime: state.sessionMetadata.lastLoginTime,
          deviceId: state.sessionMetadata.deviceId,
          // Don't persist sessionStartTime - that should be fresh each session
        },
      }),
    }
  )
);

export default useAuthStore;
