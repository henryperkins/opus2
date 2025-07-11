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

import React from "react";
import {
  createBrowserRouter,
  RouterProvider,
  Route,
  Navigate,
  Outlet,
  redirect,
} from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import LoginPage from "./pages/LoginPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import UserProfile from "./components/auth/UserProfile";
import UnifiedSettingsPage from "./pages/UnifiedSettingsPage";
import TimelinePage from "./pages/TimelinePage";
import SearchPage from "./pages/SearchPage";
import ProjectDashboard from "./pages/ProjectDashboard";
import ProjectPage from "./pages/ProjectPage";
import ProjectChatPage from "./pages/ProjectChatPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import ProjectFilesPage from "./pages/ProjectFilesPage";
import ProjectKnowledgePage from "./pages/ProjectKnowledgePage";
import FileViewerPage from "./pages/FileViewerPage";
import Layout from "./components/common/Layout";
import ProjectLayout from "./layouts/ProjectLayout";
import { useRequireAuth } from "./hooks/useAuth";

// -----------------------------------------------------------------------------
// ProtectedRoute wrapper
// -----------------------------------------------------------------------------

function ProtectedRoute({ element }) {
  const { user, loading } = useRequireAuth();

  // Handle loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // Handle authentication
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return element;
}

// -----------------------------------------------------------------------------
// Router
// -----------------------------------------------------------------------------

export const router = createBrowserRouter(
  [
    {
      path: "/",
      element: (
        <Layout>
          <Outlet />
        </Layout>
      ),
      children: [
        {
          index: true,
          element: <ProtectedRoute element={<Dashboard />} />,
        },
        {
          path: "login",
          element: <LoginPage />,
        },
        {
          path: "forgot",
          element: <ForgotPasswordPage />,
        },
        {
          path: "reset/:token",
          element: <ResetPasswordPage />,
        },
        {
          path: "projects",
          element: <ProtectedRoute element={<ProjectDashboard />} />,
        },
        {
          path: "profile",
          element: <ProtectedRoute element={<UserProfile />} />,
        },
        {
          path: "settings",
          element: <ProtectedRoute element={<UnifiedSettingsPage />} />,
        },
        {
          path: "search",
          element: <ProtectedRoute element={<SearchPage />} />,
        },
        {
          path: "timeline",
          element: <ProtectedRoute element={<TimelinePage />} />,
        },
        // Deprecated route – perform server-style redirect preserving method (307)
        {
          path: "dashboard",
          loader: () => redirect("/projects", 307),
        },
        {
          path: "projects/:projectId",
          element: <ProtectedRoute element={<ProjectLayout />} />,
          children: [
            { index: true, element: <ProjectPage /> },
            { path: "chat/:sessionId?", element: <ProjectChatPage /> },
            { path: "files", element: <ProjectFilesPage /> },
            { path: "analytics", element: <AnalyticsPage /> },
            { path: "knowledge", element: <ProjectKnowledgePage /> },
          ],
        },
        {
          path: "models",
          element: <ProtectedRoute element={<UnifiedSettingsPage />} />,
        },
        {
          path: "files/:path",
          element: <ProtectedRoute element={<FileViewerPage />} />,
        },
      ],
    },
  ],
  {
    basename: "/",
    future: {
      v7_startTransition: true,
      v7_normalizeFormMethod: true,
      v7_fetcherPersist: true,
      v7_relativeSplatPath: true,
      v7_partialHydration: true,
      v7_skipActionErrorRevalidation: true,
    },
  },
);

// Root provider component
export default function AppRouter() {
  return (
    <RouterProvider
      router={router}
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
        v7_fetcherPersist: true,
        v7_normalizeFormMethod: true,
        v7_partialHydration: true,
        v7_skipActionErrorRevalidation: true,
      }}
    />
  );
}
