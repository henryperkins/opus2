import React from 'react';

class ChatErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({
      error,
      errorInfo
    });

    // Log to console for debugging
    console.error('Chat Error Boundary caught an error:', error, errorInfo);

    // Here you could also log to an error reporting service
    // errorReportingService.captureException(error, { extra: errorInfo });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-64 p-6 bg-red-50 border border-red-200 rounded-lg">
          <div className="text-red-600 text-lg font-semibold mb-2">
            Chat Error
          </div>
          <div className="text-red-700 text-sm mb-4 text-center">
            Something went wrong with the chat functionality. Please try refreshing the page.
          </div>
          <div className="flex space-x-2">
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              Refresh Page
            </button>
            <button
              onClick={() => this.setState({ hasError: false, error: null, errorInfo: null })}
              className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
            >
              Try Again
            </button>
          </div>
          {process.env.NODE_ENV === 'development' && (
            <details className="mt-4 p-4 bg-gray-100 rounded text-sm">
              <summary className="cursor-pointer text-gray-700 font-medium">
                Error Details (Development)
              </summary>
              <pre className="mt-2 whitespace-pre-wrap text-xs text-gray-600">
                {this.state.error && this.state.error.toString()}
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

export default ChatErrorBoundary;
