/**
 * Navigation Helpers - Centralized navigation utilities
 * 
 * Consolidates duplicated navigation logic across components
 */
import { useNavigate, useLocation } from 'react-router-dom';
import { useCallback } from 'react';
import { useMediaQuery } from '../hooks/useMediaQuery';

/**
 * Custom hook for navigation with mobile-aware closing
 */
export const useNavigationHelpers = (onMobileClose) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { isMobile } = useMediaQuery();

  const navigateAndClose = useCallback((path, options = {}) => {
    navigate(path, options);
    if (isMobile && onMobileClose) {
      onMobileClose();
    }
  }, [navigate, isMobile, onMobileClose]);

  const navigateToProject = useCallback((projectId, subPath = '') => {
    const path = `/projects/${projectId}${subPath ? `/${subPath}` : ''}`;
    navigateAndClose(path);
  }, [navigateAndClose]);

  const navigateToProjectChat = useCallback((projectId, sessionId = null) => {
    const path = sessionId 
      ? `/projects/${projectId}/chat/${sessionId}`
      : `/projects/${projectId}/chat`;
    navigateAndClose(path);
  }, [navigateAndClose]);

  const navigateToNewChat = useCallback(() => {
    navigateAndClose('/projects/new/chat');
  }, [navigateAndClose]);

  const navigateToProjects = useCallback(() => {
    navigateAndClose('/projects');
  }, [navigateAndClose]);

  const isCurrentPath = useCallback((path) => {
    return location.pathname === path;
  }, [location.pathname]);

  const isPathActive = useCallback((path) => {
    // Reuse existing logic from navigationUtils
    const normalizeAndDecode = (path) => {
      try {
        const decoded = decodeURIComponent(path);
        return decoded.toLowerCase().replace(/\/$/, '') || '/';
      } catch {
        return path.toLowerCase().replace(/\/$/, '') || '/';
      }
    };

    const normalizedCurrent = normalizeAndDecode(location.pathname);
    const normalizedTarget = normalizeAndDecode(path);

    if (normalizedTarget === '/') {
      return normalizedCurrent === '/';
    }
    
    const currentSegments = normalizedCurrent.split('/').filter(Boolean);
    const targetSegments = normalizedTarget.split('/').filter(Boolean);
    
    if (targetSegments.length > currentSegments.length) {
      return false;
    }
    
    return targetSegments.every((segment, index) => 
      currentSegments[index] === segment
    );
  }, [location.pathname]);

  return {
    navigate: navigateAndClose,
    navigateToProject,
    navigateToProjectChat,
    navigateToNewChat,
    navigateToProjects,
    isCurrentPath,
    isPathActive,
    location,
  };
};

/**
 * Common navigation actions for buttons/links
 */
export const createNavigationActions = (navigationHelpers) => ({
  handleNewChat: () => navigationHelpers.navigateToNewChat(),
  handleNewProject: () => navigationHelpers.navigateToProjects(),
  handleProjectNavigation: (projectId) => navigationHelpers.navigateToProject(projectId),
  handleProjectChatNavigation: (projectId, sessionId) => 
    navigationHelpers.navigateToProjectChat(projectId, sessionId),
});

/**
 * Generate consistent styling for active navigation items
 */
export const generateNavItemStyles = (isActive, variant = 'default') => {
  const variants = {
    default: {
      active: 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300',
      inactive: 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700',
    },
    sidebar: {
      active: 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300',
      inactive: 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800',
    },
    mobile: {
      active: 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300',
      inactive: 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700',
    },
  };

  const styles = variants[variant] || variants.default;
  return isActive ? styles.active : styles.inactive;
};

/**
 * Extract current project and session from URL params
 */
export const useRouteParams = () => {
  const location = useLocation();
  
  const getRouteParams = useCallback(() => {
    const pathSegments = location.pathname.split('/').filter(Boolean);
    
    const params = {
      projectId: null,
      sessionId: null,
      subPath: null,
    };

    if (pathSegments[0] === 'projects' && pathSegments[1]) {
      params.projectId = pathSegments[1];
      
      if (pathSegments[2]) {
        params.subPath = pathSegments[2];
        
        if (pathSegments[2] === 'chat' && pathSegments[3]) {
          params.sessionId = pathSegments[3];
        }
      }
    }

    return params;
  }, [location.pathname]);

  return getRouteParams();
};

/**
 * Hook for handling common modal close patterns
 */
export const useModalClose = (onClose) => {
  const { isMobile } = useMediaQuery();

  const handleClose = useCallback((event) => {
    // Prevent event bubbling
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    
    if (onClose) {
      onClose();
    }
  }, [onClose]);

  const handleOverlayClose = useCallback((event) => {
    // Only close if clicking the overlay itself
    if (event.target === event.currentTarget) {
      handleClose(event);
    }
  }, [handleClose]);

  const handleEscapeClose = useCallback((event) => {
    if (event.key === 'Escape') {
      handleClose(event);
    }
  }, [handleClose]);

  return {
    handleClose,
    handleOverlayClose,
    handleEscapeClose,
    isMobile,
  };
};

export default {
  useNavigationHelpers,
  createNavigationActions,
  generateNavItemStyles,
  useRouteParams,
  useModalClose,
};
