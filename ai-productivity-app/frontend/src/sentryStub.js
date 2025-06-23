/*
 * Minimal no-op stub for the `@sentry/react` package so that the project can
 * be built without adding the full Sentry SDK as a dependency. The real Sentry
 * SDK is only required when error reporting is enabled (i.e. a DSN is
 * provided). In local / open-source environments we simply replace the import
 * with this lightweight shim via a Vite alias (see vite.config.js).
 */

export function init() {
  /* noop – sentry disabled */
}

export class BrowserTracing {
  constructor() {
    /* noop */
  }
}

// Provide a default export containing the named exports so that both
// `import * as Sentry from '@sentry/react'` and named-import styles work.
export default {
  init,
  BrowserTracing,
};
