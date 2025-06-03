I'll implement Phase 9 with comprehensive UI polish, accessibility, responsiveness, theming, and performance optimizations. Let me provide all the required artifacts.

# frontend/tailwind.config.js – Enhanced Tailwind config with theming and design tokens

```javascript
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}"
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Brand colors
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
        // Semantic colors
        'success': {
          50: '#f0fdf4',
          500: '#10b981',
          600: '#059669',
          700: '#047857',
        },
        'warning': {
          50: '#fffbeb',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
        },
        'error': {
          50: '#fef2f2',
          500: '#ef4444',
          600: '#dc2626',
          700: '#b91c1c',
        },
      },
      fontFamily: {
        'sans': ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        'mono': ['JetBrains Mono', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      fontSize: {
        'xs': ['0.75rem', { lineHeight: '1rem' }],
        'sm': ['0.875rem', { lineHeight: '1.25rem' }],
        'base': ['1rem', { lineHeight: '1.5rem' }],
        'lg': ['1.125rem', { lineHeight: '1.75rem' }],
        'xl': ['1.25rem', { lineHeight: '1.75rem' }],
        '2xl': ['1.5rem', { lineHeight: '2rem' }],
        '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
        '4xl': ['2.25rem', { lineHeight: '2.5rem' }],
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem',
      },
      animation: {
        'fade-in': 'fadeIn 200ms ease-in',
        'fade-out': 'fadeOut 200ms ease-out',
        'slide-in': 'slideIn 300ms ease-out',
        'slide-out': 'slideOut 300ms ease-in',
        'scale-in': 'scaleIn 200ms ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeOut: {
          '0%': { opacity: '1' },
          '100%': { opacity: '0' },
        },
        slideIn: {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideOut: {
          '0%': { transform: 'translateY(0)', opacity: '1' },
          '100%': { transform: 'translateY(-10px)', opacity: '0' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
      },
      screens: {
        'xs': '375px',
        'sm': '640px',
        'md': '768px',
        'lg': '1024px',
        'xl': '1280px',
        '2xl': '1536px',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
}
```

# frontend/src/styles/globals.css – Enhanced global styles with dark mode and accessibility

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

@tailwind base;
@tailwind components;
@tailwind utilities;

/* Base styles and resets */
@layer base {
  :root {
    --color-bg-primary: 255 255 255;
    --color-bg-secondary: 249 250 251;
    --color-text-primary: 17 24 39;
    --color-text-secondary: 107 114 128;
    --color-border: 229 231 235;
    --focus-ring-color: 59 130 246;
  }

  .dark {
    --color-bg-primary: 17 24 39;
    --color-bg-secondary: 31 41 55;
    --color-text-primary: 243 244 246;
    --color-text-secondary: 156 163 175;
    --color-border: 55 65 81;
    --focus-ring-color: 96 165 250;
  }

  * {
    @apply border-border;
  }

  body {
    @apply bg-white text-gray-900 antialiased transition-colors duration-200;
    @apply dark:bg-gray-900 dark:text-gray-100;
  }

  /* Focus styles for accessibility */
  :focus {
    @apply outline-none;
  }

  :focus-visible {
    @apply ring-2 ring-brand-primary-500 ring-offset-2 ring-offset-white;
    @apply dark:ring-offset-gray-900;
  }

  /* Reduced motion preferences */
  @media (prefers-reduced-motion: reduce) {
    * {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
    }
  }

  /* Skip link for accessibility */
  .skip-link {
    @apply absolute left-0 top-0 z-50 -translate-y-full px-4 py-2;
    @apply bg-brand-primary-600 text-white rounded-md;
    @apply focus:translate-y-0 focus:shadow-lg;
    @apply transition-transform duration-200;
  }

  /* Heading hierarchy */
  h1 {
    @apply text-3xl md:text-4xl font-bold tracking-tight;
  }

  h2 {
    @apply text-2xl md:text-3xl font-semibold tracking-tight;
  }

  h3 {
    @apply text-xl md:text-2xl font-semibold;
  }

  h4 {
    @apply text-lg md:text-xl font-medium;
  }

  /* Form elements */
  input:not([type="checkbox"]):not([type="radio"]),
  textarea,
  select {
    @apply w-full px-3 py-2 border rounded-md shadow-sm;
    @apply bg-white dark:bg-gray-800;
    @apply border-gray-300 dark:border-gray-600;
    @apply placeholder-gray-400 dark:placeholder-gray-500;
    @apply focus:ring-2 focus:ring-brand-primary-500 focus:border-transparent;
    @apply disabled:bg-gray-50 disabled:opacity-60 disabled:cursor-not-allowed;
    @apply dark:disabled:bg-gray-900;
  }

  /* Checkbox and radio */
  input[type="checkbox"],
  input[type="radio"] {
    @apply text-brand-primary-600 border-gray-300 rounded;
    @apply focus:ring-2 focus:ring-brand-primary-500;
    @apply dark:border-gray-600 dark:bg-gray-800;
  }

  /* Links */
  a {
    @apply text-brand-primary-600 hover:text-brand-primary-700;
    @apply dark:text-brand-primary-400 dark:hover:text-brand-primary-300;
    @apply underline-offset-2 hover:underline;
    @apply transition-colors duration-150;
  }

  /* Code blocks */
  pre {
    @apply bg-gray-50 dark:bg-gray-800 rounded-lg p-4 overflow-x-auto;
  }

  code {
    @apply bg-gray-100 dark:bg-gray-700 px-1 py-0.5 rounded text-sm;
    @apply font-mono;
  }
}

