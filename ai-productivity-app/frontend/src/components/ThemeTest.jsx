import React from "react";
import { useTheme } from "../hooks/useTheme";

export default function ThemeTest() {
  const { theme, toggleTheme } = useTheme();

  // Check DOM state directly
  const checkDOMState = () => {
    const root = document.documentElement;
    const currentClasses = root.classList.toString();
    const metaTheme = document.querySelector('meta[name="theme-color"]');
    const metaContent = metaTheme ? metaTheme.content : "not found";

    console.log("=== Theme Debug Info ===");
    console.log("Hook theme state:", theme);
    console.log("DOM classes:", currentClasses);
    console.log("Meta theme-color:", metaContent);
    console.log("Contains dark class:", root.classList.contains("dark"));
    console.log("Contains light class:", root.classList.contains("light"));

    // Check computed styles
    const bgColor = window.getComputedStyle(document.body).backgroundColor;
    console.log("Body background color:", bgColor);
  };

  return (
    <div className="p-8 space-y-4">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
        Theme Test Component
      </h2>

      <div className="space-y-2">
        <p className="text-gray-700 dark:text-gray-300">
          Current theme from hook: <strong>{theme}</strong>
        </p>

        <div className="flex gap-4">
          <button
            onClick={toggleTheme}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Toggle Theme
          </button>

          <button
            onClick={checkDOMState}
            className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
          >
            Check DOM State
          </button>
        </div>

        <div className="mt-4 p-4 rounded-lg bg-gray-100 dark:bg-gray-800">
          <p className="text-gray-900 dark:text-gray-100">
            This box should be light gray in light mode and dark gray in dark
            mode.
          </p>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-4">
          <div className="p-4 rounded bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700">
            <p className="text-gray-900 dark:text-gray-100">Test Card 1</p>
          </div>
          <div className="p-4 rounded bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700">
            <p className="text-gray-900 dark:text-gray-100">Test Card 2</p>
          </div>
        </div>
      </div>
    </div>
  );
}
