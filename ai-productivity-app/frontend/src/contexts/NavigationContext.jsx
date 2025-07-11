import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import { useLocation, useParams } from "react-router-dom";
import { NavigationManager } from "../utils/navigation";
import { projectAPI } from "../api/projects";

const NavigationContext = createContext(null);

export function useNavigation() {
  const context = useContext(NavigationContext);
  if (!context) {
    throw new Error("useNavigation must be used within NavigationProvider");
  }
  return context;
}

export function NavigationProvider({ children }) {
  const location = useLocation();
  const params = useParams();
  const [breadcrumbs, setBreadcrumbs] = useState([]);
  const [project, setProject] = useState(null);
  const [contextActions, setContextActions] = useState([]);
  const [loadingProject, setLoadingProject] = useState(false);

  // Load project data when projectId changes
  useEffect(() => {
    const loadProject = async () => {
      const routeParams = NavigationManager.parseRouteParams(location.pathname);

      if (routeParams.projectId && routeParams.projectId !== "new") {
        setLoadingProject(true);
        try {
          const projectData = await projectAPI.get(routeParams.projectId);
          setProject(projectData);
        } catch (error) {
          console.error("Failed to load project:", error);
          setProject(null);
        } finally {
          setLoadingProject(false);
        }
      } else {
        setProject(null);
      }
    };

    loadProject();
  }, [location.pathname]);

  // Update breadcrumbs when location or project changes
  useEffect(() => {
    const crumbs = NavigationManager.generateBreadcrumbs(
      location.pathname,
      project,
    );
    setBreadcrumbs(crumbs);
  }, [location.pathname, project]);

  // Determine context actions based on current route
  useEffect(() => {
    const routeParams = NavigationManager.parseRouteParams(location.pathname);
    const actions = [];

    if (routeParams.subPath === "chat") {
      actions.push(
        { id: "knowledge", icon: "Brain", title: "Knowledge Assistant" },
        { id: "editor", icon: "Code2", title: "Code Editor" },
        { id: "search", icon: "Search", title: "Search" },
      );
    } else if (routeParams.subPath === "files") {
      actions.push(
        { id: "upload", icon: "Upload", title: "Upload Files" },
        { id: "search", icon: "Search", title: "Search Files" },
      );
    } else if (routeParams.subPath === "knowledge") {
      actions.push(
        { id: "import", icon: "Database", title: "Import Documents" },
        { id: "search", icon: "Search", title: "Search Knowledge" },
      );
    }

    // Always add analytics and settings for project routes
    if (routeParams.isProjectRoute) {
      actions.push(
        { id: "analytics", icon: "BarChart2", title: "Analytics" },
        { id: "settings", icon: "Settings", title: "Project Settings" },
      );
    }

    setContextActions(actions);
  }, [location.pathname]);

  const isActivePath = useCallback(
    (path) => {
      return NavigationManager.isActivePath(location.pathname, path);
    },
    [location.pathname],
  );

  const getActiveStyles = useCallback(
    (path, variant = "default") => {
      return NavigationManager.getActiveStyles(isActivePath(path), variant);
    },
    [isActivePath],
  );

  const value = {
    breadcrumbs,
    project,
    loadingProject,
    contextActions,
    isActivePath,
    getActiveStyles,
    routeParams: NavigationManager.parseRouteParams(location.pathname),
  };

  return (
    <NavigationContext.Provider value={value}>
      {children}
    </NavigationContext.Provider>
  );
}