/* Component styles */
@layer components {
  /* Button variants */
  .btn {
    @apply inline-flex items-center justify-center px-4 py-2 rounded-md;
    @apply font-medium text-sm transition-all duration-150;
    @apply focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2;
    @apply disabled:opacity-60 disabled:cursor-not-allowed;
    @apply min-h-[44px] min-w-[44px]; /* Touch target size */
  }

  .btn-primary {
    @apply bg-brand-primary-600 text-white;
    @apply hover:bg-brand-primary-700 active:bg-brand-primary-800;
    @apply focus-visible:ring-brand-primary-500;
    @apply dark:bg-brand-primary-500 dark:hover:bg-brand-primary-600;
  }

  .btn-secondary {
    @apply bg-white text-gray-700 border border-gray-300;
    @apply hover:bg-gray-50 active:bg-gray-100;
    @apply dark:bg-gray-800 dark:text-gray-200 dark:border-gray-600;
    @apply dark:hover:bg-gray-700;
  }

  .btn-ghost {
    @apply text-gray-600 hover:text-gray-900 hover:bg-gray-100;
    @apply dark:text-gray-400 dark:hover:text-gray-100 dark:hover:bg-gray-800;
  }

  .btn-danger {
    @apply bg-error-600 text-white;
    @apply hover:bg-error-700 active:bg-error-800;
    @apply focus-visible:ring-error-500;
  }

  /* Card styles */
  .card {
    @apply bg-white rounded-lg shadow-sm border border-gray-200;
    @apply dark:bg-gray-800 dark:border-gray-700;
    @apply transition-shadow duration-200;
  }

  .card-hover {
    @apply hover:shadow-md hover:border-gray-300;
    @apply dark:hover:border-gray-600;
  }

  /* Form groups */
  .form-group {
    @apply space-y-1.5;
  }

  .form-label {
    @apply block text-sm font-medium text-gray-700;
    @apply dark:text-gray-300;
  }

  .form-error {
    @apply text-sm text-error-600 dark:text-error-400;
  }

  .form-help {
    @apply text-sm text-gray-500 dark:text-gray-400;
  }

  /* Loading states */
  .skeleton {
    @apply animate-pulse bg-gray-200 dark:bg-gray-700 rounded;
  }

  /* Dropdown menu */
  .dropdown-menu {
    @apply absolute z-50 mt-2 rounded-md shadow-lg;
    @apply bg-white dark:bg-gray-800;
    @apply border border-gray-200 dark:border-gray-700;
    @apply ring-1 ring-black ring-opacity-5;
    @apply animate-fade-in;
  }

  .dropdown-item {
    @apply block w-full px-4 py-2 text-sm text-left;
    @apply text-gray-700 dark:text-gray-200;
    @apply hover:bg-gray-100 dark:hover:bg-gray-700;
    @apply focus:bg-gray-100 dark:focus:bg-gray-700;
    @apply transition-colors duration-150;
  }
}

