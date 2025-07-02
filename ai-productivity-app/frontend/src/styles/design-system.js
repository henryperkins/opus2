/**
 * Design System Constants
 * Centralized styling constants to eliminate duplication and ensure consistency
 */

// Color Palette
export const colors = {
  primary: {
    50: '#eff6ff',
    100: '#dbeafe', 
    200: '#bfdbfe',
    300: '#93c5fd',
    400: '#60a5fa',
    500: '#3b82f6', // Main brand blue
    600: '#2563eb',
    700: '#1d4ed8',
    800: '#1e40af',
    900: '#1e3a8a',
  },
  gray: {
    50: '#f9fafb',
    100: '#f3f4f6',
    200: '#e5e7eb',
    300: '#d1d5db',
    400: '#9ca3af',
    500: '#6b7280',
    600: '#4b5563',
    700: '#374151',
    800: '#1f2937',
    900: '#111827',
  },
  success: {
    50: '#ecfdf5',
    100: '#d1fae5',
    500: '#10b981',
    600: '#059669',
    700: '#047857',
  },
  warning: {
    50: '#fffbeb',
    100: '#fef3c7',
    500: '#f59e0b',
    600: '#d97706',
    700: '#b45309',
  },
  error: {
    50: '#fef2f2',
    100: '#fee2e2',
    500: '#ef4444',
    600: '#dc2626',
    700: '#b91c1c',
  }
};

// Button Styles
export const buttonStyles = {
  primary: `bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed`,
  secondary: `bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 px-4 py-2 rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 disabled:opacity-50`,
  ghost: `text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 px-3 py-2 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2`,
  danger: `bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50`,
};

// Common Hover States
export const hoverStyles = {
  grayLight: 'hover:bg-gray-50 dark:hover:bg-gray-800',
  grayMedium: 'hover:bg-gray-100 dark:hover:bg-gray-700', 
  grayDark: 'hover:bg-gray-200 dark:hover:bg-gray-600',
  blue: 'hover:bg-blue-50 dark:hover:bg-blue-900/20',
  interactive: 'hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors cursor-pointer',
};

// Active/Selected States
export const activeStyles = {
  primary: 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300',
  sidebar: 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300',
  nav: 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300',
};

// Input Styles
export const inputStyles = {
  base: `w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors`,
  error: `border-red-500 focus:ring-red-500`,
  success: `border-green-500 focus:ring-green-500`,
};

// Card/Container Styles
export const cardStyles = {
  base: `bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm`,
  interactive: `bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm hover:shadow-md transition-shadow cursor-pointer`,
  elevated: `bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-md`,
};

// Modal Styles
export const modalStyles = {
  overlay: `fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50`,
  container: `bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto`,
  header: `flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700`,
  body: `p-6`,
  footer: `flex justify-end space-x-3 p-6 border-t border-gray-200 dark:border-gray-700`,
};

// Spacing
export const spacing = {
  xs: '0.25rem',   // 4px
  sm: '0.5rem',    // 8px
  md: '1rem',      // 16px
  lg: '1.5rem',    // 24px
  xl: '2rem',      // 32px
  '2xl': '3rem',   // 48px
  '3xl': '4rem',   // 64px
};

// Breakpoints
export const breakpoints = {
  sm: '640px',
  md: '768px', 
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
};

// Animation
export const animations = {
  transition: 'transition-all duration-200 ease-in-out',
  fadeIn: 'animate-fade-in',
  slideIn: 'animate-slide-in',
  bounce: 'animate-bounce',
  pulse: 'animate-pulse',
};

// Project specific constants
export const projectConstants = {
  defaultColors: [
    '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
    '#EC4899', '#06B6D4', '#84CC16', '#F97316', '#6B7280'
  ],
  defaultEmojis: [
    '🚀', '💼', '🎯', '⭐', '🔥', '💡', '🎨', '📊', '🛠️',
    '🌟', '📈', '🎪', '🎭', '🎵', '🏆', '🎸', '🎮', '🌈', '⚡'
  ],
};

export default {
  colors,
  buttonStyles,
  hoverStyles,
  activeStyles,
  inputStyles,
  cardStyles,
  modalStyles,
  spacing,
  breakpoints,
  animations,
  projectConstants,
};
