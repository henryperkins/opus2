// pages/EnhancedProjectChatPage.tsx
/* global navigator */
import React, { useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useChat } from '../hooks/useChat';
import { useProject } from '../hooks/useProjects';
import { useUser } from '../hooks/useAuth';
import Header from '../components/common/Header';
import EnhancedMessageRenderer from '../components/chat/EnhancedMessageRenderer';
import CommandInput from '../components/chat/CommandInput';
import KnowledgeAssistant from '../components/chat/KnowledgeAssistant';
import MonacoEditor from '@monaco-editor/react';
import SplitPane from '../components/common/SplitPane';
import { Brain, Settings, FileText } from 'lucide-react';

export default function EnhancedProjectChatPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const user = useUser();
  const { project, loading: projectLoading } = useProject(projectId);

  // Chat state
  const {
    messages,
    connectionState,
    typingUsers,
    sendMessage,
    editMessage,
    deleteMessage,
    sendTypingIndicator
  } = useChat(projectId);

  // UI state
  const [splitView, setSplitView] = useState(true);
  const [showKnowledgeAssistant, setShowKnowledgeAssistant] = useState(true);
  const [editorContent, setEditorContent] = useState('');
  const [editorLanguage, setEditorLanguage] = useState('python');
  const [selectedText, setSelectedText] = useState('');
  const [currentFile, setCurrentFile] = useState(undefined);

  // Enhanced message handling with knowledge context
  const handleSendMessage = useCallback(async (content, metadata) => {
    try {
      // Add editor context if requested
      if (content.includes('@editor') && editorContent) {
        metadata.code_snippets = [{
          language: editorLanguage,
          code: editorContent,
          file_path: currentFile || 'editor'
        }];
      }

      // Send message with enhanced metadata
      await sendMessage(content, metadata);
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  }, [sendMessage, editorContent, editorLanguage, currentFile]);

  // Handle code application from chat
  const handleCodeApply = useCallback((code, language) => {
    setEditorContent(code);
    setEditorLanguage(language);
  }, []);

  // Handle citation clicks
  const handleCitationClick = useCallback((citation) => {
    // Navigate to the source or open in editor
    console.log('Citation clicked:', citation);
    // Implementation depends on your routing/file system
  }, []);

  // Handle knowledge suggestions
  const handleSuggestionApply = useCallback((suggestion, citations) => {
    // Apply suggestion to the input or send directly
    const metadata = {};
    if (citations && citations.length > 0) {
      metadata.citations = citations;
    }

    handleSendMessage(suggestion, metadata);
  }, [handleSendMessage]);

  // Handle context addition from knowledge assistant
  const handleContextAdd = useCallback((context) => {
    console.log('Adding context:', context);
    // This could update the current message draft or add to metadata
  }, []);

  if (projectLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900">Project not found</h2>
          <button
            onClick={() => navigate('/projects')}
            className="mt-4 text-blue-600 hover:text-blue-800"
          >
            Back to Projects
          </button>
        </div>
      </div>
    );
  }

  const chatPanel = (
    <div className="flex flex-col h-full bg-white">
      {/* Chat Header */}
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <h2 className="text-lg font-semibold text-gray-900">
              {project.name} - AI Chat
            </h2>
            {connectionState !== 'connected' && (
              <span className="text-xs text-orange-600">
                {connectionState}
              </span>
            )}
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setShowKnowledgeAssistant(!showKnowledgeAssistant)}
              className={`p-2 rounded-lg transition-colors ${
                showKnowledgeAssistant
                  ? 'bg-blue-100 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              title="Toggle Knowledge Assistant"
            >
              <Brain className="w-5 h-5" />
            </button>
            <button
              onClick={() => setSplitView(!splitView)}
              className="p-2 text-gray-500 hover:text-gray-700 rounded-lg"
              title={splitView ? 'Hide editor' : 'Show editor'}
            >
              <FileText className="w-5 h-5" />
            </button>
            <button
              className="p-2 text-gray-500 hover:text-gray-700 rounded-lg"
              title="Settings"
            >
              <Settings className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${
              message.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            <div
              className={`max-w-3xl rounded-lg px-4 py-3 ${
                message.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              {/* Message header */}
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs opacity-75">
                  {message.role === 'assistant' ? 'AI Assistant' : 'You'}
                </span>
                {message.metadata?.model && (
                  <span className="text-xs opacity-75">
                    {message.metadata.model}
                  </span>
                )}
              </div>

              {/* Enhanced message content */}
              <EnhancedMessageRenderer
                message={{
                  id: message.id,
                  content: message.content,
                  role: message.role,
                  metadata: message.metadata,
                  codeBlocks: message.code_blocks
                }}
                onCodeApply={handleCodeApply}
                onCitationClick={handleCitationClick}
                showMetadata={message.role === 'assistant'}
              />
            </div>
          </div>
        ))}

        {/* Typing indicators */}
        {typingUsers.size > 0 && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg px-4 py-2">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Enhanced command input */}
      <CommandInput
        onSend={handleSendMessage}
        onTyping={sendTypingIndicator}
        projectId={projectId}
        editorContent={editorContent}
        selectedText={selectedText}
        currentFile={currentFile}
        userId={user?.id || ''}
      />
    </div>
  );

  const editorPanel = (
    <div className="flex flex-col h-full bg-white">
      {/* Editor Header */}
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className="text-sm font-medium text-gray-700">
              {currentFile || 'Untitled'}
            </span>
            <select
              value={editorLanguage}
              onChange={(e) => setEditorLanguage(e.target.value)}
              className="text-sm border rounded px-2 py-1"
            >
              <option value="python">Python</option>
              <option value="javascript">JavaScript</option>
              <option value="typescript">TypeScript</option>
              <option value="java">Java</option>
              <option value="go">Go</option>
              <option value="rust">Rust</option>
            </select>
          </div>
          <button
            onClick={() => navigator.clipboard.writeText(editorContent)}
            className="text-sm text-gray-600 hover:text-gray-900"
            title="Copy code"
          >
            Copy
          </button>
        </div>
      </div>

      {/* Monaco Editor */}
      <div className="flex-1">
        <MonacoEditor
          value={editorContent}
          language={editorLanguage}
          onChange={(value) => setEditorContent(value || '')}
          onMount={(editor) => {
            // Set up selection change handler
            editor.onDidChangeCursorSelection((e) => {
              const selection = editor.getModel()?.getValueInRange(e.selection);
              setSelectedText(selection || '');
            });
          }}
          theme="vs-dark"
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            wordWrap: 'on',
            automaticLayout: true,
            scrollBeyondLastLine: false
          }}
        />
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header />

      <div className="flex-1 flex overflow-hidden">
        {splitView ? (
          <SplitPane
            split="vertical"
            minSize={400}
            defaultSize="50%"
            resizerStyle={{
              background: '#e5e7eb',
              width: '4px',
              cursor: 'col-resize'
            }}
          >
            {chatPanel}
            {editorPanel}
          </SplitPane>
        ) : (
          chatPanel
        )}
      </div>

      {/* Knowledge Assistant */}
      <KnowledgeAssistant
        projectId={projectId}
        message={messages[messages.length - 1]?.content || ''}
        onSuggestionApply={handleSuggestionApply}
        onContextAdd={handleContextAdd}
        isVisible={showKnowledgeAssistant}
        position="right"
      />
    </div>
  );
}