/* Utility classes */
@layer utilities {
  /* Text truncation */
  .line-clamp-1 {
    @apply overflow-hidden;
    display: -webkit-box;
    -webkit-line-clamp: 1;
    -webkit-box-orient: vertical;
  }

  .line-clamp-2 {
    @apply overflow-hidden;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }

  .line-clamp-3 {
    @apply overflow-hidden;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
  }

  /* Scrollbar styling */
  .scrollbar-thin {
    scrollbar-width: thin;
  }

  .scrollbar-thin::-webkit-scrollbar {
    @apply w-2 h-2;
  }

  .scrollbar-thin::-webkit-scrollbar-track {
    @apply bg-gray-100 dark:bg-gray-800 rounded-full;
  }

  .scrollbar-thin::-webkit-scrollbar-thumb {
    @apply bg-gray-400 dark:bg-gray-600 rounded-full;
    @apply hover:bg-gray-500 dark:hover:bg-gray-500;
  }

  /* Safe area insets for mobile */
  .safe-top {
    padding-top: env(safe-area-inset-top);
  }

  .safe-bottom {
    padding-bottom: env(safe-area-inset-bottom);
  }

  .safe-left {
    padding-left: env(safe-area-inset-left);
  }

  .safe-right {
    padding-right: env(safe-area-inset-right);
  }
}
```

# frontend/src/hooks/useTheme.js – Theme management hook with persistence

```javascript
import { useState, useEffect, useCallback, createContext, useContext } from 'react';

const ThemeContext = createContext({
  theme: 'light',
  setTheme: () => {},
  toggleTheme: () => {},
});

export function useTheme() {
  return useContext(ThemeContext);
}

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(() => {
    // Check localStorage first
    const saved = localStorage.getItem('theme');
    if (saved === 'light' || saved === 'dark') return saved;
    
    // Check system preference
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    return 'light';
  });

  const setTheme = useCallback((newTheme) => {
    if (newTheme !== 'light' && newTheme !== 'dark') return;
    
    setThemeState(newTheme);
    localStorage.setItem('theme', newTheme);
    
    // Update document class
    const root = document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(newTheme);
    
    // Update meta theme-color
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
      meta.content = newTheme === 'dark' ? '#111827' : '#ffffff';
    }
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme(theme === 'light' ? 'dark' : 'light');
  }, [theme, setTheme]);

  // Apply theme on mount and when it changes
  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(theme);
  }, [theme]);

  // Listen for system theme changes
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    
    const handleChange = (e) => {
      const savedTheme = localStorage.getItem('theme');
      if (!savedTheme) {
        setTheme(e.matches ? 'dark' : 'light');
      }
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [setTheme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}
```

# frontend/src/components/common/ThemeToggle.jsx – Dark/Light theme switcher with persistence

```jsx
import React from 'react';
import { useTheme } from '../../hooks/useTheme';

export default function ThemeToggle({ className = '' }) {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className={`p-2 rounded-md transition-colors duration-200 hover:bg-gray-100 dark:hover:bg-gray-800 ${className}`}
      aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
      title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
    >
      {theme === 'light' ? (
        <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
            d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
        </svg>
      ) : (
        <svg className="w-5 h-5 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
            d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
        </svg>
      )}
    </button>
  );
}
```

# frontend/src/components/common/Layout.jsx – Global layout wrapper with skip links and mobile nav

```jsx
import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import UserMenu from '../auth/UserMenu';
import ThemeToggle from './ThemeToggle';

