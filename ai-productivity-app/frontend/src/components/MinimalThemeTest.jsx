import React from "react";

export default function MinimalThemeTest() {
  const toggleTheme = () => {
    const root = document.documentElement;
    const currentTheme = root.classList.contains("dark") ? "dark" : "light";
    const newTheme = currentTheme === "dark" ? "light" : "dark";

    console.log("Minimal test - switching from", currentTheme, "to", newTheme);

    root.classList.remove("light", "dark");
    root.classList.add(newTheme);

    // Also update localStorage
    localStorage.setItem("theme", newTheme);

    // Update meta theme-color
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
      meta.content = newTheme === "dark" ? "#111827" : "#ffffff";
    }
  };

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4 text-gray-900 dark:text-gray-100">
        Minimal Theme Test
      </h1>

      <p className="mb-4 text-gray-700 dark:text-gray-300">
        This test bypasses all React context and Zustand to directly manipulate
        the DOM.
      </p>

      <button
        onClick={toggleTheme}
        className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
      >
        Toggle Theme (Direct DOM)
      </button>

      <div className="mt-8 grid grid-cols-2 gap-4">
        <div className="p-4 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded">
          <p className="text-gray-900 dark:text-gray-100">Test Box 1</p>
        </div>
        <div className="p-4 bg-gray-100 dark:bg-gray-800 rounded">
          <p className="text-gray-900 dark:text-gray-100">Test Box 2</p>
        </div>
      </div>
    </div>
  );
}
