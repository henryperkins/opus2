// frontend/src/pages/UnifiedSettingsPage.jsx
import React, { useState, useMemo, useCallback } from "react";
import {
  User,
  Shield,
  Palette,
  Bell,
  Code,
  Database,
  Brain,
  Wrench,
  Eye,
  EyeOff,
} from "lucide-react";

import { toast } from "../components/common/Toast";
import UnifiedModal from "../components/common/UnifiedModal";
import UnifiedAISettings from "../components/settings/UnifiedAISettings";
import ToolUsagePanel from "../components/chat/ToolUsagePanel";

import { useAuth } from "../hooks/useAuth";
import { authAPI } from "../api/auth";
import useAuthStore from "../stores/authStore";

import { NavigationManager } from "../utils/navigation";
import { useNavigation } from "../contexts/NavigationContext";

const NAV_SECTIONS = [
  { id: "profile", label: "Profile", icon: User },
  { id: "security", label: "Security", icon: Shield },
  { id: "appearance", label: "Appearance", icon: Palette },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "models", label: "AI Models", icon: Code },
  { id: "thinking", label: "Thinking & Tools", icon: Brain },
  { id: "data", label: "Data & Privacy", icon: Database },
];

/* ---------------------------------------------------------------------- */
/* MAIN PAGE                                                              */
/* ---------------------------------------------------------------------- */
export default function UnifiedSettingsPage() {
  /* ------------------------------- global state ---------------------- */
  const { user } = useAuth();
  const { getActiveStyles } = useNavigation();
  const { preferences, setPreference } = useAuthStore();

  /* ------------------------------- local UI state -------------------- */
  const [active, setActive] = useState("profile");
  const [showPwModal, setShowPwModal] = useState(false);

  /* Demo state for ToolUsagePanel */
  const [enabledTools, setEnabledTools] = useState([
    "file_search",
    "explain_code",
    "comprehensive_analysis",
  ]);
  const [recentToolCalls, setRecentToolCalls] = useState([]);

  /* ------------------------------- section renderer ------------------ */
  const sectionContent = useMemo(() => {
    switch (active) {
      case "profile":
        return <ProfileSettings user={user} />;
      case "security":
        return <SecuritySettings onChangePassword={() => setShowPwModal(true)} />;
      case "appearance":
        return (
          <AppearanceSettings
            preferences={preferences}
            setPreference={setPreference}
          />
        );
      case "notifications":
        return (
          <NotificationSettings
            preferences={preferences}
            setPreference={setPreference}
          />
        );
      case "models":
        return <UnifiedAISettings />;
      case "thinking":
        return (
          <>
            <div className="text-center text-gray-500 py-8">
              Thinking & tools settings are consolidated into the “AI Models” tab.
            </div>

            <ToolUsagePanel
              enabledTools={enabledTools}
              onToolToggle={(toolId, enabled) =>
                setEnabledTools((prev) =>
                  enabled ? [...prev, toolId] : prev.filter((id) => id !== toolId),
                )
              }
              recentToolCalls={recentToolCalls}
              onRunTool={(toolId) =>
                setRecentToolCalls((prev) => [
                  {
                    toolId,
                    toolName: toolId.replace(/_/g, " "),
                    status: "success",
                    duration: Math.random() * 2500 + 500,
                    timestamp: new Date().toISOString(),
                  },
                  ...prev.slice(0, 9),
                ])
              }
            />
          </>
        );
      case "data":
        return <DataPrivacySettings />;
      default:
        return null;
    }
  }, [active, user, preferences, setPreference, enabledTools, recentToolCalls]);

  /* ------------------------------- render ---------------------------- */
  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
      <div className="flex gap-8">
        {/* Navigation */}
        <nav className="w-64 shrink-0">
          <ul className="space-y-1">
            {NAV_SECTIONS.map(({ id, label, icon: Icon }) => {
              const activeStyles = NavigationManager.getActiveStyles(
                active === id,
                "sidebar",
              );
              return (
                <li key={id}>
                  <button
                    onClick={() => setActive(id)}
                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm ${activeStyles}`}
                  >
                    <Icon className="w-4 h-4" />
                    {label}
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Content */}
        <div className="flex-1 bg-white dark:bg-gray-800 rounded-lg shadow">
          <div className="p-6">{sectionContent}</div>
        </div>
      </div>

      {/* Password modal */}
      {showPwModal && (
        <PasswordChangeModal isOpen={showPwModal} onClose={() => setShowPwModal(false)} />
      )}
    </div>
  );
}

/* ---------------------------------------------------------------------- */
/* PROFILE                                                                */
/* ---------------------------------------------------------------------- */
function ProfileSettings({ user }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({
    name: user?.name ?? "",
    bio: user?.bio ?? "",
  });

  const save = async () => {
    try {
      await authAPI.updateProfile(form);
      toast.success("Profile updated");
      setEditing(false);
    } catch (e) {
      toast.error("Update failed");
    }
  };

  return (
    <div>
      <h2 className="text-2xl font-semibold mb-6">Profile Settings</h2>

      <div className="space-y-6">
        {/* Name */}
        <div>
          <label className="block text-sm font-medium mb-2">Full name</label>
          {editing ? (
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="input"
            />
          ) : (
            <p>{user?.name || "—"}</p>
          )}
        </div>

        {/* Email (read-only) */}
        <div>
          <label className="block text-sm font-medium mb-2">Email address</label>
          <p>{user?.email}</p>
          <p className="text-sm text-gray-500">Contact support to change email.</p>
        </div>

        {/* Bio */}
        <div>
          <label className="block text-sm font-medium mb-2">Bio</label>
          {editing ? (
            <textarea
              rows={3}
              value={form.bio}
              onChange={(e) => setForm({ ...form, bio: e.target.value })}
              className="input"
            />
          ) : (
            <p>{user?.bio || "No bio set"}</p>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          {editing ? (
            <>
              <button onClick={save} className="btn-primary">
                Save
              </button>
              <button onClick={() => setEditing(false)} className="btn-secondary">
                Cancel
              </button>
            </>
          ) : (
            <button onClick={() => setEditing(true)} className="btn-primary">
              Edit profile
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------- */
/* SECURITY                                                               */
/* ---------------------------------------------------------------------- */
function SecuritySettings({ onChangePassword }) {
  return (
    <div>
      <h2 className="text-2xl font-semibold mb-6">Security Settings</h2>

      <div className="space-y-6">
        <div className="border p-4 rounded-lg">
          <h3 className="text-lg font-medium mb-2">Password</h3>
          <p className="text-sm text-gray-600 mb-4">
            Update your password regularly to keep your account secure.
          </p>
          <button onClick={onChangePassword} className="btn-primary">
            Change password
          </button>
        </div>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------- */
/* APPEARANCE                                                             */
/* ---------------------------------------------------------------------- */
function AppearanceSettings({ preferences, setPreference }) {
  return (
    <div>
      <h2 className="text-2xl font-semibold mb-6">Appearance</h2>

      <div className="space-y-6">
        {/* Theme */}
        <div>
          <label className="block text-sm font-medium mb-3">Theme</label>
          {["light", "dark", "auto"].map((t) => (
            <label key={t} className="flex items-center gap-2 mb-1">
              <input
                type="radio"
                name="theme"
                value={t}
                checked={preferences.theme === t}
                onChange={(e) => setPreference("theme", e.target.value)}
              />
              <span className="capitalize">{t}</span>
            </label>
          ))}
        </div>

        {/* Sidebar pinned */}
        <div>
          <label className="flex items-center justify-between">
            <span className="text-sm font-medium">Sidebar pinned</span>
            <input
              type="checkbox"
              checked={preferences.sidebarPinned}
              onChange={(e) => setPreference("sidebarPinned", e.target.checked)}
            />
          </label>
        </div>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------- */
/* NOTIFICATIONS                                                          */
/* ---------------------------------------------------------------------- */
function NotificationSettings({ preferences, setPreference }) {
  return (
    <div>
      <h2 className="text-2xl font-semibold mb-6">Notifications</h2>

      <div className="space-y-6">
        <label className="flex items-center justify-between">
          <span>Email notifications</span>
          <input
            type="checkbox"
            checked={preferences.emailNotifications}
            onChange={(e) => setPreference("emailNotifications", e.target.checked)}
          />
        </label>

        <label className="flex items-center justify-between">
          <span>Push notifications</span>
          <input
            type="checkbox"
            checked={preferences.pushNotifications}
            onChange={(e) => setPreference("pushNotifications", e.target.checked)}
          />
        </label>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------- */
/* DATA                                                                   */
/* ---------------------------------------------------------------------- */
function DataPrivacySettings() {
  return (
    <div>
      <h2 className="text-2xl font-semibold mb-6">Data & Privacy</h2>

      <div className="space-y-6">
        <div className="border p-4 rounded-lg">
          <h3 className="text-lg font-medium mb-2">Data export</h3>
          <p className="text-sm text-gray-600 mb-4">
            Download a copy of your data including projects and chats.
          </p>
          <button className="btn-primary">Export data</button>
        </div>

        <div className="border p-4 rounded-lg border-red-300">
          <h3 className="text-lg font-medium text-red-700 mb-2">Delete account</h3>
          <p className="text-sm text-red-600 mb-4">
            Permanently delete your account and all data. This action cannot be undone.
          </p>
          <button className="btn-danger">Delete account</button>
        </div>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------- */
/* PASSWORD MODAL                                                         */
/* ---------------------------------------------------------------------- */
function PasswordChangeModal({ isOpen, onClose }) {
  const [form, setForm] = useState({
    current: "",
    next: "",
    confirm: "",
  });
  const [show, setShow] = useState({ current: false, next: false, confirm: false });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (form.next !== form.confirm) {
      setError("Passwords do not match");
      return;
    }
    if (form.next.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    setLoading(true);
    try {
      await authAPI.updateProfile({
        current_password: form.current,
        password: form.next,
      });
      toast.success("Password changed");
      onClose();
    } catch {
      setError("Incorrect current password");
    } finally {
      setLoading(false);
    }
  };

  const toggleShow = (k) => setShow((p) => ({ ...p, [k]: !p[k] }));

  return (
    <UnifiedModal
      isOpen={isOpen}
      onClose={onClose}
      title="Change password"
      actions={
        <>
          <button onClick={onClose} className="btn-secondary">
            Cancel
          </button>
          <button type="submit" form="pw-form" disabled={loading} className="btn-primary">
            {loading ? "Changing…" : "Change password"}
          </button>
        </>
      }
    >
      <form id="pw-form" onSubmit={submit} className="space-y-4">
        {["current", "next", "confirm"].map((field, idx) => (
          <div key={field}>
            <label className="block text-sm font-medium mb-2">
              {idx === 0 ? "Current password" : idx === 1 ? "New password" : "Confirm new password"}
            </label>
            <div className="relative">
              <input
                type={show[field] ? "text" : "password"}
                value={form[field]}
                onChange={(e) => setForm({ ...form, [field]: e.target.value })}
                className="input pr-10"
                required
              />
              <button
                type="button"
                onClick={() => toggleShow(field)}
                className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400"
              >
                {show[field] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>
        ))}

        {error && <p className="text-sm text-red-600">{error}</p>}
      </form>
    </UnifiedModal>
  );
}

/* ---------------------------------------------------------------------- */
/* Utility button classes (Tailwind)                                      */
/* ---------------------------------------------------------------------- */
const btnBase = "px-4 py-2 rounded-md focus:outline-none";
const BTN = {
  primary: `${btnBase} bg-blue-600 text-white hover:bg-blue-700`,
  secondary: `${btnBase} bg-gray-200 dark:bg-gray-600 text-gray-800 dark:text-gray-100`,
  danger: `${btnBase} bg-red-600 text-white hover:bg-red-700`,
};

/* quick Tailwind shortcuts */
window.btnPrimary = BTN.primary;
window.btnSecondary = BTN.secondary;
window.btnDanger = BTN.danger;
