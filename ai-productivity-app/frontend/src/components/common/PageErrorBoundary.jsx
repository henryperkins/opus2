import React from 'react';
import ErrorBoundary from './ErrorBoundary';

/**
 * Page-level error boundary wrapper that provides page-specific error handling
 * for components that may crash the SPA
 */
function PageErrorBoundary({ children, pageName, onError, fallback }) {
  const handleRetry = () => {
    // Clear any page-specific state or caches
    if (onError) {
      onError();
    }
    // Reload the page as a last resort
    window.location.reload();
  };

  const PageFallback = ({ error, errorInfo, errorType, onRetry }) => {
    if (fallback) {
      return fallback({ error, errorInfo, errorType, onRetry });
    }

    return (
      <div className="min-h-[60vh] flex items-center justify-center p-8">
        <div className="text-center max-w-md">
          <div className="text-6xl mb-4">⚠️</div>
          
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
            {pageName || 'Page'} Error
          </h1>
          
          <p className="text-gray-600 dark:text-gray-300 mb-6">
            Something went wrong while loading this page. You can try reloading or go back to the dashboard.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <button
              onClick={onRetry || handleRetry}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              Reload Page
            </button>
            
            <a
              href="/projects"
              className="px-4 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-800 dark:text-gray-200 rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 text-center"
            >
              Go to Dashboard
            </a>
          </div>
          
          {process.env.NODE_ENV === 'development' && error && (
            <details className="mt-6 text-left">
              <summary className="cursor-pointer text-sm text-gray-600 dark:text-gray-400 font-medium">
                Error Details (Development Only)
              </summary>
              <pre className="mt-2 p-4 bg-gray-100 dark:bg-gray-800 text-xs overflow-auto rounded text-left max-h-40">
                {error && JSON.stringify(error, null, 2)}
                {errorInfo && (
                  <>
                    <br />
                    {errorInfo.componentStack}
                  </>
                )}
              </pre>
            </details>
          )}
        </div>
      </div>
    );
  };

  return (
    <ErrorBoundary 
      fallback={PageFallback}
      onRetry={handleRetry}
    >
      {children}
    </ErrorBoundary>
  );
}

export default PageErrorBoundary;