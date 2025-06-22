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
  redirect,
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
import ProjectPage from './pages/ProjectPage';
import ProjectChatPage from './pages/ProjectChatPage';
import AnalyticsPage from './pages/AnalyticsPage';
import KnowledgeBasePage from './pages/KnowledgeBasePage';
import ProjectFilesPage from './pages/ProjectFilesPage';
import ModelSettingsPage from './pages/ModelSettingsPage';
import Layout from './components/common/Layout';
import ProjectLayout from './layouts/ProjectLayout';
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
        // Deprecated route – perform server-style redirect preserving method (307)
        {
          path: 'dashboard',
          loader: () => redirect('/projects', 307),
        },
        {
          path: 'projects/:projectId',
          element: <ProtectedRoute element={<ProjectLayout />} />,
          children: [
            { index: true, element: <ProjectPage /> },
            { path: 'chat/:sessionId?', element: <ProjectChatPage /> },
            { path: 'files', element: <ProjectFilesPage /> },
            { path: 'analytics', element: <AnalyticsPage /> },
            { path: 'knowledge', element: <KnowledgeBasePage /> },
          ]
        },
        {
          path: 'models',
          element: <ProtectedRoute element={<ModelSettingsPage />} />,
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
