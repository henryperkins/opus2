import { Link, useLocation } from 'react-router-dom';
import { ChevronRight, Home } from 'lucide-react';
import PropTypes from 'prop-types';
import { generateBreadcrumbs } from '../../utils/navigationUtils';

export default function Breadcrumb({ items, showHome = true, separator = 'chevron' }) {
  const location = useLocation();

  // Auto-generate breadcrumbs if items not provided
  const breadcrumbs = items || generateBreadcrumbs(location.pathname);

  const SeparatorIcon = separator === 'chevron' ? 
    <ChevronRight className="w-4 h-4 text-gray-400 mx-1" /> : 
    <span className="mx-1 text-gray-400">/</span>;

  // Filter out Dashboard from breadcrumbs if showHome is false
  const filteredBreadcrumbs = showHome ? breadcrumbs : breadcrumbs.filter(crumb => crumb.path !== '/');

  return (
    <nav className="flex items-center space-x-1 text-sm" aria-label="Breadcrumb">
      {showHome && (
        <div className="flex items-center">
          <Link
            to="/"
            className="flex items-center text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
          >
            <Home className="w-4 h-4 mr-1" />
            <span>Dashboard</span>
          </Link>
          {filteredBreadcrumbs.length > 0 && SeparatorIcon}
        </div>
      )}
      
      {filteredBreadcrumbs.map((crumb, index) => (
        <div key={crumb.path} className="flex items-center">
          {index > 0 && SeparatorIcon}
          {index === filteredBreadcrumbs.length - 1 ? (
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
  );
}

Breadcrumb.propTypes = {
  items: PropTypes.arrayOf(PropTypes.shape({
    name: PropTypes.string.isRequired,
    path: PropTypes.string.isRequired
  })),
  showHome: PropTypes.bool,
  separator: PropTypes.oneOf(['chevron', 'slash'])
};