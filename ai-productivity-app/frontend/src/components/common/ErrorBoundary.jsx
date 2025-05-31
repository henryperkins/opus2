import { Component } from 'react';
import { Link } from 'react-router-dom';

/**
 * A simple error boundary that catches any runtime errors in children components,
 * preventing the entire app from unmounting.
 */
class ErrorBoundary extends Component {
  state = { hasError: false };

  static getDerivedStateFromError() {
    // Update state so the next render shows the fallback UI
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    // You can log the error to an error reporting service, e.g. Sentry
    console.error('Boundary caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 text-center">
          <h1 className="text-2xl font-semibold">Something went wrong</h1>
          <p className="mt-4 text-gray-600">
            Please{' '}
            <button
              onClick={() => window.location.reload()}
              className="text-blue-600 underline"
            >
              reload
            </button>
            {' '}or go{' '}
            <Link to="/" className="text-blue-600 underline">
              home
            </Link>.
          </p>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
