// utils/globalErrorHandler.js
// -----------------------------------------------------------------------------
// Centralised error handling across the browser context.  The handler captures
// unhandled promise rejections and `window.onerror` events and allows
// components (like ErrorBoundary) to subscribe for live updates.
// -----------------------------------------------------------------------------

class GlobalErrorHandler {
  constructor() {
    this.errorHandlers = new Set();
    this._setupGlobalListeners();
  }

  // -------------------------------------------------------------------------
  // Public API – subscribe / handleError
  // -------------------------------------------------------------------------

  subscribe(handler) {
    this.errorHandlers.add(handler);
    return () => this.errorHandlers.delete(handler);
  }

  handleError(errorInfo) {
    this.errorHandlers.forEach((cb) => {
      try {
        cb(errorInfo);
      } catch (err) {
        // eslint-disable-next-line no-console
        console.error("Error inside error handler subscriber:", err);
      }
    });

    if (import.meta.env.PROD) {
      this._sendToErrorService(errorInfo);
    }
  }

  // -------------------------------------------------------------------------
  // Internal helpers
  // -------------------------------------------------------------------------

  _setupGlobalListeners() {
    window.addEventListener("unhandledrejection", (event) => {
      // eslint-disable-next-line no-console
      console.error("Unhandled promise rejection:", event.reason);
      this.handleError({
        type: "unhandledRejection",
        error: event.reason,
        promise: event.promise,
        timestamp: new Date().toISOString(),
      });
    });

    window.addEventListener("error", (event) => {
      // eslint-disable-next-line no-console
      console.error("Global error:", event.error);
      this.handleError({
        type: "globalError",
        error: event.error,
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        timestamp: new Date().toISOString(),
      });
    });
  }

  _sendToErrorService(errorInfo) {
    // Placeholder – integrate with Sentry, LogRocket, etc.
    // eslint-disable-next-line no-console
    console.log("[ErrorService] would send:", errorInfo);
  }
}

// Singleton instance
export const globalErrorHandler = new GlobalErrorHandler();
