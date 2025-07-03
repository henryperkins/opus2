import { Link, useLocation } from 'react-router-dom';
import { ChevronRight, Home } from 'lucide-react';
import PropTypes from 'prop-types';
import { generateBreadcrumbs } from '../../utils/navigationUtils';
import { useState, useEffect } from 'react';

export default function Breadcrumb({ items, showHome = true, separator = 'chevron' }) {
  const location = useLocation();
  const [breadcrumbs, setBreadcrumbs] = useState(items || [{ name: 'Dashboard', path: '/' }]);

  useEffect(() => {
    if (!items) {
      // Auto-generate breadcrumbs if items not provided. The util was made
      // synchronous for test determinism, but we keep Promise handling for
      // backward-compatibility.
      const maybeBreadcrumbs = generateBreadcrumbs(location.pathname);
      if (maybeBreadcrumbs && typeof maybeBreadcrumbs.then === 'function') {
        // Future-proof: handle Promise.
        maybeBreadcrumbs.then(setBreadcrumbs);
      } else {
        setBreadcrumbs(maybeBreadcrumbs);
      }
    } else {
      setBreadcrumbs(items);
    }
  }, [location.pathname, items]);

  const SeparatorIcon = separator === 'chevron' ? 
    <ChevronRight className="w-4 h-4 text-gray-400 mx-1" /> : 
    <span className="mx-1 text-gray-400">/</span>;

  // Filter out Dashboard from breadcrumbs if showHome is false
  const filteredBreadcrumbs = showHome ? breadcrumbs : breadcrumbs.filter(crumb => crumb.path !== '/');

  return (
    <nav aria-label="Breadcrumb">
      <ol className="flex items-center space-x-1 text-sm">
        {showHome && (
          <li className="flex items-center">
            <Link
              to="/"
              className="flex items-center text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
            >
              <Home className="w-4 h-4 mr-1" />
              <span>Dashboard</span>
            </Link>
          </li>
        )}
        
        {filteredBreadcrumbs.map((crumb, index) => (
          <li key={`${crumb.path}-${index}`} className="flex items-center">
            {/* Add separator before each crumb (including first when showHome is true) */}
            {(showHome || index > 0) && SeparatorIcon}
            {index === filteredBreadcrumbs.length - 1 ? (
              <span 
                className="text-gray-900 dark:text-gray-100 font-medium"
                aria-current="page"
              >
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
          </li>
        ))}
      </ol>
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