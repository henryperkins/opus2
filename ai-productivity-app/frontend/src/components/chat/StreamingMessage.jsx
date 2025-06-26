import { useState, useEffect, useRef } from 'react';
import { Loader, StopCircle, RefreshCw } from 'lucide-react';

export default function StreamingMessage({
  messageId,
  isStreaming,
  content,
  onStop,
  onRetry,
  showTokenCount = true,
  model
}) {
  const [displayedContent, setDisplayedContent] = useState('');
  const [currentTokens, setCurrentTokens] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const contentRef = useRef(null);
  const lastUpdateRef = useRef(Date.now());

  // Efficient streaming effect with token-based approach
  useEffect(() => {
    if (!isStreaming && content === displayedContent) {
      setIsComplete(true);
      return;
    }

    if (!isStreaming) {
      // If not streaming, show full content immediately
      setDisplayedContent(content);
      setCurrentTokens(Math.floor(content.length / 4));
      setIsComplete(true);
      return;
    }

    // Only update if content actually changed to prevent unnecessary re-renders
    if (content !== displayedContent) {
      // For streaming, append only new content to prevent flicker
      const newContentLength = content.length;
      const currentContentLength = displayedContent.length;
      
      if (newContentLength > currentContentLength) {
        // Append new tokens progressively
        const newTokens = content.substring(currentContentLength);
        
        // Use RAF for smooth updates
        const animate = () => {
          setDisplayedContent(prev => {
            if (prev.length >= content.length) {
              setIsComplete(true);
              return content;
            }
            
            // Append new characters with natural timing
            const chunkSize = Math.min(3, content.length - prev.length);
            const nextContent = content.substring(0, prev.length + chunkSize);
            setCurrentTokens(Math.floor(nextContent.length / 4));
            
            // Schedule next update if more content to display
            if (nextContent.length < content.length) {
              setTimeout(animate, 20);
            } else {
              setIsComplete(true);
            }
            
            return nextContent;
          });
        };
        
        animate();
      }
    }
  }, [content, isStreaming]);

  // Cursor animation - using CSS instead of Framer Motion
  const CursorAnimation = () => (
    <span className="streaming-cursor inline-block w-2 h-4 bg-blue-500 ml-0.5" />
  );

  // Token counter - simplified without animation
  const TokenCounter = () => (
    <div className="text-xs text-gray-500 mt-2 fade-in">
      {currentTokens} tokens {isStreaming && '(streaming...)'}
    </div>
  );

  // Streaming indicator
  const StreamingIndicator = () => (
    <div className="flex items-center space-x-2 text-xs text-gray-500 mb-2">
      <Loader className="w-3 h-3 animate-spin" />
      <span>Generating response...</span>
      {model && <span className="text-gray-400">• {model}</span>}
    </div>
  );

  return (
    <div className="relative">
      {/* Streaming indicator */}
      {isStreaming && !isComplete && (
        <div className="streaming-indicator">
          <StreamingIndicator />
        </div>
      )}

      <div ref={contentRef} className="message-content max-w-none">
        <div className="fade-in">
          {displayedContent}
          {isStreaming && !isComplete && <CursorAnimation />}
        </div>
      </div>

      {showTokenCount && displayedContent && <TokenCounter />}

      {/* Action buttons */}
      {(isStreaming || isComplete) && (
        <div className="flex items-center space-x-2 mt-3 fade-in">
          {isStreaming && !isComplete && onStop && (
            <button
              onClick={onStop}
              className="flex items-center space-x-1 px-2 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors"
            >
              <StopCircle className="w-3 h-3" />
              <span>Stop</span>
            </button>
          )}

          {isComplete && onRetry && (
            <button
              onClick={onRetry}
              className="flex items-center space-x-1 px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors"
            >
              <RefreshCw className="w-3 h-3" />
              <span>Regenerate</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
}
