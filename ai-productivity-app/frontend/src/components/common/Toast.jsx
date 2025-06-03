import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import PropTypes from 'prop-types';

// We create a container the first time this module is evaluated so it exists
// before any toasts are rendered.
const toastContainer = document.createElement('div');
toastContainer.id = 'toast-container';
toastContainer.className =
  'fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none';
if (typeof document !== 'undefined') {
  document.body.appendChild(toastContainer);
}

let nextId = 0;

// ---------------------------------------------------------------------------------------------
// Public API – `toast()` helper & convenience shortcuts.
// ---------------------------------------------------------------------------------------------

export function toast(message, options = {}) {
  const id = ++nextId;
  const event = new CustomEvent('show-toast', {
    detail: { id, message, ...options },
  });
  window.dispatchEvent(event);
}

toast.success = (message, options) => toast(message, { ...options, type: 'success' });
toast.error = (message, options) => toast(message, { ...options, type: 'error' });
toast.info = (message, options) => toast(message, { ...options, type: 'info' });
toast.warning = (message, options) => toast(message, { ...options, type: 'warning' });

// ---------------------------------------------------------------------------------------------
// Toast item component
// ---------------------------------------------------------------------------------------------

function ToastItem({ id, message, type = 'info', duration = 5000, onClose }) {
  const [isVisible, setIsVisible] = useState(false);
  const [isExiting, setIsExiting] = useState(false);

  // Trigger entrance + auto-dismiss -----------------------------------------------------------
  useEffect(() => {
    requestAnimationFrame(() => setIsVisible(true));

    const timer = setTimeout(() => {
      handleClose();
    }, duration);

    return () => clearTimeout(timer);
  }, [duration]);

  const handleClose = () => {
    setIsExiting(true);
    setTimeout(() => onClose(id), 200);
  };

  const typeClasses = {
    success:
      'bg-green-50 dark:bg-green-900/50 text-green-800 dark:text-green-200 border-green-200 dark:border-green-800',
    error:
      'bg-red-50 dark:bg-red-900/50 text-red-800 dark:text-red-200 border-red-200 dark:border-red-800',
    warning:
      'bg-yellow-50 dark:bg-yellow-900/50 text-yellow-800 dark:text-yellow-200 border-yellow-200 dark:border-yellow-800',
    info: 'bg-blue-50 dark:bg-blue-900/50 text-blue-800 dark:text-blue-200 border-blue-200 dark:border-blue-800',
  };

  const icons = {
    success: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
    ),
    error: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
      </svg>
    ),
    warning: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
        />
      </svg>
    ),
    info: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  };

  return (
    <div
      role="alert"
      aria-live="polite"
      className={`pointer-events-auto flex items-center gap-3 p-4 rounded-lg border shadow-lg transform transition-all duration-200 ${
        typeClasses[type]
      } ${isVisible && !isExiting ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'}`}
    >
      <div className="flex-shrink-0">{icons[type]}</div>
      <p className="text-sm font-medium">{message}</p>
      <button
        onClick={handleClose}
        className="flex-shrink-0 ml-4 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
        aria-label="Close notification"
        type="button"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}

ToastItem.propTypes = {
  id: PropTypes.number.isRequired,
  message: PropTypes.string.isRequired,
  type: PropTypes.oneOf(['success', 'error', 'warning', 'info']),
  duration: PropTypes.number,
  onClose: PropTypes.func.isRequired,
};

// ---------------------------------------------------------------------------------------------
// Toast container – listens for `show-toast` events.
// ---------------------------------------------------------------------------------------------

export function ToastContainer() {
  const [toasts, setToasts] = useState([]);

  useEffect(() => {
    const handle = (event) => {
      setToasts((prev) => [...prev, event.detail]);
    };
    window.addEventListener('show-toast', handle);
    return () => window.removeEventListener('show-toast', handle);
  }, []);

  const removeToast = (id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return createPortal(
    <>
      {toasts.map((t) => (
        <ToastItem key={t.id} {...t} onClose={removeToast} />
      ))}
    </>,
    toastContainer
  );
}
