import React from 'react';
import PropTypes from 'prop-types';

/**
 * Adaptive skeleton loader for different content types
 * Provides smooth loading placeholders while content loads
 */
export default function SkeletonLoader({
  type = 'default',
  count = 1,
  className = '',
  width = '100%',
  height = 'auto'
}) {
  const renderSkeleton = (index) => {
    const baseClasses = 'animate-pulse bg-gray-200 rounded';

    switch (type) {
      case 'message':
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

      case 'search-result':
        return (
          <div key={index} className={`p-4 border rounded-lg mb-3 ${className}`}>
            <div className="h-5 bg-gray-200 rounded animate-pulse mb-2 w-3/4" />
            <div className="h-4 bg-gray-200 rounded animate-pulse mb-2 w-full" />
            <div className="h-4 bg-gray-200 rounded animate-pulse w-2/3" />
            <div className="flex mt-3 space-x-2">
              <div className="h-6 bg-gray-200 rounded animate-pulse w-16" />
              <div className="h-6 bg-gray-200 rounded animate-pulse w-20" />
            </div>
          </div>
        );

      case 'knowledge-panel':
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

      case 'card':
        return (
          <div key={index} className={`p-4 border rounded-lg ${className}`}>
            <div className="h-6 bg-gray-200 rounded animate-pulse mb-3 w-3/4" />
            <div className="space-y-2">
              <div className="h-4 bg-gray-200 rounded animate-pulse w-full" />
              <div className="h-4 bg-gray-200 rounded animate-pulse w-5/6" />
            </div>
          </div>
        );

      case 'line':
        return (
          <div
            key={index}
            className={`h-4 bg-gray-200 rounded animate-pulse mb-2 ${className}`}
            style={{ width, height: height !== 'auto' ? height : undefined }}
          />
        );

      default:
        return (
          <div
            key={index}
            className={`${baseClasses} ${className}`}
            style={{
              width,
              height: height !== 'auto' ? height : '60px'
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
    'default',
    'message',
    'search-result',
    'knowledge-panel',
    'card',
    'line'
  ]),
  count: PropTypes.number,
  className: PropTypes.string,
  width: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  height: PropTypes.oneOfType([PropTypes.string, PropTypes.number])
};
