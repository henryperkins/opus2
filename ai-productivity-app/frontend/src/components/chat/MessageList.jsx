import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { formatDistanceToNow } from 'date-fns';
import CodeSnippet from '../search/CodeSnippet';

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
  const bottomRef = useRef(null);
  const containerRef = useRef(null);
  const [editingId, setEditingId] = useState(null);
  const [editContent, setEditContent] = useState('');
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);

  // Throttled auto-scroll to prevent forced reflows
  const throttledScrollToBottom = useThrottledCallback(() => {
    if (shouldAutoScroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, 100);

  // Check if user has scrolled up manually
  const handleScroll = useThrottledCallback(() => {
    if (!containerRef.current) return;

    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
    setShouldAutoScroll(isNearBottom);
  }, 150);

  useEffect(() => {
    throttledScrollToBottom();
  }, [messages, throttledScrollToBottom]);

  // Memoize message components to prevent unnecessary re-renders
  const messageComponents = useMemo(() => {
    return messages.map((message) => (
      <MessageItem
        key={message.id}
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
    ));
  }, [
    messages,
    editingId,
    editContent,
    onMessageEdit,
    onMessageSelect,
    onCodeSelect,
    onMessageDelete,
    currentUserId
  ]);

  return (
    <div
      ref={containerRef}
      className={`chat-messages ${className}`.trim()}
      style={{
        overflowY: 'auto',
        contain: 'layout', // CSS containment for better performance
      }}
      onScroll={handleScroll}
    >
      {messageComponents}
      <div ref={bottomRef} />
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

  return (
    <div
      className={`chat-message ${
        message.role === 'assistant' ? 'chat-message-assistant' : 'chat-message-user'
      }`}
    >
      <div
        className={`chat-message-content ${onMessageSelect ? 'cursor-pointer hover:opacity-90' : ''}`}
        onClick={handleMessageClick}
      >
        {/* Message header */}
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs opacity-70">
            {message.role === 'assistant' ? 'AI' : 'You'}
          </span>
          <div className="flex items-center space-x-2">
            <span className="text-xs opacity-70">
              {formatDistanceToNow(new Date(message.created_at), {
                addSuffix: true
              })}
            </span>
            {message.is_edited && (
              <span className="text-xs opacity-70">(edited)</span>
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
            />
            <div className="flex space-x-2">
              <button
                onClick={onEditSave}
                className="px-3 py-1 bg-green-500 text-white rounded text-sm"
              >
                Save
              </button>
              <button
                onClick={onEditCancel}
                className="px-3 py-1 bg-gray-500 text-white rounded text-sm"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div className="prose prose-sm max-w-none">
            {message.content}
          </div>
        )}

        {/* Code snippets */}
        {message.code_snippets?.length > 0 && (
          <div className="mt-4 space-y-2">
            {message.code_snippets.map((snippet, index) => (
              <div key={index} className="relative">
                <CodeSnippet
                  content={snippet.code}
                  language={snippet.language}
                  startLine={snippet.line_start || 1}
                />
                {onCodeSelect && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onCodeSelect(snippet);
                    }}
                    className="absolute top-2 right-2 px-2 py-1 bg-blue-500 text-white text-xs rounded"
                  >
                    Use Code
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Referenced files */}
        {message.referenced_files?.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {message.referenced_files.map((file, index) => (
              <span
                key={index}
                className="text-xs bg-gray-200 text-gray-700 px-2 py-1 rounded"
              >
                {file}
              </span>
            ))}
          </div>
        )}

        {/* Actions */}
        {message.user_id === currentUserId && message.role === 'user' && (
          <div className="mt-2 flex space-x-2">
            <button
              onClick={handleEdit}
              className="text-xs opacity-70 hover:opacity-100"
            >
              Edit
            </button>
            <button
              onClick={handleDelete}
              className="text-xs opacity-70 hover:opacity-100"
            >
              Delete
            </button>
          </div>
        )}
      </div>
    </div>
  );
});
