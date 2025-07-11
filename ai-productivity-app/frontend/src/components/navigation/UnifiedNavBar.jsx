import { Link } from "react-router-dom";
import { Menu, ChevronRight, Home, Settings } from "lucide-react";
import * as Icons from "lucide-react";
import { useAuth } from "../../hooks/useAuth";
import { useNavigation } from "../../contexts/NavigationContext";
import UserMenu from "../auth/UserMenu";
import AIProviderStatus from "../common/AIProviderStatus";
import ThemeToggle from "../common/ThemeToggle";
import ConnectionIndicator from "../common/ConnectionIndicator";

export default function UnifiedNavBar({
  onMenuClick,
  showMenuButton = false,
  sidebarOpen = false,
  onContextAction,
}) {
  const { user, loading } = useAuth();
  const { breadcrumbs, project, contextActions, routeParams } = useNavigation();

  return (
    <header className="bg-white dark:bg-gray-800 shadow-sm sticky top-0 z-40">
      {/* Primary Navigation Bar */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <div className="px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Left: Menu + Breadcrumbs */}
            <div className="flex items-center flex-1 min-w-0">
              {showMenuButton && (
                <button
                  onClick={onMenuClick}
                  className="p-2 -ml-2 mr-3 rounded-md text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                  aria-label="Toggle sidebar"
                >
                  <Menu className="h-6 w-6" />
                </button>
              )}

              {/* Breadcrumbs */}
              <nav
                aria-label="Breadcrumb"
                className="flex items-center space-x-1 text-sm min-w-0"
              >
                {breadcrumbs.map((crumb, index) => {
                  const Icon = Icons[crumb.icon] || Home;
                  const isLast = index === breadcrumbs.length - 1;

                  return (
                    <div
                      key={`${crumb.path}-${index}`}
                      className="flex items-center min-w-0"
                    >
                      {index > 0 && (
                        <ChevronRight className="w-4 h-4 text-gray-400 mx-1 flex-shrink-0" />
                      )}

                      {isLast ? (
                        <span className="flex items-center space-x-1.5 text-gray-900 dark:text-gray-100 font-medium min-w-0">
                          <Icon className="w-4 h-4 flex-shrink-0" />
                          <span className="truncate">{crumb.name}</span>
                        </span>
                      ) : (
                        <Link
                          to={crumb.path}
                          className="flex items-center space-x-1.5 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors min-w-0"
                        >
                          <Icon className="w-4 h-4 flex-shrink-0" />
                          <span className="truncate">{crumb.name}</span>
                        </Link>
                      )}
                    </div>
                  );
                })}
              </nav>
            </div>

            {/* Right: Status + User */}
            <div className="flex items-center space-x-3 ml-4">
              <ConnectionIndicator className="hidden sm:block" />
              <AIProviderStatus className="hidden lg:block" />
              <ThemeToggle />

              {loading ? (
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600" />
              ) : user ? (
                <UserMenu />
              ) : (
                <Link
                  to="/login"
                  className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 rounded-md text-sm font-medium"
                >
                  Sign In
                </Link>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Context Bar - Project Info + Actions */}
      {routeParams.isProjectRoute && (
        <div className="px-4 sm:px-6 lg:px-8 py-2 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            {/* Project Info */}
            <div className="flex items-center space-x-3 min-w-0">
              {project && (
                <>
                  {project.color && (
                    <div
                      className="w-3 h-3 rounded-full flex-shrink-0"
                      style={{ backgroundColor: project.color }}
                    />
                  )}
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 truncate">
                    {project.title}
                  </h2>
                  {project.status && (
                    <span
                      className={`px-2 py-0.5 text-xs font-medium rounded-full flex-shrink-0 ${
                        project.status === "active"
                          ? "bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400"
                          : "bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400"
                      }`}
                    >
                      {project.status}
                    </span>
                  )}
                </>
              )}
            </div>

            {/* Context Actions */}
            {contextActions.length > 0 && (
              <div className="flex items-center space-x-1">
                {contextActions.map((action) => {
                  const Icon = Icons[action.icon] || Settings;
                  return (
                    <button
                      key={action.id}
                      onClick={() => onContextAction?.(action.id)}
                      className="p-2 rounded-lg text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                      title={action.title}
                    >
                      <Icon className="w-5 h-5" />
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
