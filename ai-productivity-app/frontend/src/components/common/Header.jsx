import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import UserMenu from '../auth/UserMenu';
import AIProviderStatus from './AIProviderStatus';
import ThemeToggle from './ThemeToggle';
import { Menu, Search, FolderOpen, Clock, Home, Settings, ChevronRight } from 'lucide-react';
import PropTypes from 'prop-types';

function Header({ onMenuClick, showMenuButton = false }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  // Helper to check if a path is active
  const isActive = (path) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  // Generate breadcrumbs based on current path
  const getBreadcrumbs = () => {
    const paths = location.pathname.split('/').filter(Boolean);
    const breadcrumbs = [{ name: 'Dashboard', path: '/' }];

    if (paths.length > 0) {
      const first = paths[0];
      if (first === 'projects') {
        breadcrumbs.push({ name: 'Projects', path: '/projects' });
        if (paths[1]) {
          breadcrumbs.push({ name: 'Project', path: `/projects/${paths[1]}` });
          if (paths[2]) {
            const subPages = {
              'chat': 'Chat',
              'files': 'Files',
              'analytics': 'Analytics',
              'knowledge': 'Knowledge Base'
            };
            breadcrumbs.push({
              name: subPages[paths[2]] || paths[2],
              path: location.pathname
            });
          }
        }
      } else {
        const pageNames = {
          'search': 'Search',
          'timeline': 'Timeline',
          'settings': 'Settings',
          'profile': 'Profile',
          'models': 'Model Settings'
        };
        breadcrumbs.push({
          name: pageNames[first] || first.charAt(0).toUpperCase() + first.slice(1),
          path: location.pathname
        });
      }
    }

    return breadcrumbs;
  };

  const breadcrumbs = getBreadcrumbs();

  return (
    <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700 sticky top-0 z-30">
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Left side - Menu button and breadcrumbs */}
          <div className="flex items-center flex-1">
            {/* Mobile menu button */}
            {showMenuButton && (
              <button
                onClick={onMenuClick}
                className="p-2 -ml-2 mr-3 rounded-md text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors duration-150"
                aria-label="Toggle sidebar"
              >
                <Menu className="h-6 w-6" />
              </button>
            )}

            {/* Breadcrumbs */}
            <nav className="flex items-center space-x-1 text-sm" aria-label="Breadcrumb">
              {breadcrumbs.map((crumb, index) => (
                <div key={crumb.path} className="flex items-center">
                  {index > 0 && <ChevronRight className="w-4 h-4 text-gray-400 mx-1" />}
                  {index === breadcrumbs.length - 1 ? (
                    <span className="text-gray-900 dark:text-gray-100 font-medium">
                      {crumb.name}
                    </span>
                  ) : (
                    <Link
                      to={crumb.path}
                      className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
                    >
                      {crumb.name}
                    </Link>
                  )}
                </div>
              ))}
            </nav>
          </div>

          {/* Center - Quick navigation (desktop only) */}
          <nav className="hidden lg:flex items-center space-x-1 mx-6">
            <Link
              to="/"
              className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive('/')
                  ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              <Home className="w-4 h-4" />
              <span>Dashboard</span>
            </Link>
            <Link
              to="/projects"
              className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive('/projects')
                  ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              <FolderOpen className="w-4 h-4" />
              <span>Projects</span>
            </Link>
            <Link
              to="/search"
              className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive('/search')
                  ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              <Search className="w-4 h-4" />
              <span>Search</span>
            </Link>
            <Link
              to="/timeline"
              className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive('/timeline')
                  ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              <Clock className="w-4 h-4" />
              <span>Timeline</span>
            </Link>
          </nav>

          {/* Right side - Status, theme, and user menu */}
          <div className="flex items-center space-x-3">
            {/* AI Provider Status */}
            <AIProviderStatus className="hidden sm:block" />

            {/* Quick search button (mobile) */}
            <Link
              to="/search"
              className="lg:hidden p-2 rounded-md text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700"
              aria-label="Search"
            >
              <Search className="w-5 h-5" />
            </Link>

            {/* Theme Toggle */}
            <ThemeToggle />

            {/* Settings (mobile) */}
            <Link
              to="/settings"
              className="lg:hidden p-2 rounded-md text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700"
              aria-label="Settings"
            >
              <Settings className="w-5 h-5" />
            </Link>

            {/* User menu or login */}
            {loading ? (
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
            ) : user ? (
              <UserMenu />
            ) : (
              <Link
                to="/login"
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors duration-200"
              >
                Sign In
              </Link>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}

Header.propTypes = {
  onMenuClick: PropTypes.func,
  showMenuButton: PropTypes.bool
};

Header.defaultProps = {
  onMenuClick: () => {},
  showMenuButton: false
};

export default Header;
