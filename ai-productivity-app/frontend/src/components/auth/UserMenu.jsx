/* UserMenu Component
 *
 * Purpose
 * -------
 * Dropdown menu for authenticated users showing:
 *  • User info display (username, email)
 *  • Profile management link
 *  • Logout functionality
 *  • Last login timestamp
 *
 * Used in the main application header for authenticated users.
 */

import { useState, useRef, useEffect } from "react";
import { useAuth } from "../../hooks/useAuth";
import { Link } from "react-router-dom";
import useAuthStore from "../../stores/authStore";

function UserMenu() {
  const { user, loading, logout } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef(null);
  const { getLastLoginInfo } = useAuthStore();

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = async () => {
    try {
      await logout();
      setIsOpen(false);
    } catch (error) {
      console.error("Logout failed:", error);
    }
  };

  // Guard: show skeleton/avatar placeholder if loading
  if (loading) {
    // Replace this with a nice SkeletonAvatar if you have one:
    return (
      <div
        className="w-8 h-8 bg-gray-200 rounded-full animate-pulse"
        data-testid="skeleton-avatar"
      ></div>
    );
  }

  // Not logged in: render nothing
  if (!user) return null;

  const lastLoginInfo = getLastLoginInfo();

  // Simplified, type-safe display name and initial
  // Defensive fallback: ensure displayName/string access is always safe
  let displayName = "";
  if (
    user &&
    user.username &&
    typeof user.username === "string" &&
    user.username.trim()
  ) {
    displayName = user.username.trim();
  } else if (
    user &&
    user.email &&
    typeof user.email === "string" &&
    user.email.trim()
  ) {
    displayName = user.email.trim();
  } else {
    displayName = "User";
  }
  // Avoid use of charAt, [0], or any direct string index unless proven safe
  let firstInitial = "U";
  if (
    typeof displayName === "string" &&
    displayName &&
    displayName.trim().length > 0
  ) {
    try {
      const trimmed = displayName.trim();
      if (trimmed.length > 0) {
        firstInitial = trimmed.slice(0, 1).toUpperCase();
        if (!firstInitial || !firstInitial.match(/[A-Z0-9]/i)) {
          firstInitial = "U";
        }
      }
    } catch (error) {
      console.warn("Error processing user initial:", error);
      firstInitial = "U";
    }
  }

  return (
    <div className="relative" ref={menuRef}>
      {/* User Avatar/Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 text-gray-700 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-md p-1"
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        <div className="w-8 h-8 bg-brand-primary-600 rounded-full flex items-center justify-center text-white text-sm font-medium">
          {firstInitial}
        </div>
        <span className="hidden md:block text-sm font-medium">
          {displayName}
        </span>
        <svg
          className={`w-4 h-4 transition-transform duration-200 ${
            isOpen ? "rotate-180" : ""
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 bg-white rounded-md shadow-lg ring-1 ring-black/5 focus:outline-none z-50">
          <div className="py-1" role="menu" aria-orientation="vertical">
            {/* User Info Header */}
            <div className="px-4 py-3 border-b border-gray-100">
              <p className="text-sm font-medium text-gray-900">
                {user?.username || "Username not available"}
              </p>
              <p className="text-sm text-gray-500">
                {user?.email || "Email not available"}
              </p>
              {lastLoginInfo?.timestamp && (
                <p className="text-xs text-gray-400 mt-1">
                  Last login:{" "}
                  {new Date(lastLoginInfo.timestamp).toLocaleString()}
                </p>
              )}
            </div>

            {/* Menu Items */}
            <div className="py-1">
              <Link
                to="/profile"
                className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                role="menuitem"
                onClick={() => setIsOpen(false)}
              >
                <div className="flex items-center">
                  <svg
                    className="w-4 h-4 mr-3"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                    />
                  </svg>
                  User Profile
                </div>
              </Link>

              <Link
                to="/settings"
                className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                role="menuitem"
                onClick={() => setIsOpen(false)}
              >
                <div className="flex items-center">
                  <svg
                    className="w-4 h-4 mr-3"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                    />
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                    />
                  </svg>
                  Settings
                </div>
              </Link>
            </div>

            {/* Logout */}
            <div className="border-t border-gray-100">
              <button
                onClick={handleLogout}
                className="block w-full text-left px-4 py-2 text-sm text-red-700 hover:bg-red-50 hover:text-red-900"
                role="menuitem"
              >
                <div className="flex items-center">
                  <svg
                    className="w-4 h-4 mr-3"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                    />
                  </svg>
                  Sign out
                </div>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default UserMenu;
