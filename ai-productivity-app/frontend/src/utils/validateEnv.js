// Utility: validateEnv
// -------------------
// Quick helper that pings the backend health endpoint to verify that the
// `VITE_API_URL` environment variable points to a reachable server.
// Components can import `validateEnvironment()` during app startup and show a
// friendly warning when the backend cannot be contacted.

// Normalise the backend URL so that it always contains a protocol.  Developers
// sometimes configure `VITE_API_URL` as "localhost:8000" which causes the
// browser `fetch()` API to throw "The string did not match the expected
// pattern".  When the protocol is missing we implicitly prefix it with
// "http://".  Falling back to the conventional FastAPI dev port when the env
// variable is absent.

function normaliseApiUrl(value) {
  if (!value) return 'http://localhost:8000';
  if (value.startsWith('http://') || value.startsWith('https://')) {
    return value;
  }
  return `http://${value}`;
}

export const API_URL = normaliseApiUrl(import.meta.env.VITE_API_URL);

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
