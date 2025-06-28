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
  useState,
  useCallback,
} from 'react';
import PropTypes from 'prop-types';
import { authAPI } from '../api/auth';
import useAuthStore from '../stores/authStore';
import { useQuery, useQueryClient } from '@tanstack/react-query';


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
  const { startSession, endSession } = useAuthStore();
  const queryClient = useQueryClient();

  // -----------------------------------------------------------
  // Query: fetch current user ("me")
  // -----------------------------------------------------------
  const fetchMe = React.useCallback(async () => {
    try {
      const data = await authAPI.getCurrentUser();
      return data;
    } catch (e) {
      const status = e?.response?.status;
      if (status === 401 || status === 403) {
        // Guest user – treat as non-fatal, just return null so downstream code
        // can decide whether to redirect to /login.
        return null;
      }
      throw e;
    }
  }, []);

  const {
    data: user,
    isInitialLoading,
    isError,
    error,
    refetch: refetchMe,
  } = useQuery({
    queryKey: ['me'],
    queryFn: fetchMe,
    // 5-minute cache, no retry on 4xx
    staleTime: 5 * 60 * 1000,
    retry: (attempt, error) => {
      const status = error?.response?.status;
      if (status && status >= 400 && status < 500) return false;
      return attempt < 2;
    },
  });

  // Listen for global logout events triggered by Axios interceptor
  React.useEffect(() => {
    const handler = () => {
      queryClient.setQueryData(['me'], null);
    };
    window.addEventListener('auth:logout', handler);
    return () => window.removeEventListener('auth:logout', handler);
  }, [queryClient]);

  // -----------------------------------------------------------
  // Auth actions
  // -----------------------------------------------------------
  const [isAuthenticating, setIsAuthenticating] = useState(false);

  const login = useCallback(
    async (username_or_email, password) => {
      if (isAuthenticating) {
        throw new Error('Authentication already in progress');
      }
      setIsAuthenticating(true);
      try {
        await authAPI.login({ username_or_email, password });

        // ensure cookie persisted before /me
        await new Promise((r) => setTimeout(r, 120));

        await refetchMe();
        startSession(username_or_email);
      } finally {
        setIsAuthenticating(false);
      }
    },
    [isAuthenticating, refetchMe, startSession]
  );

  const logout = useCallback(async () => {
    try {
      await authAPI.logout();
    } finally {
      endSession();
      // Clear all React Query cache to prevent cross-account data leaks
      queryClient.clear();
    }
  }, [endSession, queryClient]);

  const refresh = useCallback(() => refetchMe(), [refetchMe]);

  const updateProfile = useCallback(
    async (changes) => {
      const prev = user;
      queryClient.setQueryData(['me'], { ...user, ...changes });

      try {
        const data = await authAPI.updateProfile(changes);
        queryClient.setQueryData(['me'], data);
      } catch (err) {
        queryClient.setQueryData(['me'], prev);
        throw err;
      }
    },
    [user, queryClient]
  );

  const value = {
    user,
    loading: isInitialLoading,
    login,
    logout,
    refresh,
    updateProfile,
  };

  if (isInitialLoading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#f8fafc',
        }}
      >
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mr-3" />
        <span style={{ fontSize: 24, color: '#3b82f6', letterSpacing: 2 }}>
          Checking authentication…
        </span>
      </div>
    );
  }

  // Surface severe backend errors (non-401) early – still render app so
  // ErrorBoundary higher up can handle.
  if (isError && error?.response?.status >= 500) {
    throw error;
  }

  return (
    <AuthContextInstance.Provider value={value}>{children}</AuthContextInstance.Provider>
  );
}

AuthProvider.propTypes = {
  children: PropTypes.node.isRequired,
};

