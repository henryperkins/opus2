/* eslint-env browser */
/* eslint-disable react-refresh/only-export-components */
/* global requestAnimationFrame */
import { useEffect, useState, useRef, useId, useCallback } from "react";
import { createPortal } from "react-dom";
import PropTypes from "prop-types";

/* ------------------------------------------------------------------------- *
 * Environment helpers
 * ------------------------------------------------------------------------- */
const isBrowser =
  typeof window !== "undefined" && typeof document !== "undefined";

/* ------------------------------------------------------------------------- *
 * Container bootstrap – only once per runtime (HMR-safe)
 * ------------------------------------------------------------------------- */
function ensureContainer() {
  if (!isBrowser) return null;

  const existing = document.getElementById("toast-container");
  if (existing) return existing;

  const el = document.createElement("div");
  el.id = "toast-container";
  el.className =
    "fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none";
  document.body.appendChild(el);
  return el;
}

const toastContainer = ensureContainer();

/* ------------------------------------------------------------------------- *
 * Public toast API
 * ------------------------------------------------------------------------- */
let nextId = 0;

function dispatchToast(detail) {
  if (!isBrowser) return; // SSR no-op
  window.dispatchEvent(new CustomEvent("show-toast", { detail }));
}

export function toast(message, options = {}) {
  const id = ++nextId;
  dispatchToast({ id, message, ...options });
}

toast.success = (msg, opts) => toast(msg, { ...opts, type: "success" });
toast.error = (msg, opts) => toast(msg, { ...opts, type: "error" });
toast.info = (msg, opts) => toast(msg, { ...opts, type: "info" });
toast.warning = (msg, opts) => toast(msg, { ...opts, type: "warning" });
toast.clearAll = () => dispatchToast({ clear: true });

/* ------------------------------------------------------------------------- *
 * ToastItem component
 * ------------------------------------------------------------------------- */
function ToastItem({ id, message, type = "info", duration = 5000, onClose }) {
  const [phase, setPhase] = useState("enter"); // enter → idle → exit
  const timer = useRef(null);
  const reactId = useId();

  const handleClose = useCallback(() => {
    clearTimeout(timer.current);
    setPhase("exit");
    setTimeout(() => onClose(id), 200);
  }, [id, onClose]);

  /* animate in + auto-dismiss ------------------------------------------------ */
  useEffect(() => {
    requestAnimationFrame(() => setPhase("idle"));
    timer.current = setTimeout(handleClose, duration);
    return () => clearTimeout(timer.current);
  }, [duration, handleClose]);

  const typeClasses = {
    success:
      "bg-green-50 dark:bg-green-900/50 text-green-800 dark:text-green-200 border-green-200 dark:border-green-800",
    error:
      "bg-red-50 dark:bg-red-900/50 text-red-800 dark:text-red-200 border-red-200 dark:border-red-800",
    warning:
      "bg-yellow-50 dark:bg-yellow-900/50 text-yellow-800 dark:text-yellow-200 border-yellow-200 dark:border-yellow-800",
    info: "bg-blue-50 dark:bg-blue-900/50 text-blue-800 dark:text-blue-200 border-blue-200 dark:border-blue-800",
  };

  const icons = {
    success: (
      <svg
        className="w-5 h-5"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M5 13l4 4L19 7"
        />
      </svg>
    ),
    error: (
      <svg
        className="w-5 h-5"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M6 18L18 6M6 6l12 12"
        />
      </svg>
    ),
    warning: (
      <svg
        className="w-5 h-5"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
        />
      </svg>
    ),
    info: (
      <svg
        className="w-5 h-5"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
    ),
  };

  return (
    <div
      key={reactId}
      role="alert"
      aria-live="polite"
      className={`
        pointer-events-auto flex items-center gap-3 p-4 rounded-lg border shadow-lg
        transform transition-all duration-200
        ${typeClasses[type]}
        ${
          phase === "enter"
            ? "translate-x-full opacity-0"
            : phase === "idle"
              ? "translate-x-0 opacity-100"
              : "translate-x-full opacity-0"
        }
      `}
    >
      <div className="shrink-0">{icons[type]}</div>
      <p className="text-sm font-medium">{message}</p>
      <button
        onClick={handleClose}
        className="shrink-0 ml-4 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
        aria-label="Close notification"
        type="button"
      >
        <svg
          className="w-4 h-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      </button>
    </div>
  );
}

ToastItem.propTypes = {
  id: PropTypes.number.isRequired,
  message: PropTypes.string.isRequired,
  type: PropTypes.oneOf(["success", "error", "warning", "info"]),
  duration: PropTypes.number,
  onClose: PropTypes.func.isRequired,
};

/* ------------------------------------------------------------------------- *
 * ToastContainer — one per app
 * ------------------------------------------------------------------------- */
export function ToastContainer() {
  const [toasts, setToasts] = useState([]);

  useEffect(() => {
    if (!isBrowser) return () => {};

    const handler = (evt) => {
      if (evt.detail?.clear) return setToasts([]);
      setToasts((prev) => [...prev, evt.detail]);
    };
    window.addEventListener("show-toast", handler);
    return () => window.removeEventListener("show-toast", handler);
  }, []);

  const removeToast = (id) =>
    setToasts((prev) => prev.filter((t) => t.id !== id));

  if (!toastContainer) return null; // SSR safety

  return createPortal(
    <>
      {toasts.map((t) => (
        <ToastItem key={t.id} {...t} onClose={removeToast} />
      ))}
    </>,
    toastContainer,
  );
}
