/* Enhanced Tailwind CSS configuration with theming support.
 *
 * NOTE: The original config has been replaced as part of the Phase-9 UI
 * revamp.  The new design tokens and utilities rely on additional
 * Tailwind plugins (forms & typography).  To keep the repo functional even
 * when those plugins are not installed locally, we attempt to `require` them
 * and gracefully fall back to a no-op plugin when they are missing.  This
 * avoids breaking CI/test pipelines that do not have the extra packages.
 */

import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);

// Attempt to load optional plugins ------------------------------------------------
function loadPlugin(pkg) {
  try {
    return require(pkg);
  } catch {
    return () => ({ name: `noop-${pkg}` });
  }
}

const formsPlugin = loadPlugin('@tailwindcss/forms');
const typographyPlugin = loadPlugin('@tailwindcss/typography');

// ---------------------------------------------------------------------------------

export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Brand colours
      'brand-primary': {
        50: '#eff6ff',
        100: '#dbeafe',
        200: '#bfdbfe',
        300: '#93c5fd',
        400: '#60a5fa',
        500: '#3b82f6',
        600: '#2563eb',
        700: '#1d4ed8',
        800: '#1e40af',
        900: '#1e3a8a',
      },
      'brand-accent': {
        50: '#f0f9ff',
        100: '#e0f2fe',
        200: '#bae6fd',
        300: '#7dd3fc',
        400: '#38bdf8',
        500: '#0ea5e9',
        600: '#0284c7',
        700: '#0369a1',
        800: '#075985',
        900: '#0c4a6e',
      },

      // Semantic colours
      success: {
        50: '#f0fdf4',
        500: '#10b981',
        600: '#059669',
        700: '#047857',
      },
      warning: {
        50: '#fffbeb',
        500: '#f59e0b',
        600: '#d97706',
        700: '#b45309',
      },
      error: {
        50: '#fef2f2',
        400: '#f87171',
        500: '#ef4444',
        600: '#dc2626',
        700: '#b91c1c',
      },
    },
    fontFamily: {
      sans: [
        'Inter',
        'system-ui',
        '-apple-system',
        'BlinkMacSystemFont',
        'Segoe UI',
        'Roboto',
        'sans-serif',
      ],
      mono: [
        'JetBrains Mono',
        'Menlo',
        'Monaco',
        'Consolas',
        'monospace',
      ],
    },
    fontSize: {
      xs: ['0.75rem', { lineHeight: '1rem' }],
      sm: ['0.875rem', { lineHeight: '1.25rem' }],
      base: ['1rem', { lineHeight: '1.5rem' }],
      lg: ['1.125rem', { lineHeight: '1.75rem' }],
      xl: ['1.25rem', { lineHeight: '1.75rem' }],
      '2xl': ['1.5rem', { lineHeight: '2rem' }],
      '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
      '4xl': ['2.25rem', { lineHeight: '2.5rem' }],
      '5xl': ['3rem', { lineHeight: '1' }],
      '6xl': ['3.75rem', { lineHeight: '1' }],
      '7xl': ['4.5rem', { lineHeight: '1' }],
      '8xl': ['6rem', { lineHeight: '1' }],
      '9xl': ['8rem', { lineHeight: '1' }],
    },
    fontWeight: {
      thin: '100',
      extralight: '200',
      light: '300',
      normal: '400',
      medium: '500',
      semibold: '600',
      bold: '700',
      extrabold: '800',
      black: '900',
    },
      },
    },
  plugins: [
    formsPlugin,
    typographyPlugin,
  ],
};
