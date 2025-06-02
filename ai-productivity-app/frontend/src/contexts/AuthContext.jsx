/* AuthContext
 *
 * Purpose
 * -------
 * Global React context to manage authenticated user state, providing:
 *  • login / logout methods that call backend API and set cookies
 *  • automatic user fetch on page load (session persistence)
 *  • broadcast logout event (listens for `auth:logout` custom event from api/client.js)
 *
 * This is the backbone for Phase-2 frontend auth. A separate hook (useAuth.js)
 * will consume this context to offer a convenient API to components.
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
// Context
// -----------------------------------------------------------------------------

const AuthContext = createContext({
  user: /** @type {User|null} */ (null),
  loading: true,
  login: /** @type {(username: string, password: string) => Promise<void>} */ (
    async () => {}
  ),
  logout: /** @type {() => Promise<void>} */ (async () => {}),
  refresh: /** @type {() => Promise<void>} */ (async () => {}),
});

// -----------------------------------------------------------------------------
// Provider
// -----------------------------------------------------------------------------

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [initialCheckDone, setInitialCheckDone] = useState(false);
  const { startSession, endSession, shouldRememberUser, getLastLoginInfo } = useAuthStore();

  // --- helper to fetch /me
  const fetchMe = useCallback(async () => {
    // Prevent duplicate requests in development strict mode
    if (initialCheckDone && loading === false) {
      return;
    }
    
    try {
      const { data } = await client.get('/api/auth/me');
      setUser(data);
    } catch (error) {
      // Only log unexpected errors (not 401/403 which are normal when not logged in)
      if (error.response?.status !== 401 && error.response?.status !== 403) {
        console.warn('Auth check failed:', error);
      }
      setUser(null);
    } finally {
      setLoading(false);
      setInitialCheckDone(true);
    }
  }, [initialCheckDone, loading]);

  // Initial load - only run once
  useEffect(() => {
    if (!initialCheckDone) {
      fetchMe();
    }
  }, [fetchMe, initialCheckDone]);

  // Listen for global logout events (401 interception)
  useEffect(() => {
    const handler = () => {
      setUser(null);
      setLoading(false);
      // Don't reset initialCheckDone to prevent re-fetching
    };
    window.addEventListener('auth:logout', handler);
    return () => window.removeEventListener('auth:logout', handler);
  }, []);

  // --- login
  const login = useCallback(async (username, password) => {
    setLoading(true);
    try {
      await client.post('/api/auth/login', {
        username_or_email: username,
        password,
      });
      await fetchMe();
      // Update auth store with session info
      startSession(username);
    } finally {
      setLoading(false);
    }
  }, [fetchMe, startSession]);

  // --- logout
  const logout = useCallback(async () => {
    setLoading(true);
    try {
      await client.post('/api/auth/logout');
    } finally {
      setUser(null);
      endSession();
      setLoading(false);
      // Keep initialCheckDone true to prevent unnecessary re-fetch
    }
  }, [endSession]);

  // --- refresh (re-fetch user)
  const refresh = fetchMe;

  const value = { user, loading, login, logout, refresh };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

AuthProvider.propTypes = {
  children: PropTypes.node.isRequired,
};

// -----------------------------------------------------------------------------
// Hook
// -----------------------------------------------------------------------------

export function useAuthContext() {
  return useContext(AuthContext);
}

// Export the context for testing
export { AuthContext };
