/* useAuth hooks
 *
 * Purpose
 * -------
 * Thin wrappers around AuthContext for convenience inside functional components.
 *
 * Exports
 * -------
 * • useAuth()          – returns full context { user, loading, login, logout, refresh }
 * • useUser()          – returns current user object (or null)
 * • useRequireAuth()   – redirect helper; if not logged in pushes "/login"
 *
 */

import { useContext, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthContext } from '../contexts/AuthContext'; // named export

// -----------------------------------------------------------------------------

export function useAuth() {
  return useAuthContext();
}

export function useUser() {
  const { user } = useAuthContext();
  return user;
}

/**
 * React hook that ensures user is authenticated; otherwise redirects to /login.
 *
 * Usage:
 *   useRequireAuth();   // inside protected component
 */
export function useRequireAuth() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && !user) {
      navigate('/login');
    }
  }, [user, loading, navigate]);

  return { user, loading };
}
