/* Sidebar Component
 *
 * Purpose
 * -------
 * Claude.ai-inspired sidebar for AI Productivity App providing:
 *  • New Chat & Project creation
 *  • Recent & Starred items
 *  • Project organization
 *  • Quick settings & help
 *  • Mobile-responsive design
 *  • Collapsible sections
 */

import { useState, useEffect, useCallback } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import PropTypes from 'prop-types';
import { useAuth } from '../../hooks/useAuth';
import { useProjectSearch } from '../../hooks/useProjects';
import useAuthStore from '../../stores/authStore';
import chatAPI from '../../api/chat';
import ThemeToggle from './ThemeToggle';
import KeyboardShortcutsModal from '../modals/KeyboardShortcutsModal';
import WhatsNewModal from '../modals/WhatsNewModal';
import DocumentationModal from '../modals/DocumentationModal';
import { useMediaQuery } from '../../hooks/useMediaQuery';   // NEW

const Sidebar = ({ isOpen = false, onToggle, className = '' }) => {
  const { user } = useAuth();
  const { isDesktop } = useMediaQuery();            // NEW
  const navigate = useNavigate();
  const location = useLocation();
  const { projects, loading: projectsLoading, search } = useProjectSearch();
  const { preferences } = useAuthStore();

  const [isPinned, setIsPinned] = useState(preferences.sidebarPinned || false);
  const [collapsedSections, setCollapsedSections] = useState({
    recent: false,
    starred: false,
    projects: false,
    help: true,
  });
  const [recentChats, setRecentChats] = useState([]);
  const [starredItems, setStarredItems] = useState([]);
  const [loadingRecentChats, setLoadingRecentChats] = useState(false);
  const [recentChatsError, setRecentChatsError] = useState(null);
  const [isKeyboardShortcutsModalOpen, setKeyboardShortcutsModalOpen] = useState(false);
  const [isWhatsNewModalOpen, setWhatsNewModalOpen] = useState(false);
  const [isDocumentationModalOpen, setDocumentationModalOpen] = useState(false);

  // Helper to close sidebar on mobile/tablet after navigation
  const closeOnMobile = () => {           // NEW
    if (!isDesktop && !isPinned) onToggle();
  };

  // ---------------------------------------------------------------------------
  // Data loaders – wrapped in useCallback to keep references stable and avoid
  // infinite re-render loops when they are used inside useEffect.
  // ---------------------------------------------------------------------------

  const loadRecentChats = useCallback(async () => {
    if (!user) return;

    setLoadingRecentChats(true);
    setRecentChatsError(null);

    try {
      const response = await chatAPI.getSessionHistory({
        limit: 5,
        sort: 'updated_at',
        order: 'desc',
      });

      const items = response.data?.items || [];
      const formattedChats = items.map((session) => ({
        id: session.id,
        title: session.title || `Chat ${session.id}`,
        timestamp: new Date(session.updated_at),
        type: 'chat',
        projectId: session.project_id,
      }));

      setRecentChats(formattedChats);
    } catch (error) {
      console.error('Failed to load recent chats:', error);
      setRecentChatsError('Failed to load recent chats');
      setRecentChats([]);
    } finally {
      setLoadingRecentChats(false);
    }
  }, [user]);

  const loadStarredItems = useCallback(() => {
    setStarredItems([
      { id: 1, title: 'React Best Practices', type: 'chat', url: '/chat/1' },
      { id: 2, title: 'AI Productivity App', type: 'project', url: '/projects/1' },
    ]);
  }, []);

  // ---------------------------------------------------------------------------
  // Initial data fetch (runs once when component mounts or when user changes)
  // ---------------------------------------------------------------------------

  useEffect(() => {
    if (!user) return;

    // Trigger project search only if not already loaded
    if (projects.length === 0 && !projectsLoading) {
      search();
    }

    loadRecentChats();
    loadStarredItems();
  }, [user, projects.length, projectsLoading, search, loadRecentChats, loadStarredItems]);

  const toggleSection = (section) => {
    setCollapsedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const handleNewChat = () => {
    // Navigate to projects page for new chat creation
    navigate('/projects', { state: { action: 'new-chat' } });
    closeOnMobile();          // NEW
  };

  const handleNewProject = () => {
    navigate('/projects?action=create');
    closeOnMobile();          // NEW
  };

  const handleProjectChatNavigation = (project) => {
    // Ensure project exists and is valid before navigating
    if (!project || !project.id) {
      console.error('Invalid project for chat navigation:', project);
      return;
    }
    
    // Navigate with project context to avoid additional API calls
    navigate(`/projects/${project.id}/chat`, { 
      state: { project } 
    });
    closeOnMobile();          // NEW
  };

  const handleProjectAnalyticsNavigation = (project) => {
    navigate(`/projects/${project.id}/analytics`);
    closeOnMobile();          // NEW
  };

  const handleProjectFilesNavigation = (project) => {
    navigate(`/projects/${project.id}/files`);
    closeOnMobile();          // NEW
  };

  const formatTimestamp = (timestamp) => {
    const now = new Date();
    const diff = now - timestamp;
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (hours < 1) return 'Just now';
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return timestamp.toLocaleDateString();
  };

  const isActive = (path) => location.pathname === path;

  // Combine responsive behaviour:
  // • Always visible on ≥lg screens (static).  
  // • Slide-in drawer on sm/md screens controlled via `isOpen`.
  const sidebarContent = (
    <div
      className={`flex flex-col h-full bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 transform transition-transform duration-300 ease-in-out
      lg:translate-x-0 lg:static fixed inset-y-0 left-0 w-64 z-40
      ${isOpen ? 'translate-x-0' : '-translate-x-full'}
      ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <Link to="/" className="flex items-center space-x-2 no-underline">
          <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <span className="text-lg font-bold text-gray-900 dark:text-gray-100">AI Productivity</span>
        </Link>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => {
              setIsPinned(prev => {
                const next = !prev;
                // persist preference – requires tiny helper already available in the store
                useAuthStore.getState().setPreference?.('sidebarPinned', next);
                return next;
              });
            }}
            className="p-1.5 rounded-md text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            title={isPinned ? 'Unpin sidebar' : 'Pin sidebar'}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {isPinned ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
              )}
            </svg>
          </button>

          <button
            onClick={onToggle}
            className="lg:hidden p-1.5 rounded-md text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            title="Close sidebar"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="p-4 space-y-2">
        <button
          onClick={handleNewChat}
          disabled={projectsLoading}
          className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors duration-200 shadow-sm hover:shadow-md"
        >
          {projectsLoading ? (
            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
          ) : (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
          )}
          <span>New Chat</span>
        </button>

        <button
          onClick={handleNewProject}
          disabled={projectsLoading}
          className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed text-gray-700 dark:text-gray-200 rounded-lg font-medium transition-colors duration-200"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          <span>New Project</span>
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 space-y-2 overflow-y-auto scrollbar-thin">
        {/* Main Navigation */}
        <div className="space-y-1">
          <Link
            to="/"
            onClick={closeOnMobile}
            className={`flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-200 ${
              isActive('/')
                ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-700'
                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
            }`}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5a2 2 0 012-2h4a2 2 0 012 2v0M8 5a2 2 0 00-2 2v0h12a2 2 0 00-2-2v0" />
            </svg>
            <span>Dashboard</span>
          </Link>

          <Link
            to="/search"
            onClick={closeOnMobile}
            className={`flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-200 ${
              isActive('/search')
                ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-700'
                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
            }`}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <span>Search</span>
          </Link>

          <Link
            to="/models"
            onClick={closeOnMobile}
            className={`flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-200 ${
              location.pathname.startsWith('/models')
                ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-700'
                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
            }`}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M12 20a8 8 0 100-16 8 8 0 000 16z" />
            </svg>
            <span>Models</span>
          </Link>

          <Link
            to="/timeline"
            onClick={closeOnMobile}
            className={`flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-200 ${
              isActive('/timeline')
                ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-700'
                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
            }`}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>Timeline</span>
          </Link>
        </div>

        {/* Recent Chats */}
        <div className="pt-4">
          <button
            onClick={() => toggleSection('recent')}
            className="flex items-center justify-between w-full px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <span>Recent Chats</span>
            <svg
              className={`w-4 h-4 transition-transform duration-200 ${collapsedSections.recent ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {!collapsedSections.recent && (
            <div className="mt-2 space-y-1">
              {loadingRecentChats && (
                <div className="px-3 py-4 text-sm text-gray-500 dark:text-gray-400 text-center">
                  <div className="w-4 h-4 border border-gray-300 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                  Loading recent chats...
                </div>
              )}

              {recentChatsError && (
                <div className="px-3 py-2 text-sm text-red-500 dark:text-red-400 text-center">
                  {recentChatsError}
                </div>
              )}

              {!loadingRecentChats && !recentChatsError && recentChats.map((chat) => {
                const chatUrl = chat.projectId
                  ? `/projects/${chat.projectId}/chat/${chat.id}`
                  : `/chat/${chat.id}`;

                return (
                  <Link
                    key={chat.id}
                    to={chatUrl}
                    className="w-full flex items-center justify-between px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors group"
                  >
                    <div className="flex items-center space-x-2 min-w-0 flex-1">
                      <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                      </svg>
                      <span className="truncate">{chat.title}</span>
                    </div>
                    <span className="text-xs text-gray-400 ml-2 flex-shrink-0">
                      {formatTimestamp(chat.timestamp)}
                    </span>
                  </Link>
                );
              })}

              {!loadingRecentChats && !recentChatsError && recentChats.length === 0 && (
                <div className="px-3 py-4 text-sm text-gray-500 dark:text-gray-400 text-center">
                  No recent chats
                </div>
              )}
            </div>
          )}
        </div>

        {/* Starred Items */}
        <div className="pt-2">
          <button
            onClick={() => toggleSection('starred')}
            className="flex items-center justify-between w-full px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <span>Starred</span>
            <svg
              className={`w-4 h-4 transition-transform duration-200 ${collapsedSections.starred ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {!collapsedSections.starred && (
            <div className="mt-2 space-y-1">
              {starredItems.map((item) => (
                <Link
                  key={item.id}
                  to={item.url}
                  className="flex items-center space-x-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                >
                  <svg className="w-4 h-4 text-yellow-500" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.196-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                  </svg>
                  <span className="truncate">{item.title}</span>
                  <span className="text-xs text-gray-400 uppercase">{item.type}</span>
                </Link>
              ))}

              {starredItems.length === 0 && (
                <div className="px-3 py-4 text-sm text-gray-500 dark:text-gray-400 text-center">
                  No starred items
                </div>
              )}
            </div>
          )}
        </div>

        {/* Projects */}
        <div className="pt-2">
          <button
            onClick={() => toggleSection('projects')}
            className="flex items-center justify-between w-full px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <span>Projects</span>
            <div className="flex items-center space-x-2">
              <span className="text-xs bg-gray-200 dark:bg-gray-700 px-2 py-0.5 rounded-full">
                {projects.length}
              </span>
              <svg
                className={`w-4 h-4 transition-transform duration-200 ${collapsedSections.projects ? 'rotate-180' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </button>

          {!collapsedSections.projects && (
            <div className="mt-2 space-y-1">
              <Link
                to="/projects"
                onClick={closeOnMobile}
                className={`flex items-center space-x-2 px-3 py-2 text-sm rounded-lg transition-colors ${
                  isActive('/projects')
                    ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                }`}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
                <span>All Projects</span>
                {projectsLoading && (
                  <div className="w-3 h-3 border border-gray-400 border-t-transparent rounded-full animate-spin ml-auto"></div>
                )}
              </Link>

              {projects.slice(0, 5).map((project) => (
                <button
                  key={project.id}
                  onClick={() => { handleProjectChatNavigation(project); }}
                  className="w-full flex items-center space-x-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors group"
                  disabled={projectsLoading}
                >
                  <div 
                    className="color-dot" 
                    style={{ '--dot-color': project.color || '#6B7280' }}
                  ></div>
                  <span className="truncate">{project.title}</span>
                  {project.status === 'active' && (
                    <div className="w-2 h-2 bg-green-400 rounded-full ml-auto"></div>
                  )}
                  {projectsLoading && (
                    <div className="w-3 h-3 border border-gray-300 border-t-transparent rounded-full animate-spin ml-auto"></div>
                  )}
                </button>
              ))}

              {projectsLoading && projects.length === 0 && (
                <div className="px-3 py-4 text-sm text-gray-500 dark:text-gray-400 text-center">
                  <div className="w-4 h-4 border border-gray-300 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                  Loading projects...
                </div>
              )}

              {!projectsLoading && projects.length === 0 && (
                <div className="px-3 py-4 text-sm text-gray-500 dark:text-gray-400 text-center">
                  No projects yet
                </div>
              )}

              {projects.length > 5 && (
                <Link
                  to="/projects"
                  className="flex items-center justify-center px-3 py-2 text-sm text-blue-600 dark:text-blue-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                >
                  View all {projects.length} projects
                </Link>
              )}
            </div>
          )}
        </div>

        {/* Help */}
        <div className="pt-2">
          <button
            onClick={() => toggleSection('help')}
            className="flex items-center justify-between w-full px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <span>Help</span>
            <svg
              className={`w-4 h-4 transition-transform duration-200 ${collapsedSections.help ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {!collapsedSections.help && (
            <ul className="mt-2 space-y-1">
            <li>
              <button onClick={() => setDocumentationModalOpen(true)} className="w-full text-left flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors duration-200">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>
                <span>Documentation</span>
              </button>
            </li>
            <li>
              <button onClick={() => setKeyboardShortcutsModalOpen(true)} className="w-full text-left flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors duration-200">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>
                <span>Keyboard Shortcuts</span>
              </button>
            </li>
          </ul>
          )}
        </div>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700 space-y-3">
        {/* Theme Toggle */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-600 dark:text-gray-400">Theme</span>
          <ThemeToggle />
        </div>

        {/* What's New */}
        <button
          onClick={() => setWhatsNewModalOpen(true)}
          className="w-full flex items-center space-x-2 px-3 py-2 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          <span>What's New</span>
        </button>

        {/* Settings Link */}
        <Link
          to="/settings"
          className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm transition-colors ${
            isActive('/settings')
              ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
              : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
          }`}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          </svg>
          <span>Settings</span>
        </Link>

        {/* User Info */}
        {user && (
          <div className="flex items-center space-x-2 px-3 py-2 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center text-white text-xs font-medium">
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
  );

  return (
    <>
      {/*
        Ensure the sidebar itself never collapses inside flex layouts by
        explicitly preventing flex-box shrinking. Without this, some browsers
        may reduce the calculated width to 0 and the sidebar appears missing
        even though it is rendered.  The `flex-shrink-0` utility keeps the
        allotted width (e.g. `w-64` / `lg:w-72`) intact across all breakpoints.
      */}
      <div className={`flex-shrink-0 ${className}`.trim()}>
        {sidebarContent}
      </div>
      <KeyboardShortcutsModal isOpen={isKeyboardShortcutsModalOpen} onClose={() => setKeyboardShortcutsModalOpen(false)} />
      <WhatsNewModal isOpen={isWhatsNewModalOpen} onClose={() => setWhatsNewModalOpen(false)} />
      <DocumentationModal isOpen={isDocumentationModalOpen} onClose={() => setDocumentationModalOpen(false)} />
    </>
  );
};

// PropTypes validation
// Prop Types & Defaults
Sidebar.defaultProps = {
  onToggle: () => {},
  className: '',
};

Sidebar.propTypes = {
  onToggle: PropTypes.func,
  className: PropTypes.string,
  isOpen: PropTypes.bool,          // NEW
};


export default Sidebar;
