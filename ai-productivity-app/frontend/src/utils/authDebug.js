/**
 * authDebug – small helper exposing a function that logs common environment
 * parameters useful for diagnosing authentication problems (cookies present,
 * localStorage state, running extensions etc.).
 *
 * Import and call `checkAuthEnvironment()` from the browser console when
 * things go wrong; it prints a concise object making it easier to share info
 * during debugging sessions.
 */

export function checkAuthEnvironment() {
  const info = {
    apiUrl: (import.meta.env.VITE_API_URL?.match(/^https?:\/\//)
      ? import.meta.env.VITE_API_URL
      : `http://${import.meta.env.VITE_API_URL || 'localhost:8000'}`),
    cookies: document.cookie,
    localStorageAuth: localStorage.getItem('ai-productivity-auth'),
    extensions: detectBrowserExtensions(),
  };

  // eslint-disable-next-line no-console
  console.table(info);
  return info;
}

function detectBrowserExtensions() {
  const list = [];
  // Heuristic detections (can expand later)

  // LastPass injects an element with data-lastpass-root
  if (document.querySelector('[data-lastpass-root]')) {
    list.push('LastPass');
  }

  // 1Password adds a "data-op-target" attribute to input elements
  if (document.querySelector('[data-op-target]')) {
    list.push('1Password');
  }

  return list;
}
