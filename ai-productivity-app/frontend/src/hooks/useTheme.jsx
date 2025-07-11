// Theme management hook ---------------------------------------------------------
// Provides a context with `theme`, `setTheme`, and `toggleTheme`.  The selected
// theme is persisted to localStorage and kept in-sync with the system colour
// scheme.

import {
  useState,
  useEffect,
  useCallback,
  createContext,
  useContext,
} from "react";
import useAuthStore from "../stores/authStore";
import PropTypes from "prop-types";

const ThemeContext = createContext({
  theme: "light",
  setTheme: () => {},
  toggleTheme: () => {},
});

export function ThemeProvider({ children }) {
  const { preferences, setPreference } = useAuthStore();

  // Helper to map preference -> actual theme string (light | dark)
  const getSystemTheme = useCallback(() => {
    if (typeof window === "undefined") return "light";
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }, []);

  // Helper to get the current theme from DOM (set by HTML script)
  const getCurrentThemeFromDOM = useCallback(() => {
    if (typeof window === "undefined") return "light";
    const root = document.documentElement;
    return root.classList.contains("dark") ? "dark" : "light";
  }, []);

  // Helper to resolve the actual theme based on preference
  const resolveTheme = useCallback(
    (preference) => {
      if (preference === "auto") {
        return getSystemTheme();
      }
      return preference === "dark" || preference === "light"
        ? preference
        : "light";
    },
    [getSystemTheme],
  );

  const [theme, setThemeState] = useState(() => {
    if (typeof window === "undefined") return "light";

    // First, check what the HTML script already applied to avoid flash
    const domTheme = getCurrentThemeFromDOM();
    if (domTheme) {
      return domTheme;
    }

    // If we have preferences, use them
    if (preferences?.theme) {
      return resolveTheme(preferences.theme);
    }

    // Fallback to system preference
    return getSystemTheme();
  });

  // ---------------------------------------------------------------------------
  // Helper to apply the theme to the <html> element and meta tag.
  // ---------------------------------------------------------------------------
  const applyTheme = useCallback((newTheme) => {
    if (typeof window === "undefined") return;

    const root = document.documentElement;
    root.classList.remove("light", "dark");
    root.classList.add(newTheme);

    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
      meta.content = newTheme === "dark" ? "#111827" : "#ffffff";
    }
  }, []);

  // ---------------------------------------------------------------------------
  // Sync with Zustand store when preferences change
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (!preferences?.theme) return;

    const resolvedTheme = resolveTheme(preferences.theme);

    if (resolvedTheme !== theme) {
      setThemeState(resolvedTheme);
      applyTheme(resolvedTheme);
    }
  }, [preferences?.theme, resolveTheme, applyTheme, theme]);

  // ---------------------------------------------------------------------------
  // Public setter – updates state, storage & DOM.
  // ---------------------------------------------------------------------------
  const setTheme = useCallback(
    (newTheme) => {
      if (newTheme !== "light" && newTheme !== "dark" && newTheme !== "auto") {
        return;
      }

      const resolvedTheme = resolveTheme(newTheme);

      // Update state
      setThemeState(resolvedTheme);

      // Apply to DOM immediately
      applyTheme(resolvedTheme);

      // Keep fallback storage in sync
      if (newTheme !== "auto") {
        localStorage.setItem("theme", resolvedTheme);
      }

      // Always persist the preference
      setPreference("theme", newTheme);
    },
    [applyTheme, setPreference, resolveTheme],
  );

  // Convenience toggle ---------------------------------------------------------
  const toggleTheme = useCallback(() => {
    const next = theme === "light" ? "dark" : "light";
    setTheme(next);
  }, [theme, setTheme]);

  // Apply theme on mount -------------------------------------------------------
  useEffect(() => {
    applyTheme(theme);
  }, []); // Only on mount

  // Keep in-sync with system preference changes -------------------------------
  useEffect(() => {
    if (typeof window === "undefined") return;

    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

    const handleChange = (e) => {
      const pref = preferences?.theme;
      if (!pref || pref === "auto") {
        const newTheme = e.matches ? "dark" : "light";
        setThemeState(newTheme);
        applyTheme(newTheme);
      }
    };

    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
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
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
};
