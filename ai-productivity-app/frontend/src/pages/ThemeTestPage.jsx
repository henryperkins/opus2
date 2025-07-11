import React from "react";
import ThemeTest from "../components/ThemeTest";
import ThemeToggle from "../components/common/ThemeToggle";
import MinimalThemeTest from "../components/MinimalThemeTest";
import DarkModeTest from "../components/DarkModeTest";

export default function ThemeTestPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-gray-900 transition-colors duration-200">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center p-4 border-b border-gray-200 dark:border-gray-700">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
            Theme Testing Page
          </h1>
          <ThemeToggle />
        </div>

        <ThemeTest />

        <div className="border-t border-gray-200 dark:border-gray-700 my-8" />

        <MinimalThemeTest />

        <div className="border-t border-gray-200 dark:border-gray-700 my-8" />

        <DarkModeTest />

        <div className="p-8 space-y-4">
          <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            Additional Test Elements
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
              <h4 className="font-semibold text-blue-900 dark:text-blue-100">
                Info Box
              </h4>
              <p className="text-blue-700 dark:text-blue-300">
                This should have blue theming.
              </p>
            </div>

            <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
              <h4 className="font-semibold text-green-900 dark:text-green-100">
                Success Box
              </h4>
              <p className="text-green-700 dark:text-green-300">
                This should have green theming.
              </p>
            </div>
          </div>

          <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <p className="text-gray-600 dark:text-gray-400">
              Check the console for detailed theme state information when
              clicking "Check DOM State".
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
