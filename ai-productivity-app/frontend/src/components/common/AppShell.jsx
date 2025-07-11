import { useState, useEffect } from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { useMediaQuery } from '../../hooks/useMediaQuery';
import { useAuth } from '../../hooks/useAuth';
import { useLocation } from 'react-router-dom';
import UnifiedNavBar from '../navigation/UnifiedNavBar';
import UnifiedSidebar from '../navigation/UnifiedSidebar';
import ThemeToggle from './ThemeToggle';
import { Link } from 'react-router-dom';
import useAuthStore from '../../stores/authStore';
import { NavigationProvider } from '../../contexts/NavigationContext';
// Global dialog for config conflicts
import ConfigConflictDialog from '../settings/ConfigConflictDialog';

export default function AppShell({ sidebar, children }) {
  const { user, loading: authLoading } = useAuth();
  const location = useLocation();
  const { isMobile, isTablet } = useMediaQuery();
  const isDesktop = !isMobile && !isTablet;
  const [sidebarOpen, setSidebarOpen] = useState(isDesktop);
  const { preferences, setSidebarWidth } = useAuthStore();

  const handleContextAction = (actionId) => {
    // Dispatch custom event that pages can listen to
    window.dispatchEvent(new CustomEvent('contextAction', { detail: actionId }));
    
    // Handle global actions
    switch (actionId) {
      case 'settings':
        // Could navigate to settings or open a modal
        break;
      case 'analytics':
        // Could toggle global analytics view
        break;
    }
  };

  // Sync sidebar state with screen size changes
  useEffect(() => {
    if (isDesktop) {
      setSidebarOpen(true);
    } else {
      setSidebarOpen(false);
    }
  }, [isDesktop]);

  // Show loading state
  if (authLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50 dark:bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mr-3"></div>
        <span className="text-xl text-blue-600 dark:text-blue-400">Checking authentication…</span>
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
      <>
      <div className="flex flex-col h-screen overflow-hidden bg-gray-50 dark:bg-gray-900">
        <header className="sticky top-0 z-30 flex items-center justify-between bg-white dark:bg-gray-800 shadow-md px-4 py-2">
          <Link to="/" className="flex items-center space-x-2 no-underline">
            <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg flex items-center justify-center shadow-lg">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <span className="text-xl font-bold text-gray-900 dark:text-gray-100">AI Productivity</span>
          </Link>
          <ThemeToggle />
        </header>
        <main className="flex-1 overflow-auto">{children}</main>
      </div>
      <ConfigConflictDialog />
      </>
    );
  }

  // Main layout with sidebar for authenticated users
  return (
    <NavigationProvider>
      <div className="flex flex-col h-screen overflow-hidden bg-gray-50 dark:bg-gray-900">
        {/* Global header */}
        <UnifiedNavBar 
          onMenuClick={() => setSidebarOpen(!sidebarOpen)} 
          showMenuButton={!isDesktop}
          sidebarOpen={sidebarOpen}
          onContextAction={handleContextAction}
        />

        {/* Main content area with panels */}
        <div className="flex-1 overflow-hidden">
          {isDesktop ? (
            // Desktop: Resizable panels
            <PanelGroup 
              direction="horizontal" 
              className="h-full"
              onLayout={(sizes) => {
                // Calculate sidebar width from percentage
                const sidebarWidthPercent = sizes[0];
                const windowWidth = window.innerWidth;
                const newWidth = (sidebarWidthPercent / 100) * windowWidth;
                setSidebarWidth(newWidth);
              }}
            >
              <Panel 
                defaultSize={(preferences.sidebarWidth / window.innerWidth) * 100} 
                minSize={14} 
                maxSize={35} 
                collapsible
              >
                <UnifiedSidebar isOpen={true} onClose={() => {}} />
              </Panel>
              <PanelResizeHandle className="w-px bg-gray-200 dark:bg-gray-700 hover:bg-blue-400 dark:hover:bg-blue-500 cursor-col-resize" />
              <Panel minSize={40}>
                <main className="h-full overflow-auto">{children}</main>
              </Panel>
            </PanelGroup>
          ) : (
            // Mobile/Tablet: Drawer behavior
            <>
              <div className={`fixed inset-y-0 left-0 z-40 w-64 transform transition-transform duration-300 ${
                sidebarOpen ? 'translate-x-0' : '-translate-x-full'
              }`}>
                <UnifiedSidebar
                  isOpen={sidebarOpen}
                  onClose={() => setSidebarOpen(false)}
                />
              </div>
              
              {/* Overlay for mobile/tablet when sidebar is open */}
              {sidebarOpen && (
                <div
                  className="fixed inset-0 bg-black/30 backdrop-blur-sm z-30"
                  onClick={() => setSidebarOpen(false)}
                  onKeyDown={(e) => e.key === 'Enter' && setSidebarOpen(false)}
                  role="button"
                  tabIndex="0"
                  aria-label="Close menu overlay"
                />
              )}
              
              <main className="h-full overflow-auto">{children}</main>
            </>
          )}
        </div>
      </div>
      {/* Global dialogs */}
      <ConfigConflictDialog />
    </NavigationProvider>
  );
}