export const NAVIGATION_STYLES = {
  active: {
    default: 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300',
    sidebar: 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300',
    tab: 'border-b-2 border-blue-600 text-blue-600 dark:text-blue-400',
    button: 'bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-400'
  },
  inactive: {
    default: 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700',
    sidebar: 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800',
    tab: 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200',
    button: 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
  }
};

export const BREAKPOINTS = {
  mobile: 640,
  tablet: 768,
  desktop: 1024,
  wide: 1280
};

export const PANEL_DEFAULTS = {
  sidebar: { default: 20, min: 14, max: 35 },
  knowledge: { default: 30, min: 20, max: 40 },
  editor: { default: 35, min: 20, max: 50 }
};