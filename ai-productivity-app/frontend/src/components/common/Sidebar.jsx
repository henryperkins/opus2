import { useState, useEffect, useCallback, useMemo } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import PropTypes from 'prop-types';
import { useAuth } from '../../hooks/useAuth';
import { useProjectSearch } from '../../hooks/useProjects';
import useAuthStore from '../../stores/authStore';
import chatAPI from '../../api/chat';
import ThemeToggle from './ThemeToggle';
import KeyboardShortcutsModal from '../modals/KeyboardShortcutsModal';
import WhatsNewModal from '../modals/WhatsNewModal';
import DocumentationModal from '../modals/DocumentationModal';
import { useMediaQuery } from '../../hooks/useMediaQuery';
import { getNavigationItems, isActivePath, getSidebarActiveStyles } from '../../utils/navigationUtils';
import {
  Plus, FolderOpen, Clock, Star, Search, Settings, HelpCircle,
  ChevronDown, Home, MessageSquare, FileText, BarChart3, Database,
  PinIcon, X, Keyboard
} from 'lucide-react';

// Visual indicator for color with proper contrast - moved outside to prevent recreation
const ColorDot = ({ color }) => {
  const backgroundColor = color || '#6B7280';
  // Ensure minimum contrast by darkening light colors
  const isLightColor = (hex) => {
    const rgb = parseInt(hex.slice(1), 16);
    const r = (rgb >> 16) & 0xff;
    const g = (rgb >> 8) & 0xff;
    const b = (rgb >> 0) & 0xff;
    const luminance = 0.299 * r + 0.587 * g + 0.114 * b;
    return luminance > 186;
  };
  
  const finalColor = color && isLightColor(color) 
    ? `color-mix(in srgb, ${color} 70%, black)` 
    : backgroundColor;
  
  return (
    <div
      className="w-2 h-2 rounded-full shrink-0"
      style={{ backgroundColor: finalColor }}
      role="img"
      aria-label={color ? `Project color indicator: ${color}` : 'Default project color'}
    />
  );
};

ColorDot.propTypes = {
  color: PropTypes.string
};

