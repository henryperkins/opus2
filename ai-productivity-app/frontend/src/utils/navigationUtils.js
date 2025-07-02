import { navigationRoutes, projectSubRoutes, pageRoutes } from '../config/navigationConfig';

export const isActivePath = (currentPath, targetPath) => {
  if (targetPath === '/') {
    return currentPath === '/';
  }
  return currentPath.startsWith(targetPath);
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

export const generateBreadcrumbs = (pathname) => {
  const paths = pathname.split('/').filter(Boolean);
  const breadcrumbs = [{ name: 'Dashboard', path: '/' }];

  if (paths.length > 0) {
    const first = paths[0];
    if (first === 'projects') {
      breadcrumbs.push({ name: 'Projects', path: '/projects' });
      if (paths[1]) {
        breadcrumbs.push({ name: 'Project', path: `/projects/${paths[1]}` });
        if (paths[2] && projectSubRoutes[paths[2]]) {
          breadcrumbs.push({
            name: projectSubRoutes[paths[2]].breadcrumbLabel,
            path: pathname
          });
        }
      }
    } else if (pageRoutes[first]) {
      breadcrumbs.push({
        name: pageRoutes[first],
        path: pathname
      });
    } else {
      breadcrumbs.push({
        name: first.charAt(0).toUpperCase() + first.slice(1),
        path: pathname
      });
    }
  }

  return breadcrumbs;
};

export const getNavigationItems = (filter = {}) => {
  return navigationRoutes.filter(route => {
    if (filter.showInSidebar && !route.showInSidebar) return false;
    if (filter.showInHeader && !route.showInHeader) return false;
    if (filter.showMobileQuickAction && !route.showMobileQuickAction) return false;
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