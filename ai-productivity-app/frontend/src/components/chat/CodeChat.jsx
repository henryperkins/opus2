import React, { useState, useEffect, useRef } from 'react';
import { useChat } from '../../hooks/useChat';
import { useCodeEditor } from '../../hooks/useCodeEditor';
import MessageList from './MessageList';
import CommandInput from './CommandInput';
import CodePreview from './CodePreview';
import MonacoEditor from '@monaco-editor/react';

export default function CodeChat({ sessionId, projectId }) {
  const {
    messages,
    connectionState,
    typingUsers,
    sendMessage,
    editMessage,
    deleteMessage,
    sendTypingIndicator
  } = useChat(sessionId);

  const [editorContent, setEditorContent] = useState('');
  const [editorLanguage, setEditorLanguage] = useState('python');
  const [selectedMessage, setSelectedMessage] = useState(null);
  const [showDiff, setShowDiff] = useState(false);

  // Extract code from selected message
  useEffect(() => {
    if (selectedMessage?.code_snippets?.length > 0) {
      const snippet = selectedMessage.code_snippets[0];
      setEditorContent(snippet.code);
      setEditorLanguage(snippet.language);
    }
  }, [selectedMessage]);

  const handleSendMessage = (content, metadata) => {
    // Add current editor content if referenced
    if (content.includes('@editor')) {
      metadata.code_snippets = [{
        language: editorLanguage,
        code: editorContent
      }];
    }

    sendMessage(content, metadata);
  };

  const handleCodeSelect = (codeBlock) => {
    setEditorContent(codeBlock.code);
    setEditorLanguage(codeBlock.language);
  };

  const applyCodeSuggestion = (code) => {
    if (showDiff) {
      // Show diff view
      setShowDiff(true);
    } else {
      setEditorContent(code);
    }
  };

  return (
    <div className="flex h-full bg-gray-50">
      {/* Chat Panel */}
      <div className="w-1/2 flex flex-col bg-white border-r border-gray-200">
        <div className="flex-1 overflow-hidden">
          <MessageList
            messages={messages}
            onMessageSelect={setSelectedMessage}
            onCodeSelect={handleCodeSelect}
            onMessageEdit={editMessage}
            onMessageDelete={deleteMessage}
            currentUserId={user?.id}
          />
        </div>

        {/* Typing indicators */}
        {typingUsers.size > 0 && (
          <div className="px-4 py-2 text-sm text-gray-500">
            {typingUsers.size} user{typingUsers.size > 1 ? 's' : ''} typing...
          </div>
        )}

        {/* Connection status */}
        {connectionState !== 'connected' && (
          <div className="px-4 py-2 bg-yellow-50 text-yellow-800 text-sm">
            {connectionState === 'connecting' ? 'Connecting...' : 'Disconnected'}
          </div>
        )}

        <CommandInput
          onSend={handleSendMessage}
          onTyping={sendTypingIndicator}
          projectId={projectId}
        />
      </div>

      {/* Code Editor Panel */}
      <div className="w-1/2 flex flex-col">
        <div className="flex items-center justify-between px-4 py-2 bg-gray-100 border-b">
          <div className="flex items-center space-x-4">
            <select
              value={editorLanguage}
              onChange={(e) => setEditorLanguage(e.target.value)}
              className="text-sm border rounded px-2 py-1"
            >
              <option value="python">Python</option>
              <option value="javascript">JavaScript</option>
              <option value="typescript">TypeScript</option>
            </select>

            <button
              onClick={() => setShowDiff(!showDiff)}
              className={`text-sm px-3 py-1 rounded ${
                showDiff ? 'bg-blue-500 text-white' : 'bg-white border'
              }`}
            >
              Diff View
            </button>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => navigator.clipboard.writeText(editorContent)}
              className="text-sm text-gray-600 hover:text-gray-900"
              title="Copy code"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            </button>
          </div>
        </div>

        <div className="flex-1">
          <MonacoEditor
            value={editorContent}
            language={editorLanguage}
            onChange={setEditorContent}
            theme="vs-dark"
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              wordWrap: 'on',
              automaticLayout: true
            }}
          />
        </div>

        {/* Code preview for selected message */}
        {selectedMessage?.code_snippets && (
          <CodePreview
            snippets={selectedMessage.code_snippets}
            onApply={applyCodeSuggestion}
          />
        )}
      </div>
    </div>
  );
}
