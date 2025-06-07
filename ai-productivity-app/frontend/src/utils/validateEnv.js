// Utility: validateEnv
// -------------------
// Quick helper that pings the backend health endpoint to verify that the
// `VITE_API_URL` environment variable points to a reachable server.
// Components can import `validateEnvironment()` during app startup and show a
// friendly warning when the backend cannot be contacted.

export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Perform a HEAD/GET request to the backend health endpoint to ensure the
 * environment is configured correctly. Returns a boolean.
 * @returns {Promise<boolean>} whether the backend responded with HTTP 200.
 */
export async function validateEnvironment() {
  try {
    const res = await fetch(`${API_URL}/health/ready`, {
      method: 'GET',
      credentials: 'include',
      headers: { Accept: 'application/json' },
    });
    return res.ok;
  } catch {
    return false;
  }
}
