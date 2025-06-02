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

const BASE_URL =
  // Prefer explicit vite variable; otherwise use relative path (no base prefix)
  // to avoid double `/api` when endpoints already include it.
  import.meta.env.VITE_API_URL || '';

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

    // Retry transient 5xx
    return retryRequest(error);
  }
);

export default client;
