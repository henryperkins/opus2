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

      // Clear all stored data (for logout)
      clearStore: () => {
        set({
          preferences: {
            rememberMe: false,
            lastUsername: '',
            theme: 'light',
            language: 'en',
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