/* ModelSettingsPage.jsx – wrapper around reusable ModelConfiguration component */

import React from 'react';
import ModelConfiguration from '../components/settings/ModelConfiguration';

export default function ModelSettingsPage() {
  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100">

      <main className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Model Configuration</h1>
        <ModelConfiguration />
      </main>
    </div>
  );
}
