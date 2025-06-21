import { Component } from 'react';
import { Link } from 'react-router-dom';

/**
 * A comprehensive error boundary that catches runtime errors and provides
 * contextual error handling for different app scenarios
 */
class ErrorBoundary extends Component {
  state = {
    hasError: false,
    error: null,
    errorInfo: null,
    errorType: 'generic',
    retryCount: 0
  };

  static getDerivedStateFromError(error) {
    // Categorize error type for better UX
    let errorType = 'generic';

    if (error.message?.includes('WebSocket') || error.message?.includes('connection')) {
      errorType = 'websocket';
    } else if (error.message?.includes('network') || error.message?.includes('fetch')) {
      errorType = 'network';
    } else if (error.message?.includes('model') || error.message?.includes('AI')) {
      errorType = 'model';
    } else if (error.message?.includes('stream')) {
      errorType = 'streaming';
    } else if (error.message?.includes('search') || error.message?.includes('knowledge')) {
      errorType = 'search';
    }

    return { hasError: true, errorType };
  }

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

    // Log to external error service (e.g., Sentry) in production
    if (process.env.NODE_ENV === 'production') {
      // TODO: Send to error tracking service
      console.error('Production error:', error, errorInfo);
    }
  }

  handleRetry = () => {
    this.setState(prevState => ({
      hasError: false,
      error: null,
      errorInfo: null,
      retryCount: prevState.retryCount + 1
    }));
    this.props.onRetry?.();
  };

  getErrorContent = () => {
    const { errorType, error, retryCount } = this.state;
    const maxRetries = 3;

    switch (errorType) {
      case 'websocket':
        return {
          title: 'Connection Lost',
          description: 'Unable to connect to the chat server. Please check your internet connection.',
          icon: '🔌',
          actions: [
            {
              text: 'Reconnect',
              variant: 'primary',
              onClick: this.handleRetry,
              disabled: retryCount >= maxRetries
            },
            {
              text: 'Reload Page',
              variant: 'secondary',
              onClick: () => window.location.reload()
            }
          ]
        };

      case 'model':
        return {
          title: 'AI Model Error',
          description: 'There was an issue with the AI model. Try switching to a different model or retry.',
          icon: '🤖',
          actions: [
            {
              text: 'Try Again',
              variant: 'primary',
              onClick: this.handleRetry
            },
            {
              text: 'Switch Model',
              variant: 'secondary',
              onClick: () => {
                // TODO: Trigger model selector
                this.handleRetry();
              }
            }
          ]
        };

      case 'streaming':
        return {
          title: 'Streaming Error',
          description: 'The AI response was interrupted. You can retry or continue with a new message.',
          icon: '📡',
          actions: [
            {
              text: 'Retry Message',
              variant: 'primary',
              onClick: this.handleRetry
            },
            {
              text: 'Continue Chat',
              variant: 'secondary',
              onClick: this.handleRetry
            }
          ]
        };

      case 'search':
        return {
          title: 'Search Unavailable',
          description: 'Knowledge search is currently unavailable. You can still chat without search context.',
          icon: '🔍',
          actions: [
            {
              text: 'Continue Without Search',
              variant: 'primary',
              onClick: this.handleRetry
            },
            {
              text: 'Retry Search',
              variant: 'secondary',
              onClick: this.handleRetry
            }
          ]
        };

      case 'network':
        return {
          title: 'Network Error',
          description: 'Unable to reach the server. Please check your internet connection.',
          icon: '🌐',
          actions: [
            {
              text: 'Retry',
              variant: 'primary',
              onClick: this.handleRetry
            },
            {
              text: 'Work Offline',
              variant: 'secondary',
              onClick: this.handleRetry
            }
          ]
        };

      default:
        return {
          title: 'Something went wrong',
          description: error?.message || 'An unexpected error occurred',
          icon: '⚠️',
          actions: [
            {
              text: 'Try Again',
              variant: 'primary',
              onClick: this.handleRetry
            },
            {
              text: 'Reload Page',
              variant: 'secondary',
              onClick: () => window.location.reload()
            }
          ]
        };
    }
  };

  render() {
    if (this.state.hasError) {
      const { fallback: Fallback } = this.props;

      // If a custom fallback component is provided, use it
      if (Fallback) {
        return (
          <Fallback
            error={this.state.error}
            errorInfo={this.state.errorInfo}
            errorType={this.state.errorType}
            onRetry={this.handleRetry}
          />
        );
      }

      const errorContent = this.getErrorContent();

      // Enhanced error UI with contextual information
      return (
        <div className="min-h-[400px] flex items-center justify-center p-8">
          <div className="text-center max-w-md">
            <div className="text-6xl mb-4">{errorContent.icon}</div>

            <h1 className="text-2xl font-semibold text-gray-900 mb-2">
              {errorContent.title}
            </h1>

            <p className="text-gray-600 mb-6">
              {errorContent.description}
            </p>

            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              {errorContent.actions.map((action, index) => (
                <button
                  key={index}
                  onClick={action.onClick}
                  disabled={action.disabled}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed ${
                    action.variant === 'primary'
                      ? 'bg-blue-600 hover:bg-blue-700 text-white focus:ring-blue-500'
                      : 'bg-gray-200 hover:bg-gray-300 text-gray-800 focus:ring-gray-500'
                  }`}
                >
                  {action.text}
                </button>
              ))}
            </div>

            {this.state.retryCount > 0 && (
              <p className="mt-4 text-sm text-gray-500">
                Retry attempts: {this.state.retryCount}/3
              </p>
            )}

            <Link
              to="/"
              className="inline-block mt-4 text-sm text-blue-600 hover:text-blue-800"
            >
              ← Back to Home
            </Link>

            {process.env.NODE_ENV === 'development' && this.state.errorInfo && (
              <details className="mt-6 text-left">
                <summary className="cursor-pointer text-sm text-gray-600 font-medium">
                  Error Details (Development Only)
                </summary>
                <pre className="mt-2 p-4 bg-gray-100 text-xs overflow-auto rounded text-left max-h-40">
                  {this.state.error && this.state.error.toString()}
                  <br />
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

export default ErrorBoundary;
