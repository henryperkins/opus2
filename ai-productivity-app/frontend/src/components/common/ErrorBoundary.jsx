import { Component } from 'react';
import { Link } from 'react-router-dom';

/**
 * A flexible error boundary that catches any runtime errors in children components,
 * preventing the entire app from unmounting.
 */
class ErrorBoundary extends Component {
  state = { hasError: false, error: null, errorInfo: null };

  static getDerivedStateFromError(error) {
    // Update state so the next render shows the fallback UI
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Store error details for debugging
    this.setState({
      error: error,
      errorInfo: errorInfo
    });

    // Log error to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error('ErrorBoundary caught an error:', error, errorInfo);
    }

    // You can log the error to an error reporting service, e.g. Sentry
    console.error('Boundary caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      const { fallback: Fallback, onRetry } = this.props;
      
      // If a custom fallback component is provided, use it
      if (Fallback) {
        return (
          <Fallback 
            error={this.state.error}
            errorInfo={this.state.errorInfo}
            onRetry={() => {
              this.setState({ hasError: false, error: null, errorInfo: null });
              onRetry?.();
            }}
          />
        );
      }

      // Default error UI
      return (
        <div className="p-8 text-center">
          <h1 className="text-2xl font-semibold">Something went wrong</h1>
          <p className="mt-4 text-gray-600 mb-4">
            {this.state.error?.message || 'An unexpected error occurred'}
          </p>
          <div className="space-x-4">
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null, errorInfo: null });
                onRetry?.();
              }}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              Try Again
            </button>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500"
            >
              Reload Page
            </button>
            <Link 
              to="/" 
              className="inline-block px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500"
            >
              Go Home
            </Link>
          </div>
          {process.env.NODE_ENV === 'development' && this.state.errorInfo && (
            <details className="mt-6 text-left max-w-2xl mx-auto">
              <summary className="cursor-pointer text-sm text-gray-600 font-medium">
                Error Details (Development Only)
              </summary>
              <pre className="mt-2 p-4 bg-gray-100 text-xs overflow-auto rounded text-left">
                {this.state.error && this.state.error.toString()}
                <br />
                {this.state.errorInfo.componentStack}
              </pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
