import React from 'react';

export default function DarkModeTest() {
  return (
    <div className="p-8 space-y-4">
      <h1 className="text-2xl font-bold">Dark Mode Test</h1>
      
      {/* Test 1: Basic Tailwind dark mode utilities */}
      <div className="p-4 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 rounded-lg border border-gray-300 dark:border-gray-700">
        <p>Test 1: Basic dark mode utilities</p>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          This should have white background in light mode and dark gray in dark mode.
        </p>
      </div>
      
      {/* Test 2: Custom CSS component */}
      <div className="chat-layout p-4 rounded-lg">
        <p>Test 2: Custom CSS component (.chat-layout)</p>
        <p className="text-sm">
          This uses the .chat-layout class which should respond to dark mode.
        </p>
      </div>
      
      {/* Test 3: Direct style to verify */}
      <div 
        className="p-4 rounded-lg" 
        style={{ 
          backgroundColor: 'var(--test-bg, #f3f4f6)',
          color: 'var(--test-color, #111827)'
        }}
      >
        <p>Test 3: CSS Variables (fallback test)</p>
      </div>
      
      {/* Test 4: Nested dark mode */}
      <div className="p-4 space-y-2">
        <div className="p-2 bg-gray-100 dark:bg-gray-800 rounded">
          <p className="text-gray-900 dark:text-gray-100">Parent element</p>
          <div className="mt-2 p-2 bg-gray-200 dark:bg-gray-700 rounded">
            <p className="text-gray-800 dark:text-gray-200">Nested element</p>
          </div>
        </div>
      </div>
      
      {/* Test 5: Test CSS classes */}
      <div className="space-y-2">
        <div className="test-dark-mode p-4 rounded">Test CSS: .test-dark-mode</div>
        <div className="test-dark-mode-where p-4 rounded">Test CSS: .test-dark-mode-where</div>
        <div className="test-dark-mode-html p-4 rounded">Test CSS: .test-dark-mode-html</div>
        <div className="test-dark-mode-descendant p-4 rounded">Test CSS: .test-dark-mode-descendant</div>
      </div>
      
      {/* Test 6: Button to manually toggle for testing */}
      <button
        onClick={() => {
          document.documentElement.classList.toggle('dark');
          console.log('Toggled to:', document.documentElement.classList.contains('dark') ? 'dark' : 'light');
        }}
        className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded"
      >
        Manual Toggle (Direct DOM)
      </button>
    </div>
  );
}
