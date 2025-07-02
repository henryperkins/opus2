import { Link } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { useMemo } from 'react';
import UserMenu from '../auth/UserMenu';
import AIProviderStatus from './AIProviderStatus';
import ThemeToggle from './ThemeToggle';
import Breadcrumb from './Breadcrumb';
import { Menu } from 'lucide-react';
import { getNavigationItems } from '../../utils/navigationUtils';
import PropTypes from 'prop-types';

function Header({ onMenuClick, showMenuButton = false, sidebarOpen = false }) {
  const { user, loading } = useAuth();

  // Memoize mobile quick action items to prevent unnecessary recomputations
  const mobileQuickActions = useMemo(() => 
    getNavigationItems({ showMobileQuickAction: true }), 
    []
  );


  return (
    <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700 sticky top-0 z-40">
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
                aria-expanded={sidebarOpen}
                aria-controls="sidebar-menu"
              >
                <Menu className="h-6 w-6" />
              </button>
            )}

            {/* Breadcrumbs */}
            <Breadcrumb showHome={false} />
          </div>


          {/* Right side - Status, theme, and user menu */}
          <div className="flex items-center space-x-3 min-w-0 flex-wrap">
            {/* AI Provider Status */}
            <AIProviderStatus className="hidden sm:block" />

            {/* Mobile quick actions */}
            <nav className="lg:hidden flex items-center space-x-2" aria-label="Quick actions">
              {mobileQuickActions.map(action => {
                const IconComponent = action.icon;
                return (
                  <Link
                    key={action.id}
                    to={action.path}
                    className="p-2 rounded-md text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700"
                    aria-label={`Go to ${action.label}`}
                    title={action.label}
                  >
                    <IconComponent className="w-5 h-5" />
                    <span className="sr-only">{action.label}</span>
                  </Link>
                );
              })}
            </nav>

            {/* Theme Toggle */}
            <ThemeToggle />

            {/* User menu or login */}
            {loading ? (
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 flex-shrink-0" aria-label="Loading"></div>
            ) : user ? (
              <UserMenu />
            ) : (
              <Link
                to="/login"
                className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 rounded-md text-sm font-medium transition-colors duration-200 flex-shrink-0"
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
  showMenuButton: PropTypes.bool,
  sidebarOpen: PropTypes.bool
};

Header.defaultProps = {
  onMenuClick: () => {},
  showMenuButton: false,
  sidebarOpen: false
};

export default Header;
