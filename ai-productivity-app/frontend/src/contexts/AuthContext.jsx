/* AuthContext
 *
 * Purpose
 * -------
 * Global React context to manage authenticated user state, providing:
 *  • login / logout methods that call backend API and set cookies
 *  • automatic user fetch on page load (session persistence)
 *  • broadcast logout event (listens for `auth:logout` custom event from api/client.js)
 */

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
} from 'react';
import PropTypes from 'prop-types';
import client from '../api/client';
import useAuthStore from '../stores/authStore';

// Suppress duplicate /api/auth/me during StrictMode double-mount
let didFetchMeOnce = false;

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

/** @typedef {{ id: number, username: string, email: string }} User */

// -----------------------------------------------------------------------------
// Context (exported separately from Provider to avoid Fast-Refresh issues)
// -----------------------------------------------------------------------------

const AuthContextInstance = createContext({
  user: /** @type {User|null} */ (null),
  loading: true,
  login: /** @type {(username_or_email: string, password: string) => Promise<void>} */ (
    async () => {}
  ),
  logout: /** @type {() => Promise<void>} */ (async () => {}),
  refresh: /** @type {() => Promise<void>} */ (async () => {}),
});

// Named export so tests / hooks can import { AuthContext }
export const AuthContext = AuthContextInstance;

// -----------------------------------------------------------------------------
// Provider
// -----------------------------------------------------------------------------

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [initialCheckDone, setInitialCheckDone] = useState(false);
  const [isAuthenticating, setIsAuthenticating] = useState(false);

  const { startSession, endSession } = useAuthStore();

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  /**
   * Fetch the currently authenticated user from the backend.
   *
   * The `force` flag bypasses the single-run guard that avoids the duplicate
   * request caused by React 18 Strict-Mode double mounting.  This allows us to
   * re-fetch the user *after* a successful login / registration while still
   * skipping the unnecessary extra request that happens on the initial mount.
   */
  const fetchMe = useCallback(async (force = false) => {
    // Prevent duplicate requests across Strict-Mode double mounting by relying
    // on a module-level flag that survives unmounts.  Skip only when we have
    // already fetched once *and* the caller didn't explicitly request a fresh
    // fetch (e.g. right after login / registration).
    if (didFetchMeOnce && !force) {
      // Restore settled state without hitting the network.
      setLoading(false);
      setInitialCheckDone(true);
      return;
    }

    try {
      const { data } = await client.get('/api/auth/me');
      setUser(data);
    } catch (error) {
      // Non-auth failures deserve logging; 401/403 are expected when not logged in
      if (error.response?.status !== 401 && error.response?.status !== 403) {
        // eslint-disable-next-line no-console
        console.warn('Auth check failed:', error);
      }
      setUser(null);
    } finally {
      setLoading(false);
      setInitialCheckDone(true);
      didFetchMeOnce = true;
    }
  }, []);

  // Run exactly once on mount
  useEffect(() => {
    if (!initialCheckDone) {
      fetchMe();
    }
  }, [fetchMe, initialCheckDone]);

  // Listen for global logout events triggered by axios interceptor
  useEffect(() => {
    const handler = () => {
      setUser(null);
      setLoading(false);
      // Keep initialCheckDone = true so we do not automatically refetch
    };
    window.addEventListener('auth:logout', handler);
    return () => window.removeEventListener('auth:logout', handler);
  }, []);

  // ---------------------------------------------------------------------------
  // Auth API
  // ---------------------------------------------------------------------------

  const login = useCallback(
    async (username_or_email, password) => {
      if (isAuthenticating) {
        // Prevent spamming login endpoint (e.g. double-click)
        throw new Error('Authentication already in progress');
      }

      setIsAuthenticating(true);
      setLoading(true);

      try {
        await client.post('/api/auth/login', {
          username_or_email,
          password,
        });

        // Slight delay to ensure the HttpOnly cookie is set before /me request
        await new Promise((r) => setTimeout(r, 100));

        await fetchMe(true);

        // Persist last-login metadata in zustand store
        startSession(username_or_email);
      } finally {
        setIsAuthenticating(false);
        setLoading(false);
      }
    },
    [fetchMe, startSession, isAuthenticating]
  );

  const logout = useCallback(async () => {
    setLoading(true);
    try {
      await client.post('/api/auth/logout');
    } finally {
      setUser(null);
      endSession();
      setLoading(false);
      // Keep initialCheckDone = true so we do not refetch automatically
    }
  }, [endSession]);

  const refresh = (force = false) => fetchMe(force);

  /**
   * Update the authenticated user's profile (username / email / password).
   * Performs an **optimistic UI** update by immediately merging the changes
   * into the `user` state while the request is in-flight.  If the backend
   * rejects the update we roll back to the previous state so the UI remains
   * consistent.
   *
   * @param {Partial<User>} changes
   * @returns {Promise<void>}
   */
  const updateProfile = useCallback(
    async (changes) => {
      if (!user) {
        throw new Error('Not authenticated');
      }

      // Store previous snapshot for rollback in case of failure
      const prev = { ...user };

      // Apply optimistic update – only merge provided keys
      const optimisticallyUpdated = { ...user, ...changes };
      setUser(optimisticallyUpdated);

      try {
        const { data } = await client.patch('/api/auth/me', changes);
        setUser(data);
      } catch (err) {
        // Rollback and re-throw so callers can display the error
        setUser(prev);
        throw err;
      }
    },
    [user]
  );

  const value = { user, loading, login, logout, refresh, updateProfile };

  return (
    <AuthContextInstance.Provider value={value}>{children}</AuthContextInstance.Provider>
  );
}

AuthProvider.propTypes = {
  children: PropTypes.node.isRequired,
};

// -----------------------------------------------------------------------------
// Hook
// -----------------------------------------------------------------------------

export function useAuthContext() {
  return useContext(AuthContextInstance);
}
