import React, { useEffect } from 'react';
import { useTheme } from '../hooks/useTheme';
import useAuthStore from '../stores/authStore';

export default function ThemeDebug() {
  const { theme, toggleTheme, setTheme } = useTheme();
  const { preferences } = useAuthStore();

  // Log whenever theme or preferences change
  useEffect(() => {
    console.log('=== Theme State Update ===');
    console.log('Hook theme:', theme);
    console.log('Zustand theme preference:', preferences?.theme);
    console.log('DOM dark class:', document.documentElement.classList.contains('dark'));
    console.log('DOM light class:', document.documentElement.classList.contains('light'));
  }, [theme, preferences?.theme]);

  return (
    <div className="fixed bottom-4 right-4 bg-white dark:bg-gray-800 p-4 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-50">
      <h3 className="text-sm font-semibold mb-2 text-gray-900 dark:text-gray-100">Theme Debug</h3>
      <div className="space-y-1 text-xs">
        <p className="text-gray-600 dark:text-gray-400">
          Hook: <span className="font-mono text-gray-900 dark:text-gray-100">{theme}</span>
        </p>
        <p className="text-gray-600 dark:text-gray-400">
          Zustand: <span className="font-mono text-gray-900 dark:text-gray-100">{preferences?.theme || 'null'}</span>
        </p>
        <p className="text-gray-600 dark:text-gray-400">
          DOM: <span className="font-mono text-gray-900 dark:text-gray-100">
            {document.documentElement.classList.contains('dark') ? 'dark' : 'light'}
          </span>
        </p>
      </div>
      <div className="mt-3 space-x-2">
        <button
          onClick={toggleTheme}
          className="px-2 py-1 bg-blue-500 text-white rounded text-xs hover:bg-blue-600"
        >
          Toggle
        </button>
        <button
          onClick={() => setTheme('light')}
          className="px-2 py-1 bg-gray-200 text-gray-800 rounded text-xs hover:bg-gray-300"
        >
          Light
        </button>
        <button
          onClick={() => setTheme('dark')}
          className="px-2 py-1 bg-gray-800 text-white rounded text-xs hover:bg-gray-900"
        >
          Dark
        </button>
      </div>
    </div>
  );
}
