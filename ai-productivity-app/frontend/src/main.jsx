// React application entry point
import React from 'react';
import ReactDOM from 'react-dom/client';
import { AuthProvider } from './contexts/AuthContext';
import AppRouter from './router';
import { ThemeProvider } from './hooks/useTheme';
import { ToastContainer } from './components/common/Toast';
import Layout from './components/common/Layout';
import './styles/globals.css';
import ErrorBoundary from './components/common/ErrorBoundary';

// Mount React app
ReactDOM.createRoot(document.getElementById('root')).render(
  // <React.StrictMode>
    <ErrorBoundary>
      <ThemeProvider>
        <AuthProvider>
          <Layout>
            <AppRouter />
            <ToastContainer />
          </Layout>
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  // </React.StrictMode>
);
