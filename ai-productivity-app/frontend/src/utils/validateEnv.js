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
  // Default when env var is missing
  const fallback = 'http://localhost:8000';

  // Use provided env var or fallback
  let urlInput = value || fallback;

  try {
    // Construct URL relative to current origin (handles relative paths)
    const urlObj = new URL(urlInput, window.location.origin);

    // If frontend is HTTPS but backend URL is HTTP, upgrade to HTTPS only when safe
    if (window.location.protocol === 'https:' && urlObj.protocol === 'http:') {
      const sameHost = ['localhost', window.location.hostname].includes(
        urlObj.hostname
      );
      if (sameHost) {
        urlObj.protocol = 'https:';
      } else {
        return '/'; // fall back to same-origin base
      }
    }
    return urlObj.toString();
  } catch {
    // Gracefully handle non-URL strings / relative paths
    if (window.location.protocol === 'https:' && urlInput.startsWith('http://')) {
      return urlInput.replace(/^http:/, 'https:');
    }
    return urlInput;
  }
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
