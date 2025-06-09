import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import UserMenu from '../auth/UserMenu';
import ThemeToggle from './ThemeToggle';

// -------------------------------------------------------------------------------------------------
// Global layout wrapper
// -------------------------------------------------------------------------------------------------

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
    <div className="min-h-screen gradient-bg transition-colors duration-200 flex flex-col">
      {/* Skip to main content link ------------------------------------------------*/}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      {/* ------------------------------------------------------------------------*/}
      {/* Header                                                                  */}
      {/* ------------------------------------------------------------------------*/}
      <header className="glass border-b border-white/20 dark:border-gray-700/20 transition-all duration-200 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo & Desktop Nav -----------------------------------------------*/}
            <div className="flex items-center">
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

              {/* Desktop Navigation -------------------------------------------*/}
              {user && (
                <nav
                  className="hidden md:flex ml-10 space-x-8"
                  role="navigation"
                  aria-label="Main navigation"
                >
                  {navigation.map((item) => (
                    <Link
                      key={item.name}
                      to={item.href}
                      className={`px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 no-underline ${
                        isActive(item.href)
                          ? 'bg-white/20 dark:bg-gray-700/50 text-gray-900 dark:text-gray-100 shadow-sm'
                          : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-white/10 dark:hover:bg-gray-700/30'
                      }`}
                      aria-current={isActive(item.href) ? 'page' : undefined}
                    >
                      {item.name}
                    </Link>
                  ))}
                </nav>
              )}
            </div>

            {/* Right side ------------------------------------------------------*/}
            <div className="flex items-center space-x-4">
              <ThemeToggle />

              {user ? (
                <>
                  <UserMenu />
                  {/* Mobile menu button */}
                  <button
                    onClick={() => setMobileMenuOpen((o) => !o)}
                    className="md:hidden p-2 rounded-md text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors duration-150"
                    aria-expanded={mobileMenuOpen}
                    aria-label="Toggle navigation menu"
                    type="button"
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
                <Link to="/login" className="btn btn-primary text-sm no-underline animate-bounce-in">
                  Sign In
                </Link>
              )}
            </div>
          </div>
        </div>

        {/* Mobile Navigation ----------------------------------------------------*/}
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

      {/* Main content -----------------------------------------------------------*/}
      <main id="main-content" className="flex-1" role="main">
        {children}
      </main>

      {/* Footer -----------------------------------------------------------------*/}
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
