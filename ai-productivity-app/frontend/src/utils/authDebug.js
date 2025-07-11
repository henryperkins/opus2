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
  // Normalise API URL to avoid mixed-content issues
  const resolvedApiUrl = (() => {
    const envUrl = import.meta.env.VITE_API_URL;
    try {
      const urlObj = new URL(
        envUrl || "http://localhost:8000",
        window.location.origin,
      );
      if (
        window.location.protocol === "https:" &&
        urlObj.protocol === "http:"
      ) {
        const sameHost = ["localhost", window.location.hostname].includes(
          urlObj.hostname,
        );
        if (sameHost) {
          urlObj.protocol = "https:";
        } else {
          return "/";
        }
      }
      return urlObj.toString();
    } catch {
      if (
        window.location.protocol === "https:" &&
        envUrl?.startsWith("http://")
      ) {
        return envUrl.replace(/^http:/, "https:");
      }
      return envUrl || "http://localhost:8000";
    }
  })();

  const info = {
    apiUrl: resolvedApiUrl,
    cookies: document.cookie,
    localStorageAuth: localStorage.getItem("ai-productivity-auth"),
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
  if (document.querySelector("[data-lastpass-root]")) {
    list.push("LastPass");
  }

  // 1Password adds a "data-op-target" attribute to input elements
  if (document.querySelector("[data-op-target]")) {
    list.push("1Password");
  }

  return list;
}
