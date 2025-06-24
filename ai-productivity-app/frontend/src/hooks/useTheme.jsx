// Theme management hook ---------------------------------------------------------
// Provides a context with `theme`, `setTheme`, and `toggleTheme`.  The selected
// theme is persisted to localStorage and kept in-sync with the system colour
// scheme.

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
  // ---------------------------------------------------------------------------
  // Initial state – prefer localStorage, fall back to system preference.
  // ---------------------------------------------------------------------------
  const [theme, setThemeState] = useState(() => {
    if (typeof window === 'undefined') return 'light';

    const saved = localStorage.getItem('theme');
    if (saved === 'light' || saved === 'dark') return saved;

    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    return 'light';
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
  // Public setter – updates state, storage & DOM.
  // ---------------------------------------------------------------------------
  const setTheme = useCallback(
    (newTheme) => {
      if (newTheme !== 'light' && newTheme !== 'dark') return;

      setThemeState(newTheme);
      localStorage.setItem('theme', newTheme);
      applyTheme(newTheme);
    },
    [applyTheme]
  );

  // Convenience toggle ---------------------------------------------------------
  // Note: our `setTheme` helper expects the **next theme value**, not a
  // function updater.  Passing a function previously resulted in the guard
  // clause (`newTheme !== 'light' && newTheme !== 'dark'`) short-circuiting
  // the update, so the toggle never actually changed the theme.  Compute the
  // next theme explicitly instead.
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