export default function Layout({ children }) {
  const { user } = useAuth();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navigation = [
    { name: 'Dashboard', href: '/', icon: 'home' },
    { name: 'Projects', href: '/projects', icon: 'folder' },
    { name: 'Search', href: '/search', icon: 'search' },
    { name: 'Timeline', href: '/timeline', icon: 'clock' },
  ];

  const isActive = (path) => location.pathname === path;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-200">
      {/* Skip to main content link */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700 transition-colors duration-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo and Desktop Nav */}
            <div className="flex items-center">
              <Link to="/" className="flex items-center space-x-2 no-underline">
                <div className="w-8 h-8 bg-brand-primary-600 dark:bg-brand-primary-500 rounded-lg flex items-center justify-center transition-colors duration-200">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                      d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
                <span className="text-xl font-semibold text-gray-900 dark:text-gray-100 no-underline">
                  AI Productivity
                </span>
              </Link>

              {/* Desktop Navigation */}
              {user && (
                <nav className="hidden md:flex ml-10 space-x-8" role="navigation" aria-label="Main navigation">
                  {navigation.map((item) => (
                    <Link
                      key={item.name}
                      to={item.href}
                      className={`px-3 py-2 rounded-md text-sm font-medium transition-colors duration-150 no-underline ${
                        isActive(item.href)
                          ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
                          : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-700'
                      }`}
                      aria-current={isActive(item.href) ? 'page' : undefined}
                    >
                      {item.name}
                    </Link>
                  ))}
                </nav>
              )}
            </div>

            {/* Right side */}
            <div className="flex items-center space-x-4">
              <ThemeToggle />
              
              {user ? (
                <>
                  <UserMenu />
                  {/* Mobile menu button */}
                  <button
                    onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                    className="md:hidden p-2 rounded-md text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors duration-150"
                    aria-expanded={mobileMenuOpen}
                    aria-label="Toggle navigation menu"
                  >
                    <span className="sr-only">Open main menu</span>
                    {mobileMenuOpen ? (
                      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    ) : (
                      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                      </svg>
                    )}
                  </button>
                </>
              ) : (
                <Link
                  to="/login"
                  className="btn btn-primary text-sm no-underline"
                >
                  Sign In
                </Link>
              )}
            </div>
          </div>
        </div>

        {/* Mobile Navigation */}
        {user && mobileMenuOpen && (
          <nav className="md:hidden border-t border-gray-200 dark:border-gray-700 animate-slide-in">
            <div className="px-2 pt-2 pb-3 space-y-1">
              {navigation.map((item) => (
                <Link
                  key={item.name}
                  to={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`block px-3 py-2 rounded-md text-base font-medium transition-colors duration-150 no-underline ${
                    isActive(item.href)
                      ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
                      : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-700'
                  }`}
                  aria-current={isActive(item.href) ? 'page' : undefined}
                >
                  {item.name}
                </Link>
              ))}
            </div>
          </nav>
        )}
      </header>

      {/* Main Content */}
      <main id="main-content" className="flex-1" role="main">
        {children}
      </main>

      {/* Footer */}
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
```

# frontend/src/components/common/Button.jsx – Accessible button component with variants

```jsx
import React, { forwardRef } from 'react';
import PropTypes from 'prop-types';

const Button = forwardRef(({
  children,
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  fullWidth = false,
  type = 'button',
  onClick,
  className = '',
  ariaLabel,
  ariaPressed,
  ariaExpanded,
  ...rest
}, ref) => {
  const baseClasses = 'btn transition-all duration-150 font-medium rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2';
  
  const variantClasses = {
    primary: 'btn-primary',
    secondary: 'btn-secondary',
    ghost: 'btn-ghost',
    danger: 'btn-danger',
  };

  const sizeClasses = {
    sm: 'text-xs px-3 py-1.5 min-h-[36px]',
    md: 'text-sm px-4 py-2 min-h-[44px]',
    lg: 'text-base px-6 py-3 min-h-[52px]',
  };

  const classes = [
    baseClasses,
    variantClasses[variant],
    sizeClasses[size],
    fullWidth && 'w-full',
    disabled && 'opacity-60 cursor-not-allowed',
    loading && 'cursor-wait',
    className,
  ].filter(Boolean).join(' ');

  return (
    <button
      ref={ref}
      type={type}
      className={classes}
      disabled={disabled || loading}
      onClick={onClick}
      aria-label={ariaLabel}
      aria-pressed={ariaPressed}
      aria-expanded={ariaExpanded}
      {...rest}
    >
      {loading ? (
        <span className="flex items-center justify-center">
          <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <span>{children}</span>
        </span>
      ) : (
        children
      )}
    </button>
  );
});

Button.displayName = 'Button';

Button.propTypes = {
  children: PropTypes.node.isRequired,
  variant: PropTypes.oneOf(['primary', 'secondary', 'ghost', 'danger']),
  size: PropTypes.oneOf(['sm', 'md', 'lg']),
  disabled: PropTypes.bool,
  loading: PropTypes.bool,
  fullWidth: PropTypes.bool,
  type: PropTypes.oneOf(['button', 'submit', 'reset']),
  onClick: PropTypes.func,
  className: PropTypes.string,
  ariaLabel: PropTypes.string,
  ariaPressed: PropTypes.bool,
  ariaExpanded: PropTypes.bool,
};

export default Button;
```

# frontend/src/components/common/Modal.jsx – Accessible modal with focus trapping

```jsx
import React, { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import PropTypes from 'prop-types';

export default function Modal({ 
  isOpen, 
  onClose, 
  title, 
  children, 
  size = 'md',
  closeOnOverlayClick = true,
  showCloseButton = true,
  ariaDescribedBy,
}) {
  const modalRef = useRef(null);
  const previousActiveElement = useRef(null);

  // Handle focus trap and return focus
  useEffect(() => {
    if (isOpen) {
      previousActiveElement.current = document.activeElement;
      modalRef.current?.focus();

      const handleKeyDown = (e) => {
        if (e.key === 'Escape') {
          onClose();
        }
        
        // Focus trap
        if (e.key === 'Tab') {
          const focusableElements = modalRef.current?.querySelectorAll(
            'a[href], button, textarea, input, select, [tabindex]:not([tabindex="-1"])'
          );
          
          if (!focusableElements?.length) return;
          
          const firstElement = focusableElements[0];
          const lastElement = focusableElements[focusableElements.length - 1];
          
          if (e.shiftKey && document.activeElement === firstElement) {
            e.preventDefault();
            lastElement.focus();
          } else if (!e.shiftKey && document.activeElement === lastElement) {
            e.preventDefault();
            firstElement.focus();
          }
        }
      };

      document.addEventListener('keydown', handleKeyDown);

      return () => {
        document.removeEventListener('keydown', handleKeyDown);
        previousActiveElement.current?.focus();
      };
    }
  }, [isOpen, onClose]);

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }

    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const sizeClasses = {
    sm: 'sm:max-w-md',
    md: 'sm:max-w-lg',
    lg: 'sm:max-w-2xl',
    xl: 'sm:max-w-4xl',
    full: 'sm:max-w-full sm:m-4',
  };

  const modalContent = (
    <div 
      className="fixed inset-0 z-50 overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      aria-describedby={ariaDescribedBy}
    >
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        {/* Backdrop */}
        <div 
          className="fixed inset-0 bg-gray-500 dark:bg-gray-900 bg-opacity-75 dark:bg-opacity-75 transition-opacity animate-fade-in"
          onClick={closeOnOverlayClick ? onClose : undefined}
          aria-hidden="true"
        />

        {/* This element is to trick the browser into centering the modal contents. */}
        <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">
          &#8203;
        </span>

        {/* Modal panel */}
        <div
          ref={modalRef}
          tabIndex={-1}
          className={`inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle ${sizeClasses[size]} w-full animate-scale-in`}
        >
          {/* Header */}
          <div className="bg-white dark:bg-gray-800 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <div className="flex items-center justify-between mb-4">
              <h3 id="modal-title" className="text-lg font-medium text-gray-900 dark:text-gray-100">
                {title}
              </h3>
              {showCloseButton && (
                <button
                  onClick={onClose}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors duration-150 p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
                  aria-label="Close modal"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>
            <div className="mt-2">
              {children}
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}

Modal.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  title: PropTypes.string.isRequired,
  children: PropTypes.node,
  size: PropTypes.oneOf(['sm', 'md', 'lg', 'xl', 'full']),
  closeOnOverlayClick: PropTypes.bool,
  showCloseButton: PropTypes.bool,
  ariaDescribedBy: PropTypes.string,
};
```

# frontend/src/components/common/Toast.jsx – Accessible toast notifications with animations

```jsx
import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import PropTypes from 'prop-types';

const toastContainer = document.createElement('div');
toastContainer.id = 'toast-container';
toastContainer.className = 'fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none';
document.body.appendChild(toastContainer);

let toastId = 0;

export function toast(message, options = {}) {
  const id = ++toastId;
  const event = new CustomEvent('show-toast', {
    detail: { id, message, ...options }
  });
  window.dispatchEvent(event);
}

toast.success = (message, options) => toast(message, { ...options, type: 'success' });
toast.error = (message, options) => toast(message, { ...options, type: 'error' });
toast.info = (message, options) => toast(message, { ...options, type: 'info' });
toast.warning = (message, options) => toast(message, { ...options, type: 'warning' });

function ToastItem({ id, message, type = 'info', duration = 5000, onClose }) {
  const [isVisible, setIsVisible] = useState(false);
  const [isExiting, setIsExiting] = useState(false);

  useEffect(() => {
    // Trigger entrance animation
    requestAnimationFrame(() => setIsVisible(true));

    const timer = setTimeout(() => {
      handleClose();
    }, duration);

    return () => clearTimeout(timer);
  }, [duration]);

  const handleClose = () => {
    setIsExiting(true);
    setTimeout(() => {
      onClose(id);
    }, 200);
  };

  const typeClasses = {
    success: 'bg-green-50 dark:bg-green-900/50 text-green-800 dark:text-green-200 border-green-200 dark:border-green-800',
    error: 'bg-red-50 dark:bg-red-900/50 text-red-800 dark:text-red-200 border-red-200 dark:border-red-800',
    warning: 'bg-yellow-50 dark:bg-yellow-900/50 text-yellow-800 dark:text-yellow-200 border-yellow-200 dark:border-yellow-800',
    info: 'bg-blue-50 dark:bg-blue-900/50 text-blue-800 dark:text-blue-200 border-blue-200 dark:border-blue-800',
  };

  const icons = {
    success: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
    ),
    error: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
      </svg>
    ),
    warning: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
    info: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  };

  return (
    <div
      role="alert"
      aria-live="polite"
      className={`
        pointer-events-auto flex items-center gap-3 p-4 rounded-lg border shadow-lg
        transform transition-all duration-200 
        ${typeClasses[type]}
        ${isVisible && !isExiting ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'}
      `}
    >
      <div className="flex-shrink-0">{icons[type]}</div>
      <p className="text-sm font-medium">{message}</p>
      <button
        onClick={handleClose}
        className="flex-shrink-0 ml-4 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
        aria-label="Close notification"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}

ToastItem.propTypes = {
  id: PropTypes.number.isRequired,
  message: PropTypes.string.isRequired,
  type: PropTypes.oneOf(['success', 'error', 'warning', 'info']),
  duration: PropTypes.number,
  onClose: PropTypes.func.isRequired,
};

export function ToastContainer() {
  const [toasts, setToasts] = useState([]);

  useEffect(() => {
    const handleShowToast = (event) => {
      setToasts((prev) => [...prev, event.detail]);
    };

    window.addEventListener('show-toast', handleShowToast);
    return () => window.removeEventListener('show-toast', handleShowToast);
  }, []);

  const removeToast = (id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  };

  return createPortal(
    <>
      {toasts.map((toast) => (
        <ToastItem
          key={toast.id}
          {...toast}
          onClose={removeToast}
        />
      ))}
    </>,
    toastContainer
  );
}
```

# frontend/src/components/common/LoadingSpinner.jsx – Accessible loading spinner with size variants

```jsx
import React from 'react';
import PropTypes from 'prop-types';

export default function LoadingSpinner({ 
  size = 'md', 
  className = '', 
  label = 'Loading...' 
}) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12',
    xl: 'h-16 w-16',
  };

  return (
    <div 
      className={`flex items-center justify-center ${className}`}
      role="status"
      aria-live="polite"
      aria-label={label}
    >
      <svg 
        className={`animate-spin ${sizeClasses[size]} text-brand-primary-600 dark:text-brand-primary-400`}
        fill="none" 
        viewBox="0 0 24 24"
      >
        <circle 
          className="opacity-25" 
          cx="12" 
          cy="12" 
          r="10" 
          stroke="currentColor" 
          strokeWidth="4"
        />
        <path 
          className="opacity-75" 
          fill="currentColor" 
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
      <span className="sr-only">{label}</span>
    </div>
  );
}

