import { useState, useEffect, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { useNavigation } from "../../contexts/NavigationContext";
import { NavigationManager } from "../../utils/navigation";
import { useProjectSearch } from "../../hooks/useProjects";
import useAuthStore from "../../stores/authStore";
import chatAPI from "../../api/chat";
import * as Icons from "lucide-react";
import {
  Plus,
  FolderOpen,
  Clock,
  Star,
  Search,
  Settings,
  HelpCircle,
  ChevronDown,
  MessageSquare,
  PinIcon,
  X,
  Keyboard,
  FileText,
} from "lucide-react";
import UnifiedModal from "../common/UnifiedModal";

// Color dot component for projects
const ProjectColorDot = ({ color }) => {
  const backgroundColor = color || "#6B7280";
  return (
    <div
      className="w-2 h-2 rounded-full shrink-0"
      style={{ backgroundColor }}
      role="img"
      aria-label={`Project color: ${color || "default"}`}
    />
  );
};

export default function UnifiedSidebar({ isOpen = true, onClose }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { isActivePath, getActiveStyles } = useNavigation();
  const { projects, loading: projectsLoading } = useProjectSearch();
  const {
    preferences,
    setSidebarPinned,
    setCollapsedSection,
    getSectionCollapsed,
  } = useAuthStore();

  const isPinned = preferences?.sidebarPinned || false;
  const [recentChats, setRecentChats] = useState([]);
  const [loadingRecentChats, setLoadingRecentChats] = useState(false);
  const [showKeyboardShortcuts, setShowKeyboardShortcuts] = useState(false);
  const [showDocumentation, setShowDocumentation] = useState(false);

  // Load recent chats when section expands
  const loadRecentChats = useCallback(async () => {
    if (!user || recentChats.length > 0) return;

    setLoadingRecentChats(true);
    try {
      const response = await chatAPI.getChatSessions();
      const sessions =
        response?.data?.sessions || response?.sessions || response || [];
      setRecentChats(sessions.slice(0, 5));
    } catch (error) {
      console.error("Failed to load recent chats:", error);
    } finally {
      setLoadingRecentChats(false);
    }
  }, [user, recentChats.length]);

  useEffect(() => {
    if (!getSectionCollapsed("recent") && user && recentChats.length === 0) {
      loadRecentChats();
    }
  }, [getSectionCollapsed, user, recentChats.length, loadRecentChats]);

  const toggleSection = (section) => {
    setCollapsedSection(section, !getSectionCollapsed(section));
  };

  const navigationItems = NavigationManager.getNavigationItems({
    showInSidebar: true,
  });

  return (
    <>
      <div className="flex flex-col h-full bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <Link to="/" className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
              <svg
                className="w-5 h-5 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                />
              </svg>
            </div>
            <span className="text-lg font-bold text-gray-900 dark:text-gray-100">
              AI Productivity
            </span>
          </Link>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setSidebarPinned(!isPinned)}
              className={`p-1.5 rounded-md transition-colors hidden lg:block ${
                isPinned
                  ? "text-blue-600 bg-blue-50 dark:bg-blue-900/20"
                  : "text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              }`}
              title={isPinned ? "Unpin sidebar" : "Pin sidebar"}
            >
              <PinIcon className={`w-4 h-4 ${isPinned ? "" : "rotate-45"}`} />
            </button>

            {onClose && (
              <button
                onClick={onClose}
                className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-md lg:hidden"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="p-4 space-y-2 border-b border-gray-200 dark:border-gray-700">
          <button
            onClick={() => navigate("/projects/new/chat")}
            className="w-full flex items-center justify-center space-x-2 px-4 py-2.5 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white rounded-lg font-medium transition-all duration-200 shadow-sm hover:shadow-md"
          >
            <Plus className="w-4 h-4" />
            <span>New Chat</span>
          </button>

          <button
            onClick={() => navigate("/projects")}
            className="w-full flex items-center justify-center space-x-2 px-4 py-2.5 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-lg font-medium transition-colors"
          >
            <FolderOpen className="w-4 h-4" />
            <span>New Project</span>
          </button>
        </div>

        {/* Navigation Sections */}
        <nav className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Recent Chats Section */}
          <CollapsibleSection
            title="Recent"
            icon={Clock}
            isCollapsed={getSectionCollapsed("recent")}
            onToggle={() => toggleSection("recent")}
          >
            {loadingRecentChats ? (
              <LoadingState />
            ) : recentChats.length > 0 ? (
              recentChats.map((chat) => (
                <Link
                  key={chat.id}
                  to={`/projects/${chat.project_id}/chat/${chat.id}`}
                  className={`block px-3 py-2 text-sm rounded-lg truncate transition-colors ${getActiveStyles(
                    `/projects/${chat.project_id}/chat/${chat.id}`,
                  )}`}
                >
                  <div className="flex items-center space-x-2">
                    <MessageSquare className="w-3.5 h-3.5 flex-shrink-0" />
                    <span className="truncate">
                      {chat.title || "Untitled Chat"}
                    </span>
                  </div>
                </Link>
              ))
            ) : (
              <EmptyState text="No recent chats" />
            )}
          </CollapsibleSection>

          {/* Projects Section */}
          <CollapsibleSection
            title="Projects"
            icon={FolderOpen}
            isCollapsed={getSectionCollapsed("projects")}
            onToggle={() => toggleSection("projects")}
          >
            <Link
              to="/projects"
              className={`flex items-center space-x-2 px-3 py-2 text-sm rounded-lg transition-colors ${getActiveStyles(
                "/projects",
                "sidebar",
              )}`}
            >
              <Icons.BarChart3 className="w-4 h-4" />
              <span>All Projects</span>
            </Link>

            {projectsLoading ? (
              <LoadingState />
            ) : (
              projects.slice(0, 5).map((project) => (
                <button
                  key={project.id}
                  onClick={() => navigate(`/projects/${project.id}/chat`)}
                  className="w-full flex items-center space-x-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                >
                  <ProjectColorDot color={project.color} />
                  <span className="truncate flex-1 text-left">
                    {project.title}
                  </span>
                </button>
              ))
            )}
          </CollapsibleSection>

          {/* Main Navigation */}
          <div className="pt-4 space-y-1 border-t border-gray-200 dark:border-gray-700">
            {navigationItems.map((item) => {
              const Icon = Icons[item.icon] || item.icon;
              return (
                <Link
                  key={item.id}
                  to={item.path}
                  className={`flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${getActiveStyles(
                    item.path,
                    "sidebar",
                  )}`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </div>

          {/* Help Section */}
          <CollapsibleSection
            title="Help & Resources"
            icon={HelpCircle}
            isCollapsed={getSectionCollapsed("help")}
            onToggle={() => toggleSection("help")}
          >
            <button
              onClick={() => setShowDocumentation(true)}
              className="w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              <FileText className="w-4 h-4" />
              <span>Documentation</span>
            </button>
            <button
              onClick={() => setShowKeyboardShortcuts(true)}
              className="w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              <Keyboard className="w-4 h-4" />
              <span>Keyboard Shortcuts</span>
            </button>
          </CollapsibleSection>
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-700">
          <Link
            to="/settings"
            className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${getActiveStyles(
              "/settings",
              "sidebar",
            )}`}
          >
            <Settings className="w-4 h-4" />
            <span>Settings</span>
          </Link>
        </div>
      </div>

      {/* Modals */}
      {showKeyboardShortcuts && (
        <UnifiedModal
          isOpen={showKeyboardShortcuts}
          onClose={() => setShowKeyboardShortcuts(false)}
          title="Keyboard Shortcuts"
          size="lg"
        >
          <div className="space-y-4">
            <div className="grid gap-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  Open command palette
                </span>
                <kbd className="px-2 py-1 text-xs font-mono bg-gray-100 dark:bg-gray-700 rounded">
                  ⌘ K
                </kbd>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  New chat
                </span>
                <kbd className="px-2 py-1 text-xs font-mono bg-gray-100 dark:bg-gray-700 rounded">
                  N
                </kbd>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  Focus chat input
                </span>
                <kbd className="px-2 py-1 text-xs font-mono bg-gray-100 dark:bg-gray-700 rounded">
                  ⌘ J
                </kbd>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  Toggle sidebar
                </span>
                <kbd className="px-2 py-1 text-xs font-mono bg-gray-100 dark:bg-gray-700 rounded">
                  ⌘ \\
                </kbd>
              </div>
            </div>
          </div>
        </UnifiedModal>
      )}

      {showDocumentation && (
        <UnifiedModal
          isOpen={showDocumentation}
          onClose={() => setShowDocumentation(false)}
          title="Documentation"
          size="2xl"
        >
          <div className="space-y-6">
            <div className="prose dark:prose-invert max-w-none">
              <h3>Getting Started</h3>
              <p>
                Welcome to AI Productivity! This application helps you manage
                projects, chat with AI, and organize your knowledge base.
              </p>

              <h3>Key Features</h3>
              <ul>
                <li>
                  <strong>Projects:</strong> Organize your work into projects
                  with chat, files, and knowledge bases
                </li>
                <li>
                  <strong>AI Chat:</strong> Interact with AI models for
                  assistance and collaboration
                </li>
                <li>
                  <strong>Knowledge Base:</strong> Upload and search through
                  documents and files
                </li>
                <li>
                  <strong>Code Analysis:</strong> Get AI assistance with your
                  code repositories
                </li>
              </ul>

              <h3>Quick Actions</h3>
              <ul>
                <li>Use the "New Chat" button to start a conversation</li>
                <li>Create projects to organize your work</li>
                <li>Upload files to build your knowledge base</li>
                <li>Use keyboard shortcuts for faster navigation</li>
              </ul>
            </div>
          </div>
        </UnifiedModal>
      )}
    </>
  );
}

// Collapsible Section Component
function CollapsibleSection({
  title,
  icon: Icon,
  isCollapsed,
  onToggle,
  children,
}) {
  return (
    <div>
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
        aria-expanded={!isCollapsed}
      >
        <div className="flex items-center space-x-2">
          <Icon className="w-4 h-4" />
          <span>{title}</span>
        </div>
        <ChevronDown
          className={`w-4 h-4 transition-transform ${isCollapsed ? "" : "rotate-180"}`}
        />
      </button>

      {!isCollapsed && <div className="mt-2 space-y-1">{children}</div>}
    </div>
  );
}

// Helper Components
const LoadingState = () => (
  <div className="px-3 py-2 text-sm text-gray-500">
    <div className="animate-pulse">Loading...</div>
  </div>
);

const EmptyState = ({ text }) => (
  <div className="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">
    {text}
  </div>
);
