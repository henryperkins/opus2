// Axios instance with auth + CSRF handling
//
// Purpose
// -------
// Centralised HTTP client used by all frontend API modules.
//  • Automatically attaches JWT cookie (withCredentials).
//  • Adds CSRF header for mutating requests using token from `csrftoken` cookie.
//  • Intercepts 401/419 responses – clears auth state and redirects to /login.
//  • Implements basic exponential-backoff retry for transient 5xx failures.
//
// NOTE: This file is the first step of the Phase-2 frontend auth layer.
// Subsequent commits will add AuthContext, hooks, components, tests.

import axios from 'axios';

// -----------------------------------------------------------------------------
// Configuration
// -----------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Backend base URL
// ---------------------------------------------------------------------------
// 1. Use the explicit Vite env variable when provided (works with Docker-compose
//    where `VITE_API_URL` is injected).
// 2. Fallback to the conventional local development port `8000` so that a
//    plain `npm run dev` without env-vars still points towards the FastAPI
//    server.  The previous empty string made the requests *relative* to the
//    Vite origin (5173) which breaks unless a dev-proxy is configured.

// Determine base URL based on environment
const getBaseURL = () => {
  // If explicitly set via env var, use it
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  
  // Production: use HTTPS and same domain
  if (import.meta.env.PROD) {
    return `${window.location.protocol}//${window.location.host}/api`;
  }
  
  // Development fallback
  return 'http://localhost:8000';
};

const BASE_URL = getBaseURL();

const client = axios.create({
  baseURL: BASE_URL,
  withCredentials: true, // send/receive HttpOnly cookies
  timeout: 30_000,
});

// -----------------------------------------------------------------------------
// CSRF helper
// -----------------------------------------------------------------------------

function getCookie(name) {
  const match = document.cookie.match(
    new RegExp('(^| )' + name + '=([^;]+)')
  );
  return match ? decodeURIComponent(match[2]) : null;
}

function attachCsrf(config) {
  const csrfToken = getCookie('csrftoken');
  const mutating = ['post', 'put', 'patch', 'delete'];
  if (csrfToken && mutating.includes(config.method)) {
    config.headers['X-CSRFToken'] = csrfToken;
  }
  return config;
}

// -----------------------------------------------------------------------------
// Retry helper (exponential back-off up to 3 attempts)
// -----------------------------------------------------------------------------

async function retryRequest(error) {
  const cfg = error.config;
  if (!cfg || cfg.__retryCount >= 3 || !error.response) {
    return Promise.reject(error);
  }
  const { status } = error.response;
  if (status >= 500 && status < 600) {
    cfg.__retryCount = (cfg.__retryCount || 0) + 1;
    const delay = 2 ** cfg.__retryCount * 100; // 100, 200, 400ms
    await new Promise((r) => setTimeout(r, delay));
    return client(cfg);
  }
  return Promise.reject(error);
}

// -----------------------------------------------------------------------------
// Interceptors
// -----------------------------------------------------------------------------

client.interceptors.request.use(attachCsrf);

client.interceptors.response.use(
  (resp) => resp,
  async (error) => {
    const { response } = error;

    // Handle auth errors globally
    if (response && response.status === 401) {
      // Clear local user state and redirect to login (AuthContext will listen)
      window.dispatchEvent(new CustomEvent('auth:logout'));
    }

    // Provide clearer messages for backend availability issues
    if (response && response.status === 503) {
      // Service unavailable – often database down or migrations pending
      error.message =
        'Service temporarily unavailable. Please ensure the backend and database are running.';
    }

    // ---------------------------------------------------------------------
    // FastAPI validation errors come back as an array of objects under
    // `response.data.detail` – e.g. `[{loc: [...], msg: 'field required', ...}]`.
    // Trying to render this object directly in React results in the
    // "Objects are not valid as a React child" runtime error.
    //
    // To provide a smoother developer- and user-experience we convert those
    // structures into a readable string right here in the centralised Axios
    // interceptor.  That way every consumer that relies on
    // `err.response?.data?.detail` will automatically receive a display-safe
    // string without having to duplicate this logic in many places.
    // ---------------------------------------------------------------------

    if (response && response.data && response.data.detail) {
      const { detail } = response.data;

      // Case 1: Array of validation error objects
      if (Array.isArray(detail)) {
        // Collect human-readable messages, prefer the `msg` field, fall back to JSON stringification
        const messages = detail
          .map((item) => {
            if (typeof item === 'string') return item;
            if (item && typeof item === 'object' && 'msg' in item) return item.msg;
            try {
              return JSON.stringify(item);
            } catch {
              return String(item);
            }
          })
          .filter(Boolean)
          .join('; ');

        response.data.detail = messages || 'Validation error';
      }

      // Case 2: Single error object
      if (
        !Array.isArray(detail) &&
        typeof detail === 'object' &&
        detail !== null
      ) {
        const message = 'msg' in detail ? detail.msg : JSON.stringify(detail);
        response.data.detail = message;
      }
    }

    // Handle generic network / CORS errors (no response object present)
    if (!response && error.code === 'ERR_NETWORK') {
      error.message =
        'Network error. Unable to reach backend server. Check that it is running and not blocked by CORS.';
    }

    // Retry transient 5xx
    return retryRequest(error);
  }
);

export default client;
