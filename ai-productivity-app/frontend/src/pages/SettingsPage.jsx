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
import ChangePasswordModal from '../components/modals/ChangePasswordModal';
import Enable2FAModal from '../components/modals/Enable2FAModal';
import AIProviderInfo from '../components/settings/AIProviderInfo';
import LoadingSpinner from '../components/common/LoadingSpinner';

function SettingsPage() {
  const { user, loading } = useAuth();
  const { preferences, setPreference } = useAuthStore();
  const [isChangePasswordModalOpen, setChangePasswordModalOpen] = useState(false);
  const [isEnable2FAModalOpen, setEnable2FAModalOpen] = useState(false);

  const handlePreferenceChange = (key, value) => {
    setPreference(key, value);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" label="Loading..." showLabel={true} />
      </div>
    );
  }
  if (!user) {
    // Only possible after auth check, so show nice unauthenticated UI if needed
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        Not authenticated.
      </div>
    );
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100">

      <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h1 className="text-2xl font-semibold">Settings</h1>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Manage your account preferences and application settings
            </p>
          </div>

          <div className="p-6 space-y-6">
            {/* User Preferences */}
            <div>
              <h2 className="text-lg font-medium mb-4">
                User Preferences
              </h2>

              <div className="space-y-4">
                {/* Remember Me */}
                <div className="flex items-center justify-between">
                  <div>
                    <label className="text-sm font-medium">
                      Remember Me
                    </label>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
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
                    <label className="text-sm font-medium">
                      Theme
                    </label>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Choose your preferred theme
                    </p>
                  </div>
                  <select
                    value={preferences.theme}
                    onChange={(e) => handlePreferenceChange('theme', e.target.value)}
                    className="border border-gray-300 rounded-md px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
                  >
                    <option value="light">Light</option>
                    <option value="dark">Dark</option>
                    <option value="auto">Auto</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Security Settings */}
            <div>
              <h2 className="text-lg font-medium mb-4">
                Security
              </h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <label className="text-sm font-medium">
                      Change Password
                    </label>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Update your password periodically to keep your account secure.
                    </p>
                  </div>
                  <button onClick={() => setChangePasswordModalOpen(true)} className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                    Change Password
                  </button>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <label className="text-sm font-medium">
                      Two-Factor Authentication (2FA)
                    </label>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Add an extra layer of security to your account.
                    </p>
                  </div>
                  <button onClick={() => setEnable2FAModalOpen(true)} className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                    Enable 2FA
                  </button>
                </div>
              </div>
            </div>

            {/* AI Provider Settings */}
            <AIProviderInfo />

          </div>
        </div>
      </div>

      <ChangePasswordModal isOpen={isChangePasswordModalOpen} onClose={() => setChangePasswordModalOpen(false)} />
      <Enable2FAModal isOpen={isEnable2FAModalOpen} onClose={() => setEnable2FAModalOpen(false)} />
    </div>
  );
}

export default SettingsPage;
