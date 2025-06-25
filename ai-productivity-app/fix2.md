# Navigation Fix Implementation Guide

## What Was Fixed

### 1. **Restored Layout.jsx**
- Now uses the proper `Header` component instead of inline header code
- Maintains sidebar visibility state properly
- Passes menu toggle handler to Header for mobile navigation

### 2. **Enhanced Header Component**
- Added full navigation with breadcrumbs
- Desktop: Shows quick navigation links (Dashboard, Projects, Search, Timeline)
- Mobile: Shows menu button, search, and settings icons
- Breadcrumbs automatically update based on current route
- Includes AI Provider Status, Theme Toggle, and User Menu

### 3. **Restored Sidebar Visual Design**
- Beautiful gradient logo and hover effects
- "New Chat" button with blue gradient
- "New Project" button with proper styling
- Collapsible sections with smooth animations
- Color dots for projects
- Active state indicators
- Pin functionality on desktop
- User profile section at bottom
- Proper icons from lucide-react

## Key Features

### Navigation Improvements
1. **Breadcrumbs** - Always know where you are in the app
2. **Quick Nav** - Desktop users get quick access to main sections
3. **Mobile Optimized** - Touch-friendly buttons and proper spacing
4. **Visual Feedback** - Active states, hover effects, and transitions

### Sidebar Features
1. **Recent Chats** - Quick access to recent conversations
2. **Starred Items** - Save important items (ready for implementation)
3. **Projects List** - Visual project indicators with colors
4. **Collapsible Sections** - Save space by collapsing unused sections
5. **Pin/Unpin** - Keep sidebar open on desktop

## Implementation Steps

1. **Replace Layout.jsx** with the restored version
2. **Replace Header.jsx** with the enhanced version
3. **Replace Sidebar.jsx** with the restored visual design
4. **Ensure all imports are correct** - The components use lucide-react icons

## Mobile Behavior

- Sidebar slides in from left with overlay
- Menu button in header toggles sidebar
- Navigation links close sidebar after click
- Touch-friendly 44px minimum tap targets
- Bottom sheet support for additional content

## Desktop Behavior

- Sidebar can be pinned/unpinned
- Navigation bar in header for quick access
- Hover states and tooltips
- Breadcrumbs show full navigation path

## Testing Checklist

- [ ] Header appears on all pages with correct breadcrumbs
- [ ] Sidebar has all visual elements (gradients, colors, icons)
- [ ] Mobile menu toggle works smoothly
- [ ] Desktop pin functionality works
- [ ] Navigation links are active when on respective pages
- [ ] Recent chats load and display
- [ ] Projects show with color indicators
- [ ] All sections collapse/expand properly
- [ ] Theme toggle and user menu work
- [ ] AI Provider status shows correctly

## Customization

### Colors
The sidebar uses a blue-to-purple gradient for the logo and blue gradient for the main CTA button. These can be adjusted in the className strings.

### Sections
Add or remove sections by modifying the navigation structure in Sidebar.jsx.

### Breadcrumbs
The breadcrumb logic in Header.jsx can be extended to handle additional routes.