LoadingSpinner.propTypes = {
  size: PropTypes.oneOf(['sm', 'md', 'lg', 'xl']),
  className: PropTypes.string,
  label: PropTypes.string,
};
```

# frontend/src/components/common/FormInput.jsx – Accessible form input with error states

```jsx
import React, { forwardRef } from 'react';
import PropTypes from 'prop-types';

const FormInput = forwardRef(({
  id,
  name,
  type = 'text',
  label,
  value,
  onChange,
  onBlur,
  error,
  helpText,
  required = false,
  disabled = false,
  placeholder,
  autoComplete,
  className = '',
  inputClassName = '',
  ...rest
}, ref) => {
  const inputId = id || name;
  const errorId = error ? `${inputId}-error` : undefined;
  const helpId = helpText ? `${inputId}-help` : undefined;

  return (
    <div className={`form-group ${className}`}>
      {label && (
        <label 
          htmlFor={inputId} 
          className="form-label"
        >
          {label}
          {required && <span className="text-error-500 ml-1" aria-label="required">*</span>}
        </label>
      )}
      
      <input
        ref={ref}
        id={inputId}
        name={name}
        type={type}
        value={value}
        onChange={onChange}
        onBlur={onBlur}
        disabled={disabled}
        required={required}
        placeholder={placeholder}
        autoComplete={autoComplete}
        aria-invalid={error ? 'true' : 'false'}
        aria-describedby={[errorId, helpId].filter(Boolean).join(' ') || undefined}
        className={`
          w-full px-3 py-2 border rounded-md shadow-sm transition-colors duration-150
          ${error 
            ? 'border-error-500 focus:ring-error-500 focus:border-error-500' 
            : 'border-gray-300 dark:border-gray-600 focus:ring-brand-primary-500 focus:border-brand-primary-500'
          }
          bg-white dark:bg-gray-800
          text-gray-900 dark:text-gray-100
          placeholder-gray-400 dark:placeholder-gray-500
          disabled:bg-gray-50 dark:disabled:bg-gray-900 disabled:opacity-60 disabled:cursor-not-allowed
          focus:outline-none focus:ring-2
          ${inputClassName}
        `}
        {...rest}
      />
      
      {error && (
        <p id={errorId} className="form-error mt-1" role="alert">
          {error}
        </p>
      )}
      
      {helpText && !error && (
        <p id={helpId} className="form-help mt-1">
          {helpText}
        </p>
      )}
    </div>
  );
});

FormInput.displayName = 'FormInput';

FormInput.propTypes = {
  id: PropTypes.string,
  name: PropTypes.string.isRequired,
  type: PropTypes.string,
  label: PropTypes.string,
  value: PropTypes.string,
  onChange: PropTypes.func.isRequired,
  onBlur: PropTypes.func,
  error: PropTypes.string,
