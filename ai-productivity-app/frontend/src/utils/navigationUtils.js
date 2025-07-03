import { navigationRoutes, projectSubRoutes, pageRoutes } from '../config/navigationConfig';
import { projectAPI } from '../api/projects';

export const isActivePath = (currentPath, targetPath) => {
  // Normalize paths by removing trailing slashes and decoding URI components
  const normalizeAndDecode = (path) => {
    try {
      const decoded = decodeURIComponent(path);
      return decoded.toLowerCase().replace(/\/$/, '') || '/';
    } catch {
      // Fallback for malformed URIs
      return path.toLowerCase().replace(/\/$/, '') || '/';
    }
  };

  const normalizedCurrent = normalizeAndDecode(currentPath);
  const normalizedTarget = normalizeAndDecode(targetPath);

  // Root path special case
  if (normalizedTarget === '/') {
    return normalizedCurrent === '/';
  }
  
  // Split into segments and compare path boundaries
  const currentSegments = normalizedCurrent.split('/').filter(Boolean);
  const targetSegments = normalizedTarget.split('/').filter(Boolean);
  
  // Target must not have more segments than current
  if (targetSegments.length > currentSegments.length) {
    return false;
  }
  
  // Compare each segment exactly
  return targetSegments.every((segment, index) => 
    currentSegments[index] === segment
  );
};

export const getActiveNavStyles = (isActive) => {
  return isActive
    ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
    : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700';
};

export const getSidebarActiveStyles = (isActive) => {
  return isActive
    ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800';
};

// Memoization cache for breadcrumb generation
const breadcrumbCache = new Map();
const projectNameCache = new Map();

export const generateBreadcrumbs = (pathname) => {
  // Check cache first for performance
  if (breadcrumbCache.has(pathname)) {
    return breadcrumbCache.get(pathname);
  }

  // Strip query string and hash from pathname for parsing
  const cleanPathname = pathname.split('?')[0].split('#')[0];
  const paths = cleanPathname.split('/').filter(Boolean);
  const breadcrumbs = [{ name: 'Dashboard', path: '/' }];

  if (paths.length > 0) {
    const first = paths[0];
    if (first === 'projects') {
      breadcrumbs.push({ name: 'Projects', path: '/projects' });
      if (paths[1]) {
        const projectId = paths[1];
        // Default name – attempt to read from cache, otherwise generic placeholder.
        let projectName = projectNameCache.get(projectId) || 'Project';
        // Note: We intentionally avoid asynchronous network requests here so the
        // function remains synchronous. Production code that needs the real
        // project name should populate `projectNameCache` via a separate data
        // fetching layer.
        
        breadcrumbs.push({ name: projectName, path: `/projects/${projectId}` });
        
        // Handle project sub-routes with extended depth support
        if (paths[2]) {
          if (projectSubRoutes[paths[2]]) {
            breadcrumbs.push({
              name: projectSubRoutes[paths[2]].breadcrumbLabel,
              path: `/${paths.slice(0, 3).join('/')}`
            });
            
            // Handle deeper nested routes (e.g., /projects/123/files/images)
            if (paths[3]) {
              for (let i = 3; i < paths.length; i++) {
                const segment = paths[i];
                breadcrumbs.push({
                  name: segment.charAt(0).toUpperCase() + segment.slice(1),
                  path: `/${paths.slice(0, i + 1).join('/')}`
                });
              }
            }
          } else {
            // Unknown project sub-route
            breadcrumbs.push({
              name: paths[2].charAt(0).toUpperCase() + paths[2].slice(1),
              path: `/${paths.slice(0, 3).join('/')}`
            });
          }
        }
      }
    } else if (pageRoutes[first]) {
      breadcrumbs.push({
        name: pageRoutes[first],
        path: `/${first}` // Use clean path without query/hash
      });
    } else {
      breadcrumbs.push({
        name: first.charAt(0).toUpperCase() + first.slice(1),
        path: `/${first}` // Use clean path without query/hash
      });
    }
  }

  // Cache the result and return
  breadcrumbCache.set(pathname, breadcrumbs);
  
  // Prevent cache from growing too large
  if (breadcrumbCache.size > 100) {
    const firstKey = breadcrumbCache.keys().next().value;
    breadcrumbCache.delete(firstKey);
  }

  return breadcrumbs;
};

// Cache invalidation helper
export const invalidateProjectCache = (projectId) => {
  if (projectId) {
    projectNameCache.delete(projectId);
  }
  // Clear breadcrumb cache entries containing this project
  for (const [pathname] of breadcrumbCache) {
    if (pathname.includes(`/projects/${projectId}`)) {
      breadcrumbCache.delete(pathname);
    }
  }
};

export const getNavigationItems = (filter = {}) => {
  return navigationRoutes.filter(route => {
    // When the filter property is explicitly provided (true or false)
    // we require an exact boolean match.  Missing values on the route
    // are treated as false.

    if (filter.showInSidebar !== undefined) {
      if (!!route.showInSidebar !== filter.showInSidebar) return false;
    }

    if (filter.showMobileQuickAction !== undefined) {
      if (!!route.showMobileQuickAction !== filter.showMobileQuickAction) return false;
    }

    return true;
  });
};

export default {
  isActivePath,
  getActiveNavStyles,
  getSidebarActiveStyles,
  generateBreadcrumbs,
  getNavigationItems
};