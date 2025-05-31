// React application entry point
import React from 'react';
import ReactDOM from 'react-dom/client';
import { AuthProvider } from './contexts/AuthContext';
import AppRouter from './router';
// Replaced existing import to add ErrorBoundary
import './styles/tailwind.css';
import './index.css';
import ErrorBoundary from './components/common/ErrorBoundary';

// Mount React app
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <AuthProvider>
        <AppRouter />
      </AuthProvider>
    </ErrorBoundary>
  </React.StrictMode>
);