const Sidebar = ({ isOpen = true, onToggle, className = '' }) => {
  const { user } = useAuth();
  const { isDesktop } = useMediaQuery();
  const navigate = useNavigate();
  const location = useLocation();
  const { projectId, sessionId } = useParams();
  const { projects, loading: projectsLoading, search } = useProjectSearch();
  const { preferences } = useAuthStore();

  const { setSidebarPinned, setCollapsedSection, getSectionCollapsed } = useAuthStore();
  const isPinned = preferences?.sidebarPinned || false;
  
  // Use helper function to get collapsed state with defaults
  const isCollapsed = useCallback((section) => getSectionCollapsed(section), [getSectionCollapsed]);
  const [recentChats, setRecentChats] = useState([]);
  const [starredItems, setStarredItems] = useState([]);
  const [loadingRecentChats, setLoadingRecentChats] = useState(false);
  const [recentChatsError, setRecentChatsError] = useState(null);
  const [isKeyboardShortcutsModalOpen, setKeyboardShortcutsModalOpen] = useState(false);
  const [isWhatsNewModalOpen, setWhatsNewModalOpen] = useState(false);
  const [isDocumentationModalOpen, setDocumentationModalOpen] = useState(false);

  // Close sidebar on mobile after navigation
  const closeOnMobile = () => {
    if (!isDesktop && onToggle) onToggle();
  };

  // Load recent chats - only when Recent section is first expanded
  const loadRecentChats = useCallback(async () => {
    if (!user || recentChats.length > 0) return; // Don't reload if already loaded
    setLoadingRecentChats(true);
    setRecentChatsError(null);
    try {

      // Axios returns {data, status, ...}.  API might also be pre-wrapped {sessions:[…]}
      const axiosResp = await chatAPI.getChatSessions();
      const raw = axiosResp?.data ?? axiosResp;                   // normalise
      const sessionsArray = Array.isArray(raw) ? raw : raw.sessions ?? [];
      const sortedSessions = [...sessionsArray]
        .sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))
        .slice(0, 5);
      setRecentChats(sortedSessions);
    } catch (error) {
      console.error('Failed to load recent chats:', error);
      setRecentChatsError('Failed to load recent chats');
    } finally {
      setLoadingRecentChats(false);
    }
  }, [user, recentChats.length]);

  // Load recent chats when section is expanded
  useEffect(() => {
    if (!isCollapsed('recent') && user && recentChats.length === 0) {
      loadRecentChats();
    }
  }, [isCollapsed, user, recentChats.length, loadRecentChats]);

  // Navigation helpers
  const handleNewChat = () => {
    navigate('/projects/new/chat');
    closeOnMobile();
  };

  const handleNewProject = () => {
    navigate('/projects');
    // This should trigger the create modal on the projects page
    closeOnMobile();
  };

  const handleProjectChatNavigation = (project) => {
    navigate(`/projects/${project.id}/chat`);
    closeOnMobile();
  };

  const toggleSection = (section) => {
    setCollapsedSection(section, !isCollapsed(section));
  };

  // Memoize navigation items to prevent unnecessary recomputations
  const navigationItems = useMemo(() => getNavigationItems({ showInSidebar: true }), []);


  return (
    <>
      <div 
      id="sidebar-menu"
      className={`flex flex-col h-full bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 w-64 lg:w-72 ${className}`}
    >
        {/* Header with logo and pin button */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <Link to="/" className="flex items-center space-x-2 no-underline">
            <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg flex items-center justify-center transition-all duration-200 transform-gpu hover:scale-110 shadow-lg/20 hover:shadow-xl/30">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <span className="text-lg font-bold bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent dark:from-gray-100 dark:to-gray-300 text-shadow-sm text-shadow-black/20">
              AI Productivity
            </span>
          </Link>

          <div className="flex items-center space-x-2">
            {isDesktop && (
              <button
                onClick={() => setSidebarPinned(!isPinned)}
                className={`p-1.5 rounded-md transition-colors ${
                  isPinned
                    ? 'text-blue-600 bg-blue-50 dark:bg-blue-900/20'
                    : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'
                }`}
                title={isPinned ? 'Unpin sidebar' : 'Pin sidebar'}
              >
                <PinIcon className={`w-4 h-4 ${isPinned ? '' : 'rotate-45'}`} />
              </button>
            )}
            {!isDesktop && onToggle && (
              <button
                onClick={onToggle}
                className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-md"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Action buttons */}
        <div className="p-4 space-y-2 border-b border-gray-200 dark:border-gray-700">
          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-center space-x-2 px-4 py-2.5 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white rounded-lg font-medium transition-all duration-200 shadow-sm hover:shadow-md"
          >
            <Plus className="w-4 h-4" />
            <span>New Chat</span>
          </button>

          <button
            onClick={handleNewProject}
            className="w-full flex items-center justify-center space-x-2 px-4 py-2.5 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-lg font-medium transition-colors duration-200"
          >
            <FolderOpen className="w-4 h-4" />
            <span>New Project</span>
          </button>
        </div>

        {/* Navigation sections */}
        <nav className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Recent Chats */}
          <div>
            <button
              onClick={() => toggleSection('recent')}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  toggleSection('recent');
                }
              }}
              className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
              aria-expanded={!isCollapsed('recent')}
              aria-controls="recent-section"
            >
              <div className="flex items-center space-x-2">
                <Clock className="w-4 h-4" />
                <span>Recent</span>
              </div>
              <ChevronDown className={`w-4 h-4 transition-transform ${isCollapsed('recent') ? '' : 'rotate-180'}`} />
            </button>

            {!isCollapsed('recent') && (
              <div className="mt-2 space-y-1" id="recent-section">
                {loadingRecentChats ? (
                  <div className="px-3 py-2 text-sm text-gray-500">
                    <div className="animate-pulse">Loading...</div>
                  </div>
                ) : recentChats.length > 0 ? (
                  recentChats.map((chat) => {
                    const isActive = sessionId === chat.id;
                    return (
                      <Link
                        key={chat.id}
                        to={`/projects/${chat.project_id}/chat/${chat.id}`}
                        onClick={closeOnMobile}
                        className={`block px-3 py-2 text-sm rounded-lg truncate transition-colors ${
                          isActive
                            ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                            : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                        }`}
                      >
                        <div className="flex items-center space-x-2">
                          <MessageSquare className="w-3.5 h-3.5 flex-shrink-0" />
                          <span className="truncate">{chat.title || 'Untitled Chat'}</span>
                        </div>
                      </Link>
                    );
                  })
                ) : recentChatsError ? (
                  <div className="px-3 py-2 space-y-2">
                    <div className="text-sm text-red-500 dark:text-red-400">
                      {recentChatsError}
                    </div>
                    <button
                      onClick={loadRecentChats}
                      className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                    >
                      Try again
                    </button>
                  </div>
                ) : (
                  <div className="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">
                    No recent chats
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Starred Items */}
          <div>
            <button
              onClick={() => toggleSection('starred')}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  toggleSection('starred');
                }
              }}
              className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
              aria-expanded={!isCollapsed('starred')}
              aria-controls="starred-section"
            >
              <div className="flex items-center space-x-2">
                <Star className="w-4 h-4" />
                <span>Starred</span>
              </div>
              <ChevronDown className={`w-4 h-4 transition-transform ${isCollapsed('starred') ? '' : 'rotate-180'}`} />
            </button>

            {!isCollapsed('starred') && (
              <div className="mt-2 px-3 py-2 text-sm text-gray-500 dark:text-gray-400" id="starred-section">
                No starred items yet
              </div>
            )}
          </div>

          {/* Projects */}
          <div>
            <button
              onClick={() => toggleSection('projects')}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  toggleSection('projects');
                }
              }}
              className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
              aria-expanded={!isCollapsed('projects')}
              aria-controls="projects-section"
            >
              <div className="flex items-center space-x-2">
                <FolderOpen className="w-4 h-4" />
                <span>Projects</span>
              </div>
              <ChevronDown className={`w-4 h-4 transition-transform ${isCollapsed('projects') ? '' : 'rotate-180'}`} />
            </button>

            {!isCollapsed('projects') && (
              <div className="mt-2 space-y-1" id="projects-section">
                <Link
                  to="/projects"
                  onClick={closeOnMobile}
                  className={`flex items-center space-x-2 px-3 py-2 text-sm rounded-lg transition-colors ${
                    getSidebarActiveStyles(isActivePath(location.pathname, '/projects'))
                  }`}
                >
                  <BarChart3 className="w-4 h-4" />
                  <span>All Projects</span>
                </Link>

                {projectsLoading && projects.length === 0 ? (
                  <div className="px-3 py-2 text-sm text-gray-500">
                    <div className="animate-pulse">Loading projects...</div>
                  </div>
                ) : (
                  projects.slice(0, 5).map((project) => (
                    <button
                      key={project.id}
                      onClick={() => handleProjectChatNavigation(project)}
                      className="w-full flex items-center space-x-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors group"
                    >
                      <ColorDot color={project.color} />
                      <span className="truncate flex-1 text-left">{project.title}</span>
                      {project.status === 'active' && (
                        <div className="w-2 h-2 bg-green-400 rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
                      )}
                    </button>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Main Navigation */}
          <div className="pt-4 space-y-1 border-t border-gray-200 dark:border-gray-700">
            {navigationItems.map(item => {
              const IconComponent = item.icon;
              const isActive = isActivePath(location.pathname, item.path);
              return (
                <Link
                  key={item.id}
                  to={item.path}
                  onClick={closeOnMobile}
                  className={`flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    getSidebarActiveStyles(isActive)
                  }`}
                >
                  <IconComponent className="w-4 h-4" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </div>

          {/* Help & Resources */}
          <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={() => toggleSection('help')}
              className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
              aria-expanded={!isCollapsed('help')}
            >
              <div className="flex items-center space-x-2">
                <HelpCircle className="w-4 h-4" />
                <span>Help & Resources</span>
              </div>
              <ChevronDown className={`w-4 h-4 transition-transform ${isCollapsed('help') ? '' : 'rotate-180'}`} />
            </button>

            {!isCollapsed('help') && (
              <div className="mt-2 space-y-1">
                <button
                  onClick={() => setDocumentationModalOpen(true)}
                  className="w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                >
                  <FileText className="w-4 h-4" />
                  <span>Documentation</span>
                </button>
                <button
                  onClick={() => setKeyboardShortcutsModalOpen(true)}
                  className="w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                >
                  <Keyboard className="w-4 h-4" />
                  <span>Keyboard Shortcuts</span>
                </button>
              </div>
            )}
          </div>
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 space-y-3">
          {/* Settings */}
          <Link
            to="/settings"
            onClick={closeOnMobile}
            className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              getSidebarActiveStyles(isActivePath(location.pathname, '/settings'))
            }`}
          >
            <Settings className="w-4 h-4" />
            <span>Settings</span>
          </Link>

          {/* User Info */}
          {user && (
            <div className="flex items-center space-x-3 px-3 py-2 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center text-white text-sm font-medium shadow-sm">
                {user.username?.charAt(0)?.toUpperCase() || 'U'}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                  {user.username}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                  {user.email}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Modals */}
      <KeyboardShortcutsModal isOpen={isKeyboardShortcutsModalOpen} onClose={() => setKeyboardShortcutsModalOpen(false)} />
      <WhatsNewModal isOpen={isWhatsNewModalOpen} onClose={() => setWhatsNewModalOpen(false)} />
      <DocumentationModal isOpen={isDocumentationModalOpen} onClose={() => setDocumentationModalOpen(false)} />
    </>
  );
};

Sidebar.defaultProps = {
  isOpen: true,
  onToggle: () => {},
  className: '',
};

Sidebar.propTypes = {
  isOpen: PropTypes.bool,
  onToggle: PropTypes.func,
  className: PropTypes.string,
};

export default Sidebar;
