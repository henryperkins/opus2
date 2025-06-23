import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import PropTypes from 'prop-types';
import { useAuth } from '../../hooks/useAuth';
import UserMenu from '../auth/UserMenu';
import ThemeToggle from './ThemeToggle';
import Sidebar from './Sidebar';

// -------------------------------------------------------------------------------------------------
// Global layout wrapper
// -------------------------------------------------------------------------------------------------

export default function Layout({ children }) {
  const { user, loading: authLoading } = useAuth();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Always gate on authLoading for bulletproofness.
  if (authLoading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#f8fafc'
        }}
      >
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mr-3"></div>
        <span style={{ fontSize: 24, color: '#3b82f6', letterSpacing: 2 }}>Checking authentication…</span>
      </div>
    );
  }

  // Don't show sidebar on login page
  const showSidebar = user && location.pathname !== '/login';

  if (!showSidebar) {
    // Simple layout for login page and when user is not authenticated
    return (
      <div className="min-h-screen gradient-bg transition-colors duration-200 flex flex-col">
        {/* Skip to main content link */}
        <a href="#main-content" className="skip-link">
          Skip to main content
        </a>

        {/* Simple header for login page */}
        <header className="glass border-b border-white/20 dark:border-gray-700/20 transition-all duration-200 backdrop-blur-md">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <Link to="/" className="flex items-center space-x-2 no-underline">
                <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg flex items-center justify-center transition-all duration-200 hover:scale-110 shadow-lg">
                  <svg
                    className="w-5 h-5 text-white"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                    />
                  </svg>
                </div>
                <span className="text-xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent dark:from-gray-100 dark:to-gray-300 no-underline">
                  AI Productivity
                </span>
              </Link>
              <ThemeToggle />
            </div>
          </div>
        </header>

        {/* Main content */}
        <main id="main-content" className="flex-1" role="main">
          {children}
        </main>

        {/* Footer */}
        <footer className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 transition-colors duration-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <p className="text-center text-sm text-gray-500 dark:text-gray-400">
              © 2024 AI Productivity. All rights reserved.
            </p>
          </div>
        </footer>
      </div>
    );
  }

  // Layout with sidebar for authenticated users
  return (
    <div className="min-h-screen gradient-bg transition-colors duration-200 flex">
      {/* Skip to main content link */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      {/* Sidebar */}
      {/* Overlay for mobile when sidebar open */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/30 backdrop-blur-sm lg:hidden z-30"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      <Sidebar
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(false)}
        className="lg:w-72"
      />

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top header - now visible on all screen sizes */}
        <header className="glass border-b border-white/20 dark:border-gray-700/20 transition-all duration-200 backdrop-blur-md">
          <div className="px-4 sm:px-6">
            <div className="flex justify-between items-center h-16">
              {/* Mobile menu button - only on small screens */}
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="lg:hidden p-2 rounded-md text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors duration-150"
                aria-expanded={sidebarOpen}
                aria-label="Toggle sidebar"
                type="button"
              >
                <span className="sr-only">Open sidebar</span>
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>

              {/* Desktop: Empty space for potential breadcrumb/title */}
              <div className="hidden lg:block flex-1">
                {/* Space for future page title or breadcrumb */}
              </div>

              {/* User menu - visible on all screen sizes */}
              <UserMenu />
            </div>
          </div>
        </header>

        {/* Main content */}
        <main id="main-content" className="flex-1 overflow-auto" role="main">
          {children}
        </main>
      </div>
    </div>
  );
}

// PropTypes validation
Layout.propTypes = {
  children: PropTypes.node.isRequired
};
