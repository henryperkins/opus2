import { Home, FolderOpen, Search, Clock, Settings, BarChart3, Bot } from 'lucide-react';

export const navigationRoutes = [
  {
    id: 'dashboard',
    path: '/',
    label: 'Dashboard',
    icon: Home,
    showInSidebar: true,
    breadcrumbLabel: 'Dashboard'
  },
  {
    id: 'projects',
    path: '/projects',
    label: 'Projects',
    icon: FolderOpen,
    showInSidebar: true,
    breadcrumbLabel: 'Projects'
  },
  {
    id: 'search',
    path: '/search',
    label: 'Search',
    icon: Search,
    showInSidebar: true,
    showMobileQuickAction: true,
    breadcrumbLabel: 'Search'
  },
  {
    id: 'timeline',
    path: '/timeline',
    label: 'Timeline',
    icon: Clock,
    showInSidebar: true,
    breadcrumbLabel: 'Timeline'
  },
  {
    id: 'settings',
    path: '/settings',
    label: 'Settings',
    icon: Settings,
    showInSidebar: true,
    showMobileQuickAction: true,
    breadcrumbLabel: 'Settings'
  },
  {
    id: 'models',
    path: '/models',
    label: 'Model Settings',
    icon: Bot,
    showInSidebar: true,
    breadcrumbLabel: 'Model Settings'
  }
];

export const projectSubRoutes = {
  'chat': { label: 'Chat', breadcrumbLabel: 'Chat' },
  'files': { label: 'Files', breadcrumbLabel: 'Files' },
  'analytics': { label: 'Analytics', breadcrumbLabel: 'Analytics' },
  'knowledge': { label: 'Knowledge Base', breadcrumbLabel: 'Knowledge Base' }
};

export const pageRoutes = {
  'search': 'Search',
  'timeline': 'Timeline', 
  'settings': 'Settings',
  'profile': 'Profile',
  'models': 'Model Settings'
};

export default {
  navigationRoutes,
  projectSubRoutes,
  pageRoutes
};