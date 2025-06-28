import React from 'react';
import { AlertTriangle, RefreshCw, Code } from 'lucide-react';

/**
 * Error boundary specifically for Monaco Editor
 * Provides graceful fallback when editor crashes
 */
class EditorErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({
      error: error,
      errorInfo: errorInfo
    });

    // Log to console for debugging
    console.error('Monaco Editor Error:', error, errorInfo);

    // Report to monitoring service if available
    if (window.Sentry) {
      window.Sentry.captureException(error, {
        tags: { component: 'monaco-editor' },
        extra: errorInfo
      });
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-full min-h-[200px] p-6 bg-gray-50 dark:bg-gray-800 border border-red-200 dark:border-red-800 rounded-lg">
          <div className="text-center max-w-md">
            <div className="flex items-center justify-center w-16 h-16 mx-auto mb-4 bg-red-100 dark:bg-red-900/30 rounded-full">
              <AlertTriangle className="w-8 h-8 text-red-600 dark:text-red-400" />
            </div>
            
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
              Code Editor Error
            </h3>
            
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              The code editor encountered an unexpected error. Your work has been preserved.
            </p>

            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <button
                onClick={this.handleRetry}
                className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Retry Editor
              </button>
              
              <button
                onClick={() => this.props.onFallback?.(this.props.value)}
                className="inline-flex items-center px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors"
              >
                <Code className="w-4 h-4 mr-2" />
                Use Text Area
              </button>
            </div>

            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details className="mt-4 text-left">
                <summary className="text-sm text-gray-500 cursor-pointer mb-2">
                  Technical Details
                </summary>
                <pre className="text-xs bg-gray-100 dark:bg-gray-900 p-3 rounded border overflow-auto max-h-32">
                  {this.state.error.toString()}
                  {this.state.errorInfo.componentStack}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default EditorErrorBoundary;