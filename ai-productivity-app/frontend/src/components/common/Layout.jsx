import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import PropTypes from 'prop-types';
import { useAuth } from '../../hooks/useAuth';
import UserMenu from '../auth/UserMenu';
import ThemeToggle from './ThemeToggle';
import Sidebar from './Sidebar';
import Header from './Header';
import { useMediaQuery } from '../../hooks/useMediaQuery';
import useAuthStore from '../../stores/authStore';
import { useResponsiveLayout } from '../../hooks/useResponsiveLayout';
import { ResponsivePage, ShowOnDesktop, HideOnDesktop } from '../layout/ResponsiveContainer';
import { Menu } from 'lucide-react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';

export default function Layout({ children }) {
  const { user, loading: authLoading } = useAuth();
  const location = useLocation();
  const { preferences } = useAuthStore();
  // Start with sidebar open on desktop, closed on mobile/tablet
  const { isMobile, isTablet } = useMediaQuery();
  const isDesktop = !isMobile && !isTablet;
  const [sidebarOpen, setSidebarOpen] = useState(isDesktop);
  const layout = useResponsiveLayout();

  // Show loading state
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

  // Don't show sidebar on login/auth pages
  const authPages = ['/login', '/forgot', '/reset'];
  const isAuthPage = authPages.some(page => location.pathname.startsWith(page));
  const showSidebar = user && !isAuthPage;

  if (!showSidebar) {
    // Simple layout for auth pages
    return (
      <div className="min-h-screen gradient-bg transition-colors duration-200 flex flex-col">
        <a href="#main-content" className="skip-link">
          Skip to main content
        </a>

        {/* Simple header for auth pages */}
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

        <main id="main-content" className="flex-1" role="main">
          {children}
        </main>

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

  // Main layout with sidebar for authenticated users
  return (
    <div className="min-h-screen gradient-bg transition-colors duration-200">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      {/* Desktop: Resizable panels */}
      {isDesktop ? (
        <PanelGroup direction="horizontal" className="h-screen">
          <Panel defaultSize={20} minSize={12} maxSize={35}>
            <Sidebar
              isOpen={true}
              onToggle={() => {}}
              className="h-full"
            />
          </Panel>
          <PanelResizeHandle className="w-1 bg-gray-300 dark:bg-gray-600 hover:bg-gray-400 dark:hover:bg-gray-500 transition-colors cursor-col-resize" />
          <Panel minSize={50}>
            <div className="flex flex-col h-full">
              <Header
                onMenuClick={() => setSidebarOpen(!sidebarOpen)}
                showMenuButton={false}
              />
              <main id="main-content" className="flex-1 overflow-auto" role="main">
                {children}
              </main>
            </div>
          </Panel>
        </PanelGroup>
      ) : (
        // Mobile/Tablet: Drawer behavior
        <div className="flex h-screen">
          <Sidebar
            isOpen={sidebarOpen}
            onToggle={() => setSidebarOpen(false)}
            className={`
              fixed inset-y-0 left-0 z-40 w-64 transform transition-transform duration-300
              ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
            `}
          />

          {/* Overlay for mobile/tablet when sidebar is open */}
          {sidebarOpen && (
            <div
              className="fixed inset-0 bg-black/30 backdrop-blur-sm z-30"
              onClick={() => setSidebarOpen(false)}
              aria-hidden="true"
            />
          )}

          {/* Main content area */}
          <div className="flex-1 flex flex-col">
            <Header
              onMenuClick={() => setSidebarOpen(!sidebarOpen)}
              showMenuButton={true}
            />
            <main id="main-content" className="flex-1 overflow-auto" role="main">
              {children}
            </main>
          </div>
        </div>
      )}
    </div>
  );
}

Layout.propTypes = {
  children: PropTypes.node.isRequired
};
