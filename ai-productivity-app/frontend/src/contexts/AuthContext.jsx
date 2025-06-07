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

  const fetchMe = useCallback(async () => {
    // Prevent duplicate requests (e.g. React.StrictMode double-invocation)
    if (initialCheckDone && loading === false) {
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
    }
  }, [initialCheckDone, loading]);

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

        await fetchMe();

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

  const refresh = fetchMe;

  const value = { user, loading, login, logout, refresh };

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
