import PropTypes from "prop-types";

/**
 * Adaptive skeleton loader for different content types
 * Provides smooth loading placeholders while content loads
 */
export default function SkeletonLoader({
  type = "default",
  count = 1,
  className = "",
  width = "100%",
  height = "auto",
}) {
  const renderSkeleton = (index) => {
    const baseClasses = "animate-pulse bg-gray-200 rounded";

    switch (type) {
      case "message":
        return (
          <div key={index} className={`flex mb-4 ${className}`}>
            <div className="w-8 h-8 bg-gray-200 rounded-full animate-pulse mr-3" />
            <div className="flex-1">
              <div className="h-4 bg-gray-200 rounded animate-pulse mb-2 w-1/4" />
              <div className="space-y-2">
                <div className="h-4 bg-gray-200 rounded animate-pulse w-full" />
                <div className="h-4 bg-gray-200 rounded animate-pulse w-3/4" />
                <div className="h-4 bg-gray-200 rounded animate-pulse w-1/2" />
              </div>
            </div>
          </div>
        );

      case "search-result":
        return (
          <div
            key={index}
            className={`p-4 border rounded-lg mb-3 ${className}`}
          >
            <div className="h-5 bg-gray-200 rounded animate-pulse mb-2 w-3/4" />
            <div className="h-4 bg-gray-200 rounded animate-pulse mb-2 w-full" />
            <div className="h-4 bg-gray-200 rounded animate-pulse w-2/3" />
            <div className="flex mt-3 space-x-2">
              <div className="h-6 bg-gray-200 rounded animate-pulse w-16" />
              <div className="h-6 bg-gray-200 rounded animate-pulse w-20" />
            </div>
          </div>
        );

      case "knowledge-panel":
        return (
          <div key={index} className={`space-y-3 ${className}`}>
            <div className="h-6 bg-gray-200 rounded animate-pulse w-1/2" />
            {[...Array(3)].map((_, i) => (
              <div key={i} className="flex items-center space-x-2">
                <div className="w-4 h-4 bg-gray-200 rounded animate-pulse" />
                <div className="h-4 bg-gray-200 rounded animate-pulse flex-1" />
                <div className="h-4 bg-gray-200 rounded animate-pulse w-12" />
              </div>
            ))}
          </div>
        );

      case "card":
        return (
          <div key={index} className={`p-4 border rounded-lg ${className}`}>
            <div className="h-6 bg-gray-200 rounded animate-pulse mb-3 w-3/4" />
            <div className="space-y-2">
              <div className="h-4 bg-gray-200 rounded animate-pulse w-full" />
              <div className="h-4 bg-gray-200 rounded animate-pulse w-5/6" />
            </div>
          </div>
        );

      case "line":
        return (
          <div
            key={index}
            className={`h-4 bg-gray-200 rounded animate-pulse mb-2 ${className}`}
            style={{ width, height: height !== "auto" ? height : undefined }}
          />
        );

      case "streaming-message":
        return (
          <div key={index} className={`flex mb-4 ${className}`}>
            <div className="w-8 h-8 bg-blue-200 rounded-full animate-pulse mr-3 shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="h-4 bg-blue-100 rounded animate-pulse mb-2 w-16" />
              <div className="space-y-2">
                <div className="h-4 bg-gray-200 rounded animate-pulse w-full" />
                <div className="h-4 bg-gray-200 rounded animate-pulse w-4/5" />
                <div className="flex items-center space-x-2 mt-2">
                  <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
                  <div
                    className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"
                    style={{ animationDelay: "0.1s" }}
                  ></div>
                  <div
                    className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"
                    style={{ animationDelay: "0.2s" }}
                  ></div>
                  <span className="text-xs text-gray-500 ml-2">
                    AI is thinking...
                  </span>
                </div>
              </div>
            </div>
          </div>
        );

      case "websocket-connecting":
        return (
          <div
            key={index}
            className={`flex items-center justify-center p-4 ${className}`}
          >
            <div className="flex items-center space-x-3">
              <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
              <span className="text-sm text-gray-600">
                Connecting to chat...
              </span>
            </div>
          </div>
        );

      case "model-switching":
        return (
          <div
            key={index}
            className={`flex items-center space-x-3 p-3 bg-yellow-50 rounded-lg ${className}`}
          >
            <div className="w-5 h-5 text-yellow-600">
              <svg
                className="w-full h-full animate-spin"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                  className="opacity-25"
                ></circle>
                <path
                  fill="currentColor"
                  className="opacity-75"
                  d="M4 12a8 8 0 0 1 8-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 0 1 4 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
            </div>
            <span className="text-sm text-yellow-800">
              Switching AI model...
            </span>
          </div>
        );

      default:
        return (
          <div
            key={index}
            className={`${baseClasses} ${className}`}
            style={{
              width,
              height: height !== "auto" ? height : "60px",
            }}
          />
        );
    }
  };

  return (
    <div className="space-y-3">
      {[...Array(count)].map((_, index) => renderSkeleton(index))}
    </div>
  );
}

SkeletonLoader.propTypes = {
  type: PropTypes.oneOf([
    "default",
    "message",
    "search-result",
    "knowledge-panel",
    "card",
    "line",
    "streaming-message",
    "websocket-connecting",
    "model-switching",
  ]),
  count: PropTypes.number,
  className: PropTypes.string,
  width: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  height: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
};
