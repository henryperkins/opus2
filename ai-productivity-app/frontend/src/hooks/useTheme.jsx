// Theme management hook ---------------------------------------------------------
// Provides a context with `theme`, `setTheme`, and `toggleTheme`.  The selected
// theme is persisted to localStorage and kept in-sync with the system colour
// scheme.

import { useState, useEffect, useCallback, createContext, useContext, useRef } from 'react';
import useAuthStore from '../stores/authStore';
import PropTypes from 'prop-types';

const ThemeContext = createContext({
  theme: 'light',
  setTheme: () => {},
  toggleTheme: () => {},
});

export function ThemeProvider({ children }) {
  const { preferences, setPreference } = useAuthStore();
  const isInitialMount = useRef(true);

  // Helper to map preference -> actual theme string (light | dark)
  const getSystemTheme = useCallback(() => {
    if (typeof window === 'undefined') return 'light';
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }, []);

  // Helper to get the current theme from DOM (set by HTML script)
  const getCurrentThemeFromDOM = useCallback(() => {
    if (typeof window === 'undefined') return 'light';
    const root = document.documentElement;
    return root.classList.contains('dark') ? 'dark' : 'light';
  }, []);

  const [theme, setThemeState] = useState(() => {
    if (typeof window === 'undefined') return 'light';

    // First, check what the HTML script already applied to avoid flash
    const domTheme = getCurrentThemeFromDOM();

    // If we already have a theme from the HTML script, use it initially
    if (domTheme) {
      return domTheme;
    }

    // Fallback to system preference if nothing is set
    return getSystemTheme();
  });

  // ---------------------------------------------------------------------------
  // Helper to apply the theme to the <html> element and meta tag.
  // ---------------------------------------------------------------------------
  const applyTheme = useCallback((newTheme) => {
    if (typeof window === 'undefined') return;

    console.log('applyTheme called with:', newTheme);
    const root = document.documentElement;
    
    // Only update if actually changing
    if (root.classList.contains(newTheme)) {
      console.log('Theme already applied:', newTheme);
      return;
    }

    console.log('Current classes before change:', root.classList.toString());

    root.classList.remove('light', 'dark');
    root.classList.add(newTheme);

    console.log('Current classes after change:', root.classList.toString());

    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
      meta.content = newTheme === 'dark' ? '#111827' : '#ffffff';
      console.log('Updated meta theme-color to:', meta.content);
    }
  }, []);

  // ---------------------------------------------------------------------------
  // Initialize theme from preferences on mount
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (!isInitialMount.current || !preferences) return;
    
    isInitialMount.current = false;
    
    const pref = preferences.theme;
    
    // Handle explicit preference
    if (pref === 'light' || pref === 'dark') {
      setThemeState(pref);
      applyTheme(pref);
      localStorage.setItem('theme', pref);
    } else if (pref === 'auto') {
      const systemTheme = getSystemTheme();
      setThemeState(systemTheme);
      applyTheme(systemTheme);
    } else {
      // No preference set, check localStorage for legacy support
      const legacyTheme = localStorage.getItem('theme');
      if (legacyTheme === 'light' || legacyTheme === 'dark') {
        setThemeState(legacyTheme);
        applyTheme(legacyTheme);
        setPreference('theme', legacyTheme);
      }
    }
  }, [preferences, applyTheme, getSystemTheme, setPreference]);

  // ---------------------------------------------------------------------------
  // Public setter – updates state, storage & DOM.
  // ---------------------------------------------------------------------------
  const setTheme = useCallback(
    (newTheme) => {
      console.log('setTheme called with:', newTheme);
      if (newTheme !== 'light' && newTheme !== 'dark' && newTheme !== 'auto') return;

      let actualTheme = newTheme;
      
      if (newTheme === 'auto') {
        actualTheme = getSystemTheme();
        console.log('Auto theme detected, using system theme:', actualTheme);
      }
      
      // Update state
      setThemeState(actualTheme);
      
      // Apply to DOM immediately
      applyTheme(actualTheme);
      
      // Keep fallback storage in sync
      if (newTheme !== 'auto') {
        localStorage.setItem('theme', actualTheme);
      }

      // Always persist the preference (including 'auto')
      console.log('Persisting theme preference to Zustand store:', newTheme);
      setPreference('theme', newTheme);
    },
    [applyTheme, setPreference, getSystemTheme]
  );

  // Convenience toggle ---------------------------------------------------------
  const toggleTheme = useCallback(() => {
    console.log('Theme toggle clicked. Current theme:', theme);
    const next = theme === 'light' ? 'dark' : 'light';
    console.log('Switching to theme:', next);
    setTheme(next);
  }, [theme, setTheme]);

  // Keep in-sync with system preference changes -------------------------------
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    const handleChange = (e) => {
      // Only update when user preference is set to "auto" (or unset).
      const pref = preferences?.theme;
      if (!pref || pref === 'auto') {
        const newTheme = e.matches ? 'dark' : 'light';
        setThemeState(newTheme);
        applyTheme(newTheme);
      }
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [preferences?.theme, applyTheme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

ThemeProvider.propTypes = {
  children: PropTypes.node.isRequired,
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};