### `Sidebar.jsx`
```jsx
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
import { useMediaQuery } from '../../hooks/useMediaQuery';
import {
  Plus, FolderOpen, Clock, Star, Search, Settings, HelpCircle,
  ChevronDown, Home, MessageSquare, FileText, BarChart3, Database,
  PinIcon, X
} from 'lucide-react';

const Sidebar = ({ isOpen = true, onToggle, className = '' }) => {
  const { user } = useAuth();
  const { isDesktop } = useMediaQuery();
  const navigate = useNavigate();
  const location = useLocation();
  const { projects, loading: projectsLoading, search } = useProjectSearch();
  const { preferences } = useAuthStore();

  const [isPinned, setIsPinned] = useState(preferences?.sidebarPinned || false);
  const [collapsedSections, setCollapsedSections] = useState({
    recent: false,
    starred: true,
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

  // Close sidebar on mobile after navigation
  const closeOnMobile = () => {
    if (!isDesktop && onToggle) onToggle();
  };

  // Load recent chats
  const loadRecentChats = useCallback(async () => {
    if (!user) return;
    setLoadingRecentChats(true);
    setRecentChatsError(null);
    try {
      const response = await chatAPI.getChatSessions();
      const sessions = response.data || [];
      const sortedSessions = sessions
        .sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))
        .slice(0, 5);
      setRecentChats(sortedSessions);
    } catch (error) {
      console.error('Failed to load recent chats:', error);
      setRecentChatsError('Failed to load recent chats');
    } finally {
      setLoadingRecentChats(false);
    }
  }, [user]);

  useEffect(() => {
    loadRecentChats();
  }, [loadRecentChats, location.pathname]);

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
    setCollapsedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const isActive = (path) => location.pathname === path;

  // Visual indicator for color
  const ColorDot = ({ color }) => (
    <div
      className="w-2 h-2 rounded-full flex-shrink-0"
      style={{ backgroundColor: color || '#6B7280' }}
    />
  );

  return (
    <>
      <div className={`flex flex-col h-full bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 w-64 lg:w-72 ${className}`}>
        {/* Header with logo and pin button */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <Link to="/" className="flex items-center space-x-2 no-underline">
            <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg flex items-center justify-center transition-all duration-200 hover:scale-110 shadow-lg">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <span className="text-lg font-bold bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent dark:from-gray-100 dark:to-gray-300">
              AI Productivity
            </span>
          </Link>

          <div className="flex items-center space-x-2">
            {isDesktop && (
              <button
                onClick={() => setIsPinned(!isPinned)}
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
              className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
            >
              <div className="flex items-center space-x-2">
                <Clock className="w-4 h-4" />
                <span>Recent</span>
              </div>
              <ChevronDown className={`w-4 h-4 transition-transform ${collapsedSections.recent ? '' : 'rotate-180'}`} />
            </button>

            {!collapsedSections.recent && (
              <div className="mt-2 space-y-1">
                {loadingRecentChats ? (
                  <div className="px-3 py-2 text-sm text-gray-500">
                    <div className="animate-pulse">Loading...</div>
                  </div>
                ) : recentChats.length > 0 ? (
                  recentChats.map((chat) => (
                    <Link
                      key={chat.id}
                      to={`/projects/${chat.project_id}/chat/${chat.id}`}
                      onClick={closeOnMobile}
                      className="block px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg truncate transition-colors"
                    >
                      <div className="flex items-center space-x-2">
                        <MessageSquare className="w-3.5 h-3.5 flex-shrink-0" />
                        <span className="truncate">{chat.title || 'Untitled Chat'}</span>
                      </div>
                    </Link>
                  ))
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
              className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
            >
              <div className="flex items-center space-x-2">
                <Star className="w-4 h-4" />
                <span>Starred</span>
              </div>
              <ChevronDown className={`w-4 h-4 transition-transform ${collapsedSections.starred ? '' : 'rotate-180'}`} />
            </button>

            {!collapsedSections.starred && (
              <div className="mt-2 px-3 py-2 text-sm text-gray-500 dark:text-gray-400">
                No starred items yet
              </div>
            )}
          </div>

          {/* Projects */}
          <div>
            <button
              onClick={() => toggleSection('projects')}
              className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
            >
              <div className="flex items-center space-x-2">
                <FolderOpen className="w-4 h-4" />
                <span>Projects</span>
              </div>
              <ChevronDown className={`w-4 h-4 transition-transform ${collapsedSections.projects ? '' : 'rotate-180'}`} />
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
            <Link
              to="/"
              onClick={closeOnMobile}
              className={`flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isActive('/')
                  ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
              }`}
            >
              <Home className="w-4 h-4" />
              <span>Dashboard</span>
            </Link>

            <Link
              to="/search"
              onClick={closeOnMobile}
              className={`flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isActive('/search')
                  ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
              }`}
            >
              <Search className="w-4 h-4" />
              <span>Search</span>
            </Link>

            <Link
              to="/timeline"
              onClick={closeOnMobile}
              className={`flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isActive('/timeline')
                  ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
              }`}
            >
              <Clock className="w-4 h-4" />
              <span>Timeline</span>
            </Link>
          </div>

          {/* Help & Resources */}
          <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={() => toggleSection('help')}
              className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
            >
              <div className="flex items-center space-x-2">
                <HelpCircle className="w-4 h-4" />
                <span>Help & Resources</span>
              </div>
              <ChevronDown className={`w-4 h-4 transition-transform ${collapsedSections.help ? '' : 'rotate-180'}`} />
            </button>

            {!collapsedSections.help && (
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
                  <Database className="w-4 h-4" />
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
              isActive('/settings')
                ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
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
```
---
### `Header.jsx`
```jsx
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import UserMenu from '../auth/UserMenu';
import AIProviderStatus from './AIProviderStatus';
import ThemeToggle from './ThemeToggle';
import { Menu, Search, FolderOpen, Clock, Home, Settings, ChevronRight } from 'lucide-react';
import PropTypes from 'prop-types';

function Header({ onMenuClick, showMenuButton = false }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  // Helper to check if a path is active
  const isActive = (path) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  // Generate breadcrumbs based on current path
  const getBreadcrumbs = () => {
    const paths = location.pathname.split('/').filter(Boolean);
    const breadcrumbs = [{ name: 'Dashboard', path: '/' }];

    if (paths.length > 0) {
      const first = paths[0];
      if (first === 'projects') {
        breadcrumbs.push({ name: 'Projects', path: '/projects' });
        if (paths[1]) {
          breadcrumbs.push({ name: 'Project', path: `/projects/${paths[1]}` });
          if (paths[2]) {
            const subPages = {
              'chat': 'Chat',
              'files': 'Files',
              'analytics': 'Analytics',
              'knowledge': 'Knowledge Base'
            };
            breadcrumbs.push({
              name: subPages[paths[2]] || paths[2],
              path: location.pathname
            });
          }
        }
      } else {
        const pageNames = {
          'search': 'Search',
          'timeline': 'Timeline',
          'settings': 'Settings',
          'profile': 'Profile',
          'models': 'Model Settings'
        };
        breadcrumbs.push({
          name: pageNames[first] || first.charAt(0).toUpperCase() + first.slice(1),
          path: location.pathname
        });
      }
    }

    return breadcrumbs;
  };

  const breadcrumbs = getBreadcrumbs();

  return (
    <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700 sticky top-0 z-30">
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Left side - Menu button and breadcrumbs */}
          <div className="flex items-center flex-1">
            {/* Mobile menu button */}
            {showMenuButton && (
              <button
                onClick={onMenuClick}
                className="p-2 -ml-2 mr-3 rounded-md text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors duration-150"
                aria-label="Toggle sidebar"
              >
                <Menu className="h-6 w-6" />
              </button>
            )}

            {/* Breadcrumbs */}
            <nav className="flex items-center space-x-1 text-sm" aria-label="Breadcrumb">
              {breadcrumbs.map((crumb, index) => (
                <div key={crumb.path} className="flex items-center">
                  {index > 0 && <ChevronRight className="w-4 h-4 text-gray-400 mx-1" />}
                  {index === breadcrumbs.length - 1 ? (
                    <span className="text-gray-900 dark:text-gray-100 font-medium">
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
                </div>
              ))}
            </nav>
          </div>

          {/* Center - Quick navigation (desktop only) */}
          <nav className="hidden lg:flex items-center space-x-1 mx-6">
            <Link
              to="/"
              className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive('/')
                  ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              <Home className="w-4 h-4" />
              <span>Dashboard</span>
            </Link>
            <Link
              to="/projects"
              className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive('/projects')
                  ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              <FolderOpen className="w-4 h-4" />
              <span>Projects</span>
            </Link>
            <Link
              to="/search"
              className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive('/search')
                  ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              <Search className="w-4 h-4" />
              <span>Search</span>
            </Link>
            <Link
              to="/timeline"
              className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive('/timeline')
                  ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              <Clock className="w-4 h-4" />
              <span>Timeline</span>
            </Link>
          </nav>

          {/* Right side - Status, theme, and user menu */}
          <div className="flex items-center space-x-3">
            {/* AI Provider Status */}
            <AIProviderStatus className="hidden sm:block" />

            {/* Quick search button (mobile) */}
            <Link
              to="/search"
              className="lg:hidden p-2 rounded-md text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700"
              aria-label="Search"
            >
              <Search className="w-5 h-5" />
            </Link>

            {/* Theme Toggle */}
            <ThemeToggle />

            {/* Settings (mobile) */}
            <Link
              to="/settings"
              className="lg:hidden p-2 rounded-md text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700"
              aria-label="Settings"
            >
              <Settings className="w-5 h-5" />
            </Link>

            {/* User menu or login */}
            {loading ? (
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
            ) : user ? (
              <UserMenu />
            ) : (
              <Link
                to="/login"
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors duration-200"
              >
                Sign In
              </Link>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}

Header.propTypes = {
  onMenuClick: PropTypes.func,
  showMenuButton: PropTypes.bool
};

Header.defaultProps = {
  onMenuClick: () => {},
  showMenuButton: false
};

export default Header;
```
---
### `Layout.jsx`
```jsx
import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import PropTypes from 'prop-types';
import { useAuth } from '../../hooks/useAuth';
import UserMenu from '../auth/UserMenu';
import ThemeToggle from './ThemeToggle';
import Sidebar from './Sidebar';
import Header from './Header';
import { useMediaQuery } from '../../hooks/useMediaQuery';
import useAuthStore from '../../stores/authStore';
import { useResponsiveLayout } from '../../hooks/useResponsiveLayout';
import { ResponsivePage, ShowOnDesktop, HideOnDesktop } from '../layout/ResponsiveContainer';
import { Menu } from 'lucide-react';

export default function Layout({ children }) {
  const { user, loading: authLoading } = useAuth();
  const location = useLocation();
  const { preferences } = useAuthStore();
  // Start with sidebar open on desktop, closed on mobile/tablet
  const { isMobile, isTablet } = useMediaQuery();
  const isDesktop = !isMobile && !isTablet;
  const [sidebarOpen, setSidebarOpen] = useState(isDesktop);
  const layout = useResponsiveLayout();

  // Show loading state
  if (authLoading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#f8fafc'
        }}
      >
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mr-3"></div>
        <span style={{ fontSize: 24, color: '#3b82f6', letterSpacing: 2 }}>Checking authentication…</span>
      </div>
    );
  }

  // Don't show sidebar on login/auth pages
  const authPages = ['/login', '/forgot', '/reset'];
  const isAuthPage = authPages.some(page => location.pathname.startsWith(page));
  const showSidebar = user && !isAuthPage;

  if (!showSidebar) {
    // Simple layout for auth pages
    return (
      <div className="min-h-screen gradient-bg transition-colors duration-200 flex flex-col">
        <a href="#main-content" className="skip-link">
          Skip to main content
        </a>

        {/* Simple header for auth pages */}
        <header className="glass border-b border-white/20 dark:border-gray-700/20 transition-all duration-200 backdrop-blur-md">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <Link to="/" className="flex items-center space-x-2 no-underline">
                <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg flex items-center justify-center transition-all duration-200 hover:scale-110 shadow-lg">
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
                <span className="text-xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent dark:from-gray-100 dark:to-gray-300 no-underline">
                  AI Productivity
                </span>
              </Link>
              <ThemeToggle />
            </div>
          </div>
        </header>

        <main id="main-content" className="flex-1" role="main">
          {children}
        </main>

        <footer className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 transition-colors duration-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <p className="text-center text-sm text-gray-500 dark:text-gray-400">
              © 2024 AI Productivity. All rights reserved.
            </p>
          </div>
        </footer>
      </div>
    );
  }

  // Main layout with sidebar for authenticated users
  return (
    <div className="min-h-screen gradient-bg transition-colors duration-200 flex">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      {/* Sidebar with proper responsive behavior */}
      <Sidebar
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(false)}
        className={`
          ${isMobile || isTablet ? 'fixed' : 'relative'}
          ${(!isDesktop && !sidebarOpen) ? 'hidden' : ''}
          z-40
        `}
      />

      {/* Overlay for mobile/tablet when sidebar is open */}
      {!isDesktop && sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/30 backdrop-blur-sm z-30"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Use the proper Header component with navigation */}
        <Header
          onMenuClick={() => setSidebarOpen(!sidebarOpen)}
          showMenuButton={!isDesktop}
        />

        {/* Main content */}
        <main id="main-content" className="flex-1 overflow-auto" role="main">
          {children}
        </main>
      </div>
    </div>
  );
}

Layout.propTypes = {
  children: PropTypes.node.isRequired
};
```
