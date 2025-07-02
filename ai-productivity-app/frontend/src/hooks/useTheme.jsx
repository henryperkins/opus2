// Theme management hook ---------------------------------------------------------
// Provides a context with `theme`, `setTheme`, and `toggleTheme`.  The selected
// theme is persisted to localStorage and kept in-sync with the system colour
// scheme.

import { useState, useEffect, useCallback, createContext, useContext } from 'react';
import useAuthStore from '../stores/authStore';
import PropTypes from 'prop-types';

const ThemeContext = createContext({
  theme: 'light',
  setTheme: () => {},
  toggleTheme: () => {},
});

export function ThemeProvider({ children }) {
  const { preferences, setPreference } = useAuthStore();

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
  // Sync with Zustand store when it hydrates or changes
  // ---------------------------------------------------------------------------
  useEffect(() => {
    // Wait for the store to be hydrated (preferences will be null initially)
    if (!preferences) return;

    const pref = preferences.theme;

    // Handle explicit light/dark preference
    if (pref === 'light' || pref === 'dark') {
      if (pref !== theme) {
        setThemeState(pref);
        applyTheme(pref);
        // Keep fallback storage in sync
        localStorage.setItem('theme', pref);
      }
      return;
    }

    // Handle auto preference - follow system setting
    if (pref === 'auto') {
      const sys = getSystemTheme();
      if (sys !== theme) {
        setThemeState(sys);
        applyTheme(sys);
      }
      return;
    }

    // If no preference is set in the store, check localStorage for legacy support
    const legacyTheme = localStorage.getItem('theme');
    if (legacyTheme === 'light' || legacyTheme === 'dark') {
      if (legacyTheme !== theme) {
        setThemeState(legacyTheme);
        applyTheme(legacyTheme);
        // Migrate to Zustand store
        setPreference('theme', legacyTheme);
      }
    }
  }, [preferences, theme, applyTheme, getSystemTheme, setPreference]);

  // ---------------------------------------------------------------------------
  // Public setter – updates state, storage & DOM.
  // ---------------------------------------------------------------------------
  const setTheme = useCallback(
    (newTheme) => {
      console.log('setTheme called with:', newTheme);
      if (newTheme !== 'light' && newTheme !== 'dark' && newTheme !== 'auto') return;

      if (newTheme === 'auto') {
        const systemTheme = getSystemTheme();
        console.log('Auto theme detected, using system theme:', systemTheme);
        setThemeState(systemTheme);
        applyTheme(systemTheme);
      } else {
        console.log('Setting theme state and applying:', newTheme);
        setThemeState(newTheme);
        applyTheme(newTheme);
        // Keep fallback storage in sync
        localStorage.setItem('theme', newTheme);
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

  // Apply theme at mount & whenever it changes --------------------------------
  useEffect(() => {
    console.log('Applying theme to DOM:', theme);
    applyTheme(theme);
  }, [theme, applyTheme]);

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
