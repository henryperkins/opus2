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
  // ---------------------------------------------------------------------------
  // Initial state – prefer localStorage, fall back to system preference.
  // ---------------------------------------------------------------------------
  /* -------------------------------------------------------------------------
   * Theme source of truth
   * ------------------------------------------------------------------------
   * 1. We first try to read the preference from the Zustand auth store so the
   *    user-selected theme survives across devices/browsers (the store itself
   *    is persisted via `zustand/middleware/persist`).
   * 2. If the store has no preference we fall back to localStorage (legacy –
   *    kept for backward compatibility so existing users keep their choice).
   * 3. Finally we fall back to the system preference.
   */

  const { preferences, setPreference } = useAuthStore();

  // Helper to map preference -> actual theme string (light | dark)
  const getSystemTheme = () =>
    window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';

  const [theme, setThemeState] = useState(() => {
    if (typeof window === 'undefined') return 'light';

    const prefFromStore = preferences?.theme;
    if (prefFromStore === 'light' || prefFromStore === 'dark') {
      return prefFromStore;
    }

    if (prefFromStore === 'auto') {
      return getSystemTheme();
    }

    const saved = localStorage.getItem('theme');
    if (saved === 'light' || saved === 'dark') return saved;

    return getSystemTheme();
  });

  // ---------------------------------------------------------------------------
  // Helper to apply the theme to the <html> element and meta tag.
  // ---------------------------------------------------------------------------
  const applyTheme = useCallback((newTheme) => {
    const root = document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(newTheme);

    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
      meta.content = newTheme === 'dark' ? '#111827' : '#ffffff';
    }
  }, []);

  // ---------------------------------------------------------------------------
  // React to external preference updates (e.g. Settings page) -----------------
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const pref = preferences?.theme;

    // Fast-exit if nothing changed
    if (!pref) return;

    // 1. Explicit light / dark preference ------------------------------------
    if (pref === 'light' || pref === 'dark') {
      if (pref !== theme) {
        /*
         * We ONLY want to update the *effective* theme here – the preference
         * itself is already stored in Zustand, so persisting again would be
         * redundant and would overwrite an eventual user choice that happened
         * in another tab while this tab was in the background.
         */
        setThemeState(pref);
        applyTheme(pref);
        // Keep fallback storage in sync without re-triggering Zustand updates
        localStorage.setItem('theme', pref);
      }
      return;
    }

    // 2. "Auto" preference – follow system setting ---------------------------
    if (pref === 'auto') {
      const sys = getSystemTheme();
      if (sys !== theme) {
        // Do *not* persist the computed value – keep the original "auto"
        // preference intact while still reflecting the correct UI theme.
        setThemeState(sys);
        applyTheme(sys);
      }
    }
  }, [preferences?.theme, theme, applyTheme]);

  // ---------------------------------------------------------------------------
  // Public setter – updates state, storage & DOM.
  // ---------------------------------------------------------------------------
  const setTheme = useCallback(
    (newTheme) => {
      if (newTheme !== 'light' && newTheme !== 'dark') return;

      setThemeState(newTheme);
      // Persist both in Zustand store and localStorage for backward compat.
      setPreference('theme', newTheme);
      localStorage.setItem('theme', newTheme);
      applyTheme(newTheme);
    },
    [applyTheme, setPreference]
  );

  // Convenience toggle ---------------------------------------------------------
  const toggleTheme = useCallback(() => {
    const next = theme === 'light' ? 'dark' : 'light';
    setTheme(next);
  }, [theme, setTheme]);

  // Apply theme at mount & whenever it changes --------------------------------
  useEffect(() => {
    applyTheme(theme);
  }, [theme, applyTheme]);

  // Keep in-sync with system preference changes -------------------------------
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    const handleChange = (e) => {
      // Only update when user preference is set to "auto" (or unset).
      const pref = preferences?.theme;
      if (!pref || pref === 'auto') {
        setTheme(e.matches ? 'dark' : 'light');
      }
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [setTheme, preferences?.theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

ThemeProvider.propTypes = {
  children: PropTypes.node.isRequired,
};

export function useTheme() {
  return useContext(ThemeContext);
}
