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
  Outlet,
} from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import LoginPage from './pages/LoginPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import UserProfile from './components/auth/UserProfile';
import SettingsPage from './pages/SettingsPage';
import TimelinePage from './pages/TimelinePage';
import SearchPage from './pages/SearchPage';
import ProjectDashboard from './pages/ProjectDashboard';
import ProjectChatPage from './pages/ProjectChatPage';
import Layout from './components/common/Layout';
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
      path: '/',
      element: <Layout><Outlet /></Layout>,
      children: [
        {
          index: true,
          element: <ProtectedRoute element={<Dashboard />} />,
        },
        {
          path: 'login',
          element: <LoginPage />,
        },
        {
          path: 'forgot',
          element: <ForgotPasswordPage />,
        },
        {
          path: 'reset/:token',
          element: <ResetPasswordPage />,
        },
        {
          path: 'projects',
          element: <ProtectedRoute element={<ProjectDashboard />} />,
        },
        {
          path: 'profile',
          element: <ProtectedRoute element={<UserProfile />} />,
        },
        {
          path: 'settings',
          element: <ProtectedRoute element={<SettingsPage />} />,
        },
        {
          path: 'search',
          element: <ProtectedRoute element={<SearchPage />} />,
        },
        {
          path: 'timeline',
          element: <ProtectedRoute element={<TimelinePage />} />,
        },
        // Deprecated alias – kept temporarily so existing bookmarks to "/dashboard"
        // still work.  Can be removed once users migrate.
        {
          path: 'dashboard',
          element: <ProtectedRoute element={<ProjectDashboard />} />,
        },
        {
          path: 'projects/:projectId/chat',
          element: <ProtectedRoute element={<ProjectChatPage />} />,
        },
      ],
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
