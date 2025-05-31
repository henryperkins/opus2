/* Settings Page
 *
 * Purpose
 * -------
 * User settings and preferences management page.
 * Integrates with auth store for persistent settings.
 */

import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import useAuthStore from '../stores/authStore';
import Header from '../components/common/Header';

function SettingsPage() {
  const { user } = useAuth();
  const { preferences, setPreference, setPreferences } = useAuthStore();
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handlePreferenceChange = (key, value) => {
    setPreference(key, value);
    setMessage('Settings saved automatically');
    setTimeout(() => setMessage(''), 2000);
  };

  const handleSaveAll = () => {
    setLoading(true);
    // In a real app, you might sync these with the backend
    setTimeout(() => {
      setLoading(false);
      setMessage('All settings saved successfully');
      setTimeout(() => setMessage(''), 3000);
    }, 500);
  };

  if (!user) {
    return <div>Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      
      <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h1 className="text-2xl font-semibold text-gray-900">Settings</h1>
            <p className="text-sm text-gray-600 mt-1">
              Manage your account preferences and application settings
            </p>
          </div>

          <div className="p-6 space-y-6">
            {/* User Preferences */}
            <div>
              <h2 className="text-lg font-medium text-gray-900 mb-4">
                User Preferences
              </h2>
              
              <div className="space-y-4">
                {/* Remember Me */}
                <div className="flex items-center justify-between">
                  <div>
                    <label className="text-sm font-medium text-gray-700">
                      Remember Me
                    </label>
                    <p className="text-sm text-gray-500">
                      Keep me logged in on this device
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    checked={preferences.rememberMe}
                    onChange={(e) => handlePreferenceChange('rememberMe', e.target.checked)}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                </div>

                {/* Theme */}
                <div className="flex items-center justify-between">
                  <div>
                    <label className="text-sm font-medium text-gray-700">
                      Theme
                    </label>
                    <p className="text-sm text-gray-500">
                      Choose your preferred theme
                    </p>
                  </div>
                  <select
                    value={preferences.theme}
                    onChange={(e) => handlePreferenceChange('theme', e.target.value)}
                    className="border border-gray-300 rounded-md px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="light">Light</option>
                    <option value="dark">Dark</option>
                    <option value="auto">Auto</option>
                  </select>
                </div>

                {/* Language */}
                <div className="flex items-center justify-between">
                  <div>
                    <label className="text-sm font-medium text-gray-700">
                      Language
                    </label>
                    <p className="text-sm text-gray-500">
                      Select your preferred language
                    </p>
                  </div>
                  <select
                    value={preferences.language}
                    onChange={(e) => handlePreferenceChange('language', e.target.value)}
                    className="border border-gray-300 rounded-md px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="en">English</option>
                    <option value="es">Español</option>
                    <option value="fr">Français</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Account Security */}
            <div className="border-t border-gray-200 pt-6">
              <h2 className="text-lg font-medium text-gray-900 mb-4">
                Account Security
              </h2>
              
              <div className="space-y-4">
                <div className="bg-gray-50 p-4 rounded-md">
                  <h3 className="text-sm font-medium text-gray-900">
                    Password
                  </h3>
                  <p className="text-sm text-gray-600 mt-1">
                    Last changed: Never
                  </p>
                  <button className="mt-2 text-sm text-blue-600 hover:text-blue-700">
                    Change Password
                  </button>
                </div>

                <div className="bg-gray-50 p-4 rounded-md">
                  <h3 className="text-sm font-medium text-gray-900">
                    Two-Factor Authentication
                  </h3>
                  <p className="text-sm text-gray-600 mt-1">
                    Not enabled
                  </p>
                  <button className="mt-2 text-sm text-blue-600 hover:text-blue-700">
                    Enable 2FA
                  </button>
                </div>
              </div>
            </div>

            {/* Success Message */}
            {message && (
              <div className="bg-green-50 border border-green-200 rounded-md p-4">
                <div className="flex">
                  <svg
                    className="h-5 w-5 text-green-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  <p className="ml-3 text-sm text-green-700">{message}</p>
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="border-t border-gray-200 pt-6 flex justify-end space-x-3">
              <button
                type="button"
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                Reset to Defaults
              </button>
              <button
                onClick={handleSaveAll}
                disabled={loading}
                className="px-4 py-2 bg-blue-600 border border-transparent rounded-md text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              >
                {loading ? 'Saving...' : 'Save All Settings'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default SettingsPage;