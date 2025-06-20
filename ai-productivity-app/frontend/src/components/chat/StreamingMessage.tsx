// components/chat/StreamingMessage.tsx
import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader, StopCircle, RefreshCw } from 'lucide-react';

interface StreamingMessageProps {
  messageId: string;
  isStreaming: boolean;
  content: string;
  onStop?: () => void;
  onRetry?: () => void;
  showTokenCount?: boolean;
  model?: string;
}

export default function StreamingMessage({
  messageId,
  isStreaming,
  content,
  onStop,
  onRetry,
  showTokenCount = true,
  model
}: StreamingMessageProps) {
  const [displayedContent, setDisplayedContent] = useState('');
  const [currentTokens, setCurrentTokens] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);
  const lastUpdateRef = useRef<number>(Date.now());

  // Simulate streaming effect
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

    // Streaming simulation
    let currentIndex = displayedContent.length;
    const targetLength = content.length;

    const streamInterval = setInterval(() => {
      if (currentIndex >= targetLength) {
        clearInterval(streamInterval);
        setIsComplete(true);
        return;
      }

      // Variable speed streaming for more natural feel
      const chunkSize = Math.random() > 0.95 ? 1 : Math.floor(Math.random() * 4) + 2;
      const nextIndex = Math.min(currentIndex + chunkSize, targetLength);

      setDisplayedContent(content.substring(0, nextIndex));
      setCurrentTokens(Math.floor(nextIndex / 4));
      currentIndex = nextIndex;

      // Auto-scroll to bottom
      if (contentRef.current) {
        const parent = contentRef.current.parentElement;
        if (parent) {
          parent.scrollTop = parent.scrollHeight;
        }
      }
    }, 30);

    return () => clearInterval(streamInterval);
  }, [content, isStreaming, displayedContent]);

  // Cursor animation
  const CursorAnimation = () => (
    <motion.span
      className="inline-block w-2 h-4 bg-blue-500 ml-0.5"
      animate={{ opacity: [1, 0] }}
      transition={{ duration: 0.5, repeat: Infinity, repeatType: "reverse" }}
    />
  );

  // Token counter animation
  const TokenCounter = () => (
    <motion.div
      className="text-xs text-gray-500 mt-2"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.5 }}
    >
      {currentTokens} tokens {isStreaming && '(streaming...)'}
    </motion.div>
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
      <AnimatePresence>
        {isStreaming && !isComplete && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
          >
            <StreamingIndicator />
          </motion.div>
        )}
      </AnimatePresence>

      <div ref={contentRef} className="prose prose-sm max-w-none">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
        >
          {displayedContent}
          {isStreaming && !isComplete && <CursorAnimation />}
        </motion.div>
      </div>

      {showTokenCount && displayedContent && <TokenCounter />}

      {/* Action buttons */}
      <AnimatePresence>
        {(isStreaming || isComplete) && (
          <motion.div
            className="flex items-center space-x-2 mt-3"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ delay: 0.3 }}
          >
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
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
