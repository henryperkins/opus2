import { NAVIGATION_STYLES } from "../constants/navigation";
import {
  navigationRoutes,
  projectSubRoutes,
  pageRoutes,
} from "../config/navigationConfig";

export class NavigationManager {
  static isActivePath(currentPath, targetPath) {
    const normalize = (path) => {
      try {
        return decodeURIComponent(path).toLowerCase().replace(/\/$/, "") || "/";
      } catch {
        return path.toLowerCase().replace(/\/$/, "") || "/";
      }
    };

    const normalizedCurrent = normalize(currentPath);
    const normalizedTarget = normalize(targetPath);

    if (normalizedTarget === "/") {
      return normalizedCurrent === "/";
    }

    const currentSegments = normalizedCurrent.split("/").filter(Boolean);
    const targetSegments = normalizedTarget.split("/").filter(Boolean);

    if (targetSegments.length > currentSegments.length) return false;

    return targetSegments.every(
      (segment, index) => currentSegments[index] === segment,
    );
  }

  static getActiveStyles(isActive, variant = "default") {
    return isActive
      ? NAVIGATION_STYLES.active[variant]
      : NAVIGATION_STYLES.inactive[variant];
  }

  static generateBreadcrumbs(pathname, project = null) {
    const cleanPath = pathname.split("?")[0].split("#")[0];
    const segments = cleanPath.split("/").filter(Boolean);
    const breadcrumbs = [{ name: "Dashboard", path: "/", icon: "Home" }];

    if (segments.length === 0) return breadcrumbs;

    const [first, second, third, ...rest] = segments;

    if (first === "projects") {
      breadcrumbs.push({
        name: "Projects",
        path: "/projects",
        icon: "FolderOpen",
      });

      if (second && second !== "new") {
        const projectName = project?.title || project?.name || "Project";
        breadcrumbs.push({
          name: projectName,
          path: `/projects/${second}`,
          icon: "Folder",
        });

        if (third && projectSubRoutes[third]) {
          breadcrumbs.push({
            name: projectSubRoutes[third].breadcrumbLabel,
            path: `/${segments.slice(0, 3).join("/")}`,
            icon: projectSubRoutes[third].icon,
          });
        }
      }
    } else if (pageRoutes[first]) {
      breadcrumbs.push({
        name: pageRoutes[first],
        path: `/${first}`,
        icon:
          navigationRoutes.find((r) => r.path === `/${first}`)?.icon || "File",
      });
    }

    return breadcrumbs;
  }

  static getNavigationItems(filter = {}) {
    return navigationRoutes.filter((route) => {
      for (const [key, value] of Object.entries(filter)) {
        if (value !== undefined && !!route[key] !== value) return false;
      }
      return true;
    });
  }

  static parseRouteParams(pathname) {
    const segments = pathname.split("/").filter(Boolean);
    const params = {
      projectId: null,
      sessionId: null,
      subPath: null,
      isProjectRoute: false,
    };

    if (segments[0] === "projects" && segments[1]) {
      params.isProjectRoute = true;
      params.projectId = segments[1];

      if (segments[2]) {
        params.subPath = segments[2];
        if (segments[2] === "chat" && segments[3]) {
          params.sessionId = segments[3];
        }
      }
    }

    return params;
  }

  // Consolidated navigation helpers for backward compatibility
  static createNavigationHelpers(navigate, location, onMobileClose) {
    const navigateAndClose = (path) => {
      navigate(path);
      if (window.innerWidth < 768 && onMobileClose) {
        onMobileClose();
      }
    };

    return {
      navigateToProject: (projectId, subPath = "") => {
        navigateAndClose(
          `/projects/${projectId}${subPath ? `/${subPath}` : ""}`,
        );
      },
      navigateToProjectChat: (projectId, sessionId = null) => {
        navigateAndClose(
          sessionId
            ? `/projects/${projectId}/chat/${sessionId}`
            : `/projects/${projectId}/chat`,
        );
      },
      navigateToNewChat: () => navigateAndClose("/projects/new/chat"),
      navigateToProjects: () => navigateAndClose("/projects"),
      isCurrentPath: (path) => location.pathname === path,
      isPathActive: (path) =>
        NavigationManager.isActivePath(location.pathname, path),
    };
  }
}

// Export as default for easy migration
export default NavigationManager;
