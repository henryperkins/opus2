import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { useVirtualizer } from '@tanstack/react-virtual';
import CodeSnippet from '../search/CodeSnippet';
import EnhancedMessageRenderer from './EnhancedMessageRenderer';

// Throttle scroll events to prevent performance issues
const useThrottledCallback = (callback, delay) => {
  const callbackRef = useRef(callback);
  const throttleRef = useRef(null);

  useEffect(() => {
    callbackRef.current = callback;
  });

  return useCallback((...args) => {
    if (throttleRef.current) return;

    throttleRef.current = setTimeout(() => {
      callbackRef.current(...args);
      throttleRef.current = null;
    }, delay);
  }, [delay]);
};

export default function MessageList({
  messages,
  onMessageSelect,
  onCodeSelect,
  onMessageEdit,
  onMessageDelete,
  currentUserId,
  className = ''
}) {
  const parentRef = useRef(null);
  const [editingId, setEditingId] = useState(null);
  const [editContent, setEditContent] = useState('');
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [showNewMessageButton, setShowNewMessageButton] = useState(false);

  // Create virtual list
  const rowVirtualizer = useVirtualizer({
    count: messages.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 120, // Estimated message height
    overscan: 5, // Render extra messages for smooth scrolling
  });

  // Auto-scroll detection using IntersectionObserver
  const bottomMarkerRef = useRef(null);
  
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        const newIsAtBottom = entry.isIntersecting;
        setIsAtBottom(newIsAtBottom);
        setShowNewMessageButton(!newIsAtBottom && messages.length > 0);
      },
      { threshold: 0.1 }
    );

    if (bottomMarkerRef.current) {
      observer.observe(bottomMarkerRef.current);
    }

    return () => observer.disconnect();
  }, [messages.length]);

  // Auto-scroll when new messages arrive (only if user is at bottom)
  useEffect(() => {
    if (isAtBottom && messages.length > 0) {
      const lastItem = rowVirtualizer.getVirtualItems().slice(-1)[0];
      if (lastItem) {
        rowVirtualizer.scrollToIndex(messages.length - 1, { align: 'end' });
      }
    }
  }, [messages.length, isAtBottom, rowVirtualizer]);

  const scrollToBottom = useCallback(() => {
    if (messages.length > 0) {
      rowVirtualizer.scrollToIndex(messages.length - 1, { align: 'end' });
    }
  }, [messages.length, rowVirtualizer]);

  return (
    <div className={`relative h-full ${className}`.trim()}>
      <div
        ref={parentRef}
        className="h-full overflow-auto"
        style={{
          contain: 'layout style', // CSS containment for better performance
        }}
        role="log"
        aria-live="polite"
        aria-label="Chat messages"
      >
        <div
          style={{
            height: `${rowVirtualizer.getTotalSize()}px`,
            width: '100%',
            position: 'relative',
          }}
        >
          {rowVirtualizer.getVirtualItems().map((virtualRow) => {
            const message = messages[virtualRow.index];
            return (
              <div
                key={virtualRow.key}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: `${virtualRow.size}px`,
                  transform: `translateY(${virtualRow.start}px)`,
                }}
              >
                <MessageItem
                  message={message}
                  isEditing={editingId === message.id}
                  editContent={editContent}
                  onEditStart={() => {
                    setEditingId(message.id);
                    setEditContent(message.content);
                  }}
                  onEditSave={() => {
                    if (editingId && editContent.trim()) {
                      onMessageEdit(editingId, editContent);
                      setEditingId(null);
                      setEditContent('');
                    }
                  }}
                  onEditCancel={() => {
                    setEditingId(null);
                    setEditContent('');
                  }}
                  onEditContentChange={setEditContent}
                  onMessageSelect={onMessageSelect}
                  onCodeSelect={onCodeSelect}
                  onMessageDelete={onMessageDelete}
                  currentUserId={currentUserId}
                />
              </div>
            );
          })}
        </div>
        
        {/* Bottom marker for intersection observer */}
        <div ref={bottomMarkerRef} style={{ height: '1px', width: '100%' }} />
      </div>

      {/* New messages indicator */}
      {showNewMessageButton && (
        <button
          onClick={scrollToBottom}
          className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-full shadow-lg transition-all duration-200 flex items-center space-x-2 z-10"
          aria-label="Scroll to new messages"
        >
          <span>New messages</span>
          <span>↓</span>
        </button>
      )}
    </div>
  );
}

// Memoized individual message component
const MessageItem = React.memo(({
  message,
  isEditing,
  editContent,
  onEditStart,
  onEditSave,
  onEditCancel,
  onEditContentChange,
  onMessageSelect,
  onCodeSelect,
  onMessageDelete,
  currentUserId
}) => {
  const handleEdit = useCallback((e) => {
    e.stopPropagation();
    onEditStart();
  }, [onEditStart]);

  const handleDelete = useCallback((e) => {
    e.stopPropagation();
    onMessageDelete(message.id);
  }, [onMessageDelete, message.id]);

  const handleMessageClick = useCallback(() => {
    onMessageSelect?.(message);
  }, [onMessageSelect, message]);

  const handleCodeApply = useCallback((code, language) => {
    onCodeSelect?.({ code, language });
  }, [onCodeSelect]);

  return (
    <div
      className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} mb-6 px-4 py-2`}
    >
      <div
        className={`max-w-3xl rounded-lg px-4 py-3 ${
          message.role === 'user'
            ? 'bg-blue-600 text-white dark:bg-blue-500'
            : 'bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-100'
        } ${onMessageSelect ? 'cursor-pointer hover:opacity-90' : ''}`}
        onClick={handleMessageClick}
      >
        {/* Message header */}
        <div className="flex items-center justify-between mb-2 text-xs opacity-75">
          <span>{message.role === 'assistant' ? 'AI Assistant' : 'You'}</span>
          <div className="flex items-center space-x-2">
            <span>
              {formatDistanceToNow(new Date(message.created_at), {
                addSuffix: true
              })}
            </span>
            {message.is_edited && (
              <span>(edited)</span>
            )}
          </div>
        </div>

        {/* Message content */}
        {isEditing ? (
          <div className="space-y-2">
            <textarea
              value={editContent}
              onChange={(e) => onEditContentChange(e.target.value)}
              className="w-full p-2 rounded border text-gray-900"
              rows={4}
              aria-label="Edit message content"
            />
            <div className="flex space-x-2">
              <button
                onClick={onEditSave}
                className="px-3 py-1 bg-green-500 text-white rounded text-sm"
                aria-label="Save changes"
              >
                Save
              </button>
              <button
                onClick={onEditCancel}
                className="px-3 py-1 bg-gray-500 text-white rounded text-sm"
                aria-label="Cancel editing"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <EnhancedMessageRenderer
            message={message}
            content={message.content}
            metadata={message.metadata}
            onCodeApply={handleCodeApply}
          />
        )}

        {/* Actions */}
        {message.user_id === currentUserId && message.role === 'user' && (
          <div className="mt-2 flex space-x-2">
            <button
              onClick={handleEdit}
              className="text-xs opacity-70 hover:opacity-100"
              aria-label="Edit message"
            >
              Edit
            </button>
            <button
              onClick={handleDelete}
              className="text-xs opacity-70 hover:opacity-100"
              aria-label="Delete message"
            >
              Delete
            </button>
          </div>
        )}
      </div>
    </div>
  );
});
