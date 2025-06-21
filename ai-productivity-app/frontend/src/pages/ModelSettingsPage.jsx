/* ModelSettingsPage.jsx – wrapper around reusable ModelConfiguration component */

import React from 'react';
import Header from '../components/common/Header';
import ModelConfiguration from '../components/settings/ModelConfiguration';

export default function ModelSettingsPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />

      <main className="max-w-6xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Model Configuration</h1>
        <ModelConfiguration />
      </main>
    </div>
  );
}
