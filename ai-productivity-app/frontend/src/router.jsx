/* Application Router
 *
 * Purpose
 * -------
 * Centralised React-Router configuration adding:
 *  • Login route (/login)
 *  • Protected root route (/) that requires authentication
 *
 * ProtectedRoute component is defined inline for brevity; it leverages useRequireAuth
 * from hooks/useAuth.js.
 */

import React from 'react';
import {
  createBrowserRouter,
  RouterProvider,
  Route,
  Navigate,
} from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import LoginPage from './pages/LoginPage';
import UserProfile from './components/auth/UserProfile';
import SettingsPage from './pages/SettingsPage';
import ProjectsPage from './pages/ProjectsPage';
import TimelinePage from './pages/TimelinePage';
import SearchPage from './pages/SearchPage';
import { useRequireAuth } from './hooks/useAuth';

// -----------------------------------------------------------------------------
// ProtectedRoute wrapper
// -----------------------------------------------------------------------------

function ProtectedRoute({ element }) {
  const { user, loading } = useRequireAuth();
  if (loading) return null; // Could render a spinner
  return user ? element : <Navigate to="/login" replace />;
}

// -----------------------------------------------------------------------------
// Router
// -----------------------------------------------------------------------------

export const router = createBrowserRouter(
  [
    {
      path: '/login',
      element: <LoginPage />,
    },
    {
      path: '/',
      element: <ProtectedRoute element={<Dashboard />} />,
    },
    {
      path: '/projects',
      element: <ProtectedRoute element={<ProjectsPage />} />,
    },
    {
      path: '/profile',
      element: <ProtectedRoute element={<UserProfile />} />,
    },
    {
      path: '/settings',
      element: <ProtectedRoute element={<SettingsPage />} />,
    },
    {
      path: '/search',
      element: <ProtectedRoute element={<SearchPage />} />,
    },
    {
      path: '/timeline',
      element: <ProtectedRoute element={<TimelinePage />} />,
    },
  ],
  {
    future: {
      v7_startTransition: true,
      v7_normalizeFormMethod: true,
    },
  }
);

// Root provider component
export default function AppRouter() {
  return (
    <RouterProvider
      router={router}
      future={{
        v7_startTransition: true,
      }}
    />
  );
}
