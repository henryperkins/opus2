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
import { queryClient } from '../queryClient.js';

// -----------------------------------------------------------------------------
// Configuration
// -----------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Backend base URL
// ---------------------------------------------------------------------------
// 1. Use the explicit Vite env variable when provided (works with Docker-compose
//    where `VITE_API_URL` is injected, or local development with specific backend URL).
// 2. Fallback to relative URLs for production behind reverse proxy.
//
// This handles both development scenarios:
// - Local dev: VITE_API_URL=http://localhost:8000 (backend on different port)
// - Production: VITE_API_URL="" or unset (reverse proxy handles routing)

/**
 * Resolve backend base URL with protocol-safety:
 *  1. Prefer VITE_API_URL when provided.
 *  2. If the frontend is served over HTTPS but VITE_API_URL begins with HTTP,
 *     automatically upgrade the protocol to HTTPS to avoid mixed-content errors
 *     (assuming the backend also supports HTTPS on the same host/port).
 *  3. Fallback to relative '/' which relies on same-origin or reverse-proxy routing.
 */
let resolvedBaseUrl = '/';
const envUrl = import.meta.env.VITE_API_URL;

/**
 * Determine the safest base URL for backend API calls.
 *
 * Decision matrix:
 * ────────────────────────────────────────────────────────────
 * 1. No VITE_API_URL provided  → use relative '/' (same-origin)
 * 2. VITE_API_URL provided and protocol matches page protocol
 *    → use the provided absolute URL as-is.
 * 3. VITE_API_URL is HTTP while page is HTTPS
 *    a) Same hostname or localhost  → upgrade to HTTPS.
 *    b) Different hostname          → fall back to relative '/' to
 *                                     avoid mixed-content errors.
 * 4. VITE_API_URL is relative (e.g. '/api') → use as-is.
 */
if (envUrl) {
  try {
    const urlObj = new URL(envUrl, window.location.origin);

    // Avoid browser mixed-content errors: when the frontend is served over
    // HTTPS but the configured backend URL is HTTP, upgrade the protocol to
    // HTTPS automatically.  Modern browsers will silently refuse the request
    // otherwise.
    //
    // Historically we limited this behaviour to “same-host or localhost”
    // scenarios, falling back to a relative path for cross-host setups.  This
    // proved too restrictive – production deployments often route traffic to
    // a separate API sub-domain (e.g. api.example.com) that **does** support
    // HTTPS even when the environment variable mistakenly points to HTTP.
    //
    // The safer default is therefore:
    //   • If the page is HTTPS and the backend URL is HTTP → **always**
    //     upgrade to HTTPS.
    //   • Otherwise leave the URL untouched.
    if (window.location.protocol === 'https:' && urlObj.protocol === 'http:') {
      urlObj.protocol = 'https:';
    }

    // At this point the protocol matches the page’s protocol, or the page is
    // served over plain HTTP where mixed-content is not an issue.
    resolvedBaseUrl = urlObj.toString();
  } catch {
    // envUrl might be a relative path like '/api'
    resolvedBaseUrl = envUrl;
  }
}

const client = axios.create({
  baseURL: resolvedBaseUrl,
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

  if (csrfToken && mutating.includes(config.method?.toLowerCase())) {
    // Ensure headers object exists
    config.headers = config.headers || {};
    config.headers['X-CSRFToken'] = csrfToken;
  }

  return config;
}

// -----------------------------------------------------------------------------
// Retry helper (exponential back-off up to 3 attempts)
// -----------------------------------------------------------------------------

async function retryRequest(error) {
  const cfg = error.config;
  if (!cfg || cfg.__retryCount >= 3 || !error.response || cfg.__noRetry) {
    return Promise.reject(error);
  }
  const { status } = error.response;
  // Only retry transient server errors, not application errors
  const transient = [502, 503, 504];
  if (transient.includes(status)) {
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

// Request interceptor: attach CSRF token and optional logging
client.interceptors.request.use(
  (config) => {
    // Attach CSRF token for mutating requests
    attachCsrf(config);

    // Optional request logging in development
    if (import.meta.env.DEV && import.meta.env.VITE_API_DEBUG) {
      console.log(`🚀 API Request: ${config.method?.toUpperCase()} ${config.url}`);
    }

    return config;
  },
  (error) => {
    if (import.meta.env.DEV) {
      console.error('❌ Request Error:', error);
    }
    return Promise.reject(error);
  }
);

client.interceptors.response.use(
  (resp) => {
    // Optional response logging in development
    if (import.meta.env.DEV && import.meta.env.VITE_API_DEBUG) {
      console.log(`✅ API Response: ${resp.status} ${resp.config.method?.toUpperCase()} ${resp.config.url}`);
    }
    return resp;
  },
  async (error) => {
    const { response } = error;

    // Handle auth errors globally
    // -------------------------------------------------------------------
    // 401 – Unauthenticated / session expired
    // -------------------------------------------------------------------
    // The AuthProvider already handles the unauthenticated state gracefully
    // by catching the 401 in `fetchMe` and returning `null`, meaning the
    // application should render as a "guest" user.  Clearing the entire
    // React-Query cache here caused a feedback-loop where the ongoing `/me`
    // request was removed from the cache which in turn re-triggered a new
    // request – resulting in an infinite "Checking authentication…" spinner.
    //
    // Instead of wiping the complete cache we now only reset the `me` query
    // ensuring other cached data gets cleared when the user explicitly logs
    // out via `authAPI.logout()` (that path still calls `queryClient.clear()`).
    if (response && response.status === 401) {
      if (queryClient) {
        queryClient.setQueryData(['me'], null);
      }
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

    // Handle timeout errors
    if (!response && error.code === 'ECONNABORTED') {
      error.message =
        'Request timeout. The server is taking too long to respond.';
    }

    // Handle connection refused errors (common in development)
    if (!response && (error.code === 'ECONNREFUSED' || error.message.includes('ECONNREFUSED'))) {
      error.message =
        'Connection refused. Backend server may not be running on the expected port.';
    }

    // Retry transient 5xx
    return retryRequest(error);
  }
);

export default client;
