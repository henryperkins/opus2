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
import App from './App';
import LoginPage from './pages/LoginPage';
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

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/',
    element: <ProtectedRoute element={<App />} />,
  },
]);

// Root provider component
export default function AppRouter() {
  return <RouterProvider router={router} />;
}
