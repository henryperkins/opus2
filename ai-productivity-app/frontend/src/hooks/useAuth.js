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

import { useContext, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { AuthContext } from "../contexts/AuthContext";

// Hook to access AuthContext
export function useAuthContext() {
  return useContext(AuthContext);
}

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
    console.log(
      "useRequireAuth effect triggered - loading:",
      loading,
      "user:",
      !!user,
    );
    if (!loading && !user) {
      console.log("useRequireAuth: Redirecting to login - no user found");
      navigate("/login");
    }
  }, [user, loading, navigate]);

  return { user, loading };
}
