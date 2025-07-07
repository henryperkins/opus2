import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useNavigation } from '../contexts/NavigationContext';
import { NavigationManager } from '../utils/navigation';
import UnifiedModal from '../components/common/UnifiedModal';
import ModelConfiguration from '../components/settings/ModelConfiguration';
import AIProviderInfo from '../components/settings/AIProviderInfo';
import ThinkingConfiguration from '../components/settings/ThinkingConfiguration';
import ToolUsagePanel from '../components/chat/ToolUsagePanel';
import useAuthStore from '../stores/authStore';
import { authAPI } from '../api/auth';
import { toast } from '../components/common/Toast';
import { User, Shield, Palette, Bell, Code, Database, Eye, EyeOff, Brain, Wrench } from 'lucide-react';

const SETTINGS_SECTIONS = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'security', label: 'Security', icon: Shield },
  { id: 'appearance', label: 'Appearance', icon: Palette },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'models', label: 'AI Models', icon: Code },
  { id: 'thinking', label: 'Thinking & Tools', icon: Brain },
  { id: 'data', label: 'Data & Privacy', icon: Database }
];

export default function UnifiedSettingsPage() {
  const { user } = useAuth();
  const { getActiveStyles } = useNavigation();
  const { preferences, setPreference } = useAuthStore();
  const [activeSection, setActiveSection] = useState('profile');
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [show2FAModal, setShow2FAModal] = useState(false);
  const [enabledTools, setEnabledTools] = useState(['file_search', 'explain_code', 'comprehensive_analysis']);
  const [recentToolCalls, setRecentToolCalls] = useState([]);

  const renderSectionContent = () => {
    switch (activeSection) {
      case 'profile':
        return <ProfileSettings user={user} />;
      case 'security':
        return (
          <SecuritySettings
            onChangePassword={() => setShowPasswordModal(true)}
            onEnable2FA={() => setShow2FAModal(true)}
          />
        );
      case 'appearance':
        return <AppearanceSettings preferences={preferences} setPreference={setPreference} />;
      case 'notifications':
        return <NotificationSettings preferences={preferences} setPreference={setPreference} />;
      case 'models':
        return (
          <div>
            <h2 className="text-2xl font-semibold mb-6 text-gray-900 dark:text-gray-100">AI Models</h2>
            <ModelConfiguration />
            <div className="mt-8">
              <AIProviderInfo />
            </div>
          </div>
        );
      case 'thinking':
        return (
          <div className="space-y-8">
            <ThinkingConfiguration />
            <div className="border-t border-gray-200 pt-8">
              <div className="flex items-center gap-3 mb-6">
                <Wrench className="h-6 w-6 text-blue-500" />
                <h2 className="text-xl font-semibold text-gray-900">Tool Management</h2>
              </div>
              <ToolUsagePanel
                enabledTools={enabledTools}
                onToolToggle={(toolId, enabled) => {
                  if (enabled) {
                    setEnabledTools(prev => [...prev, toolId]);
                  } else {
                    setEnabledTools(prev => prev.filter(id => id !== toolId));
                  }
                }}
                recentToolCalls={recentToolCalls}
                onRunTool={(toolId) => {
                  console.log('Running tool:', toolId);
                  // Add test tool call to recent calls
                  const testCall = {
                    toolId,
                    toolName: toolId.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
                    description: 'Test execution',
                    status: 'success',
                    duration: Math.random() * 3000 + 500,
                    timestamp: new Date().toISOString()
                  };
                  setRecentToolCalls(prev => [testCall, ...prev.slice(0, 9)]);
                }}
                compact={false}
              />
            </div>
          </div>
        );
      case 'data':
        return <DataPrivacySettings />;
      default:
        return null;
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex gap-8">
        {/* Settings Navigation */}
        <nav className="w-64 flex-shrink-0">
          <ul className="space-y-1">
            {SETTINGS_SECTIONS.map(section => {
              const Icon = section.icon;
              const isActive = activeSection === section.id;
              return (
                <li key={section.id}>
                  <button
                    onClick={() => setActiveSection(section.id)}
                    className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      NavigationManager.getActiveStyles(isActive, 'sidebar')
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{section.label}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Settings Content */}
        <div className="flex-1 bg-white dark:bg-gray-800 rounded-lg shadow">
          <div className="p-6">
            {renderSectionContent()}
          </div>
        </div>
      </div>

      {/* Modals */}
      {showPasswordModal && (
        <PasswordChangeModal
          isOpen={showPasswordModal}
          onClose={() => setShowPasswordModal(false)}
        />
      )}
    </div>
  );
}

// Settings section components
function ProfileSettings({ user }) {
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({
    name: user?.name || '',
    email: user?.email || '',
    bio: user?.bio || ''
  });

  const handleSave = async () => {
    try {
      await authAPI.updateProfile(formData);
      toast.success('Profile updated successfully');
      setIsEditing(false);
    } catch (error) {
      toast.error('Failed to update profile');
      console.error('Profile update error:', error);
    }
  };

  return (
    <div>
      <h2 className="text-2xl font-semibold mb-6 text-gray-900 dark:text-gray-100">Profile Settings</h2>
      
      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Full Name
          </label>
          {isEditing ? (
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            />
          ) : (
            <p className="text-gray-900 dark:text-gray-100">{user?.name || 'Not set'}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Email Address
          </label>
          <p className="text-gray-900 dark:text-gray-100">{user?.email}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Contact support to change your email address
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Bio
          </label>
          {isEditing ? (
            <textarea
              value={formData.bio}
              onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
              rows={3}
              className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              placeholder="Tell us about yourself..."
            />
          ) : (
            <p className="text-gray-900 dark:text-gray-100">{user?.bio || 'No bio set'}</p>
          )}
        </div>

        <div className="flex space-x-3">
          {isEditing ? (
            <>
              <button
                onClick={handleSave}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                Save Changes
              </button>
              <button
                onClick={() => setIsEditing(false)}
                className="px-4 py-2 bg-gray-300 dark:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-md hover:bg-gray-400 dark:hover:bg-gray-500"
              >
                Cancel
              </button>
            </>
          ) : (
            <button
              onClick={() => setIsEditing(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              Edit Profile
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function SecuritySettings({ onChangePassword, onEnable2FA }) {
  return (
    <div>
      <h2 className="text-2xl font-semibold mb-6 text-gray-900 dark:text-gray-100">Security Settings</h2>
      
      <div className="space-y-6">
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">Password</h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Update your password regularly to keep your account secure.
          </p>
          <button
            onClick={onChangePassword}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            Change Password
          </button>
        </div>

        <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">Two-Factor Authentication</h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Add an extra layer of security to your account with 2FA.
          </p>
          <button
            onClick={onEnable2FA}
            className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500"
          >
            Enable 2FA
          </button>
        </div>

        <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">Active Sessions</h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Monitor and manage your active login sessions.
          </p>
          <button className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500">
            View Sessions
          </button>
        </div>
      </div>
    </div>
  );
}

function AppearanceSettings({ preferences, setPreference }) {
  return (
    <div>
      <h2 className="text-2xl font-semibold mb-6 text-gray-900 dark:text-gray-100">Appearance</h2>
      
      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
            Theme
          </label>
          <div className="space-y-2">
            {['light', 'dark', 'auto'].map(theme => (
              <label key={theme} className="flex items-center">
                <input
                  type="radio"
                  name="theme"
                  value={theme}
                  checked={preferences.theme === theme}
                  onChange={(e) => setPreference('theme', e.target.value)}
                  className="mr-3 text-blue-600"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300 capitalize">
                  {theme}
                </span>
              </label>
            ))}
          </div>
        </div>

        <div>
          <label className="flex items-center justify-between">
            <div>
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Sidebar Pinned
              </span>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Keep the sidebar open by default
              </p>
            </div>
            <input
              type="checkbox"
              checked={preferences.sidebarPinned}
              onChange={(e) => setPreference('sidebarPinned', e.target.checked)}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
          </label>
        </div>
      </div>
    </div>
  );
}

function NotificationSettings({ preferences, setPreference }) {
  return (
    <div>
      <h2 className="text-2xl font-semibold mb-6 text-gray-900 dark:text-gray-100">Notifications</h2>
      
      <div className="space-y-6">
        <div>
          <label className="flex items-center justify-between">
            <div>
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Email Notifications
              </span>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Receive updates via email
              </p>
            </div>
            <input
              type="checkbox"
              checked={preferences.emailNotifications}
              onChange={(e) => setPreference('emailNotifications', e.target.checked)}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
          </label>
        </div>

        <div>
          <label className="flex items-center justify-between">
            <div>
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Push Notifications
              </span>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Receive browser notifications
              </p>
            </div>
            <input
              type="checkbox"
              checked={preferences.pushNotifications}
              onChange={(e) => setPreference('pushNotifications', e.target.checked)}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
          </label>
        </div>
      </div>
    </div>
  );
}

function DataPrivacySettings() {
  return (
    <div>
      <h2 className="text-2xl font-semibold mb-6 text-gray-900 dark:text-gray-100">Data & Privacy</h2>
      
      <div className="space-y-6">
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">Data Export</h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Download a copy of your data including projects, chats, and files.
          </p>
          <button className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">
            Export Data
          </button>
        </div>

        <div className="border border-red-200 dark:border-red-700 rounded-lg p-4">
          <h3 className="text-lg font-medium text-red-900 dark:text-red-100 mb-2">Delete Account</h3>
          <p className="text-sm text-red-600 dark:text-red-400 mb-4">
            Permanently delete your account and all associated data. This action cannot be undone.
          </p>
          <button className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700">
            Delete Account
          </button>
        </div>
      </div>
    </div>
  );
}

// Password Change Modal Component
function PasswordChangeModal({ isOpen, onClose }) {
  const [formData, setFormData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });
  const [showPasswords, setShowPasswords] = useState({
    current: false,
    new: false,
    confirm: false
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (formData.newPassword !== formData.confirmPassword) {
      setError('New passwords do not match');
      return;
    }

    if (formData.newPassword.length < 8) {
      setError('New password must be at least 8 characters');
      return;
    }

    setLoading(true);
    try {
      await authAPI.updateProfile({
        current_password: formData.currentPassword,
        password: formData.newPassword
      });
      toast.success('Password changed successfully');
      onClose();
    } catch (error) {
      setError('Failed to change password. Please check your current password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <UnifiedModal
      isOpen={isOpen}
      onClose={onClose}
      title="Change Password"
      actions={
        <>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-md"
          >
            Cancel
          </button>
          <button
            type="submit"
            form="password-form"
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Changing...' : 'Change Password'}
          </button>
        </>
      }
    >
      <form id="password-form" onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Current Password
          </label>
          <div className="relative">
            <input
              type={showPasswords.current ? 'text' : 'password'}
              value={formData.currentPassword}
              onChange={(e) => setFormData({ ...formData, currentPassword: e.target.value })}
              className="block w-full px-3 py-2 pr-10 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              required
            />
            <button
              type="button"
              onClick={() => setShowPasswords({ ...showPasswords, current: !showPasswords.current })}
              className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
            >
              {showPasswords.current ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            New Password
          </label>
          <div className="relative">
            <input
              type={showPasswords.new ? 'text' : 'password'}
              value={formData.newPassword}
              onChange={(e) => setFormData({ ...formData, newPassword: e.target.value })}
              className="block w-full px-3 py-2 pr-10 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              required
            />
            <button
              type="button"
              onClick={() => setShowPasswords({ ...showPasswords, new: !showPasswords.new })}
              className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
            >
              {showPasswords.new ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Confirm New Password
          </label>
          <div className="relative">
            <input
              type={showPasswords.confirm ? 'text' : 'password'}
              value={formData.confirmPassword}
              onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
              className="block w-full px-3 py-2 pr-10 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              required
            />
            <button
              type="button"
              onClick={() => setShowPasswords({ ...showPasswords, confirm: !showPasswords.confirm })}
              className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
            >
              {showPasswords.confirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {error && (
          <div className="text-sm text-red-600 dark:text-red-400">
            {error}
          </div>
        )}
      </form>
    </UnifiedModal>
  );
}