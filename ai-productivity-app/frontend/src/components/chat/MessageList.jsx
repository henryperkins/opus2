import React, { useEffect, useRef, useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import CodeSnippet from '../search/CodeSnippet';

export default function MessageList({
  messages,
  onMessageSelect,
  onCodeSelect,
  onMessageEdit,
  onMessageDelete,
  currentUserId
}) {
  const bottomRef = useRef(null);
  const [editingId, setEditingId] = useState(null);
  const [editContent, setEditContent] = useState('');

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleEdit = (message) => {
    setEditingId(message.id);
    setEditContent(message.content);
  };

  const handleSaveEdit = () => {
    if (editingId && editContent.trim()) {
      onMessageEdit(editingId, editContent);
      setEditingId(null);
      setEditContent('');
    }
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditContent('');
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${
            message.role === 'assistant' ? 'justify-start' : 'justify-end'
          }`}
        >
          <div
            className={`max-w-[70%] rounded-lg p-4 ${
              message.role === 'assistant'
                ? 'bg-gray-100 text-gray-900'
                : 'bg-blue-500 text-white'
            } ${onMessageSelect ? 'cursor-pointer hover:opacity-90' : ''}`}
            onClick={() => onMessageSelect?.(message)}
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
            {editingId === message.id ? (
              <div className="space-y-2">
                <textarea
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  className="w-full p-2 rounded border text-gray-900"
                  rows={4}
                />
                <div className="flex space-x-2">
                  <button
                    onClick={handleSaveEdit}
                    className="px-3 py-1 bg-green-500 text-white rounded text-sm"
                  >
                    Save
                  </button>
                  <button
                    onClick={handleCancelEdit}
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
                  onClick={(e) => {
                    e.stopPropagation();
                    handleEdit(message);
                  }}
                  className="text-xs opacity-70 hover:opacity-100"
                >
                  Edit
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onMessageDelete(message.id);
                  }}
                  className="text-xs opacity-70 hover:opacity-100"
                >
                  Delete
                </button>
              </div>
            )}
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
