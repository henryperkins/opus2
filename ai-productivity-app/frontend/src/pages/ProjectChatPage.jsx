import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useChat } from '../hooks/useChat';
import { useProject } from '../hooks/useProjects';
import { useUser } from '../hooks/useAuth';
import { useCodeExecutor } from '../hooks/useCodeExecutor';
import { useKnowledgeChat } from '../hooks/useKnowledgeContext';
import EnhancedMessageRenderer from '../components/chat/EnhancedMessageRenderer';
import EnhancedCommandInput from '../components/chat/EnhancedCommandInput';
import KnowledgeAssistant from '../components/chat/KnowledgeAssistant';
import MonacoEditor from '@monaco-editor/react';
import SplitPane from '../components/common/SplitPane';
import { Send, Brain, Code, FileText } from 'lucide-react';

export default function ProjectChatPage() {
  const { projectId, sessionId: urlSessionId } = useParams();
  const navigate = useNavigate();
  const user = useUser();
  const { project, loading: projectLoading } = useProject(projectId);
  const { 
    messages, 
    sendMessage, 
    connectionState, 
    typingUsers,
    sendTypingIndicator,
    streamingMessages 
  } = useChat(projectId, urlSessionId);
  
  // Centralised code execution hook – shared across components
  const { executeCode, results: executionResults } = useCodeExecutor(projectId);
  const knowledgeChat = useKnowledgeChat(projectId);

  // State
  const [editorContent, setEditorContent] = useState('');
  const [editorLanguage, setEditorLanguage] = useState('python');
  const [selectedText, setSelectedText] = useState('');
  const [currentFile, setCurrentFile] = useState();
  const [showKnowledgeAssistant, setShowKnowledgeAssistant] = useState(true);
  // Wrapper so EnhancedMessageRenderer gets a promise-like API identical to previous signature
  const handleCodeExecution = useCallback(
    async (code, language, messageId) => {
      try {
        const res = await executeCode(code, language, projectId, messageId);
        return res;
      } catch (error) {
        console.error('Code execution failed:', error);
        return {
          output: '',
          error: error.message || 'Execution failed',
          execution_time: 0,
        };
      }
    },
    [executeCode, projectId]
  );

  // Handle message sending with all metadata
  const handleSendMessage = useCallback(async (content, metadata = {}) => {
    try {
      // Add editor context if referenced
      if (content.includes('@editor') && editorContent) {
        metadata.code_snippets = [{
          language: editorLanguage,
          code: editorContent,
          file_path: currentFile || 'editor'
        }];
      }

      // Add knowledge context if available
      if (knowledgeChat.currentContext.length > 0) {
        metadata.knowledge_context = knowledgeChat.currentContext;
      }

      const messageId = await sendMessage(content, metadata);
      return messageId;
    } catch (error) {
      console.error('Failed to send message:', error);
      throw error;
    }
  }, [sendMessage, editorContent, editorLanguage, currentFile, knowledgeChat]);

  // Handle code apply from messages
  const handleCodeApply = useCallback((code, language) => {
    setEditorContent(code);
    setEditorLanguage(language || 'python');
  }, []);

  // Handle knowledge search result selection
  const handleSearchResultSelect = useCallback((result) => {
    knowledgeChat.addToCitations([result]);
    console.log('Added knowledge to context');
  }, [knowledgeChat]);

  // Render message with streaming support
  const renderMessage = (message) => {
    const isStreaming = streamingMessages.has(message.id);
    const streamingContent = streamingMessages.get(message.id);
    const executionResult = executionResults.get(message.id);

    return (
      <div
        key={message.id}
        className={`flex ${
          message.role === 'user' ? 'justify-end' : 'justify-start'
        } mb-4`}
      >
        <div
          className={`max-w-3xl ${
            message.role === 'user'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-900'
          } rounded-lg px-4 py-3`}
        >
          {isStreaming ? (
            <div className="space-y-2">
              <div className="text-sm opacity-75">AI Assistant (streaming...)</div>
              <div className="whitespace-pre-wrap">
                {streamingContent?.content || ''}
                <span className="inline-block w-2 h-4 bg-blue-500 ml-0.5 animate-pulse" />
              </div>
            </div>
          ) : (
            <EnhancedMessageRenderer
              message={message}
              content={message.content}
              metadata={message.metadata}
              onCodeRun={(code, language) => handleCodeExecution(code, language, message.id)}
              onCodeApply={handleCodeApply}
              executionResult={executionResult}
            />
          )}
        </div>
      </div>
    );
  };

  if (projectLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-gray-500">Loading project...</div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <h2 className="text-xl font-semibold mb-2">Project not found</h2>
          <button
            onClick={() => navigate('/projects')}
            className="text-blue-600 hover:underline"
          >
            Back to projects
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <div className="border-b bg-white px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-xl font-semibold">{project.title}</h1>
            <span className={`text-sm px-2 py-1 rounded ${
              connectionState === 'connected' 
                ? 'bg-green-100 text-green-700' 
                : connectionState === 'connecting'
                ? 'bg-yellow-100 text-yellow-700'
                : 'bg-red-100 text-red-700'
            }`}>
              {connectionState}
            </span>
          </div>
          
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setShowKnowledgeAssistant(!showKnowledgeAssistant)}
              className="p-2 hover:bg-gray-100 rounded-lg"
              aria-label="Toggle Knowledge Assistant"
            >
              <Brain className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        <SplitPane
          split="vertical"
          minSize={300}
          defaultSize="60%"
        >
          {/* Chat panel */}
          <div className="flex flex-col h-full">
            <div className="flex-1 overflow-y-auto p-4">
              {messages.length === 0 ? (
                <div className="text-center text-gray-500 mt-8">
                  <p>Start a conversation about your code</p>
                  <p className="text-sm mt-2">
                    Use @editor to reference the code editor content
                  </p>
                </div>
              ) : (
                messages.map(renderMessage)
              )}
              
              {/* Typing indicators */}
              {typingUsers.size > 0 && (
                <div className="text-sm text-gray-500 italic ml-2">
                  {typingUsers.size} user{typingUsers.size > 1 ? 's' : ''} typing...
                </div>
              )}
            </div>

            <div className="border-t bg-white">
              <EnhancedCommandInput
                onSend={handleSendMessage}
                onTyping={sendTypingIndicator}
                projectId={projectId}
                editorContent={editorContent}
                selectedText={selectedText}
                currentFile={currentFile}
                userId={user?.id}
              />
            </div>
          </div>

          {/* Right panel - Knowledge Assistant or Code Editor */}
          {showKnowledgeAssistant ? (
            <KnowledgeAssistant
              projectId={projectId}
              onSearchSelect={handleSearchResultSelect}
              showEditor={true}
              editorContent={editorContent}
              onEditorChange={setEditorContent}
              editorLanguage={editorLanguage}
              onLanguageChange={setEditorLanguage}
            />
          ) : (
            <div className="h-full flex flex-col">
              <div className="border-b px-4 py-2 bg-gray-50">
                <select
                  value={editorLanguage}
                  onChange={(e) => setEditorLanguage(e.target.value)}
                  className="text-sm border rounded px-2 py-1"
                >
                  <option value="python">Python</option>
                  <option value="javascript">JavaScript</option>
                  <option value="typescript">TypeScript</option>
                  <option value="java">Java</option>
                  <option value="cpp">C++</option>
                </select>
              </div>
              <div className="flex-1">
                <MonacoEditor
                  language={editorLanguage}
                  value={editorContent}
                  onChange={setEditorContent}
                  theme="vs-light"
                  options={{
                    minimap: { enabled: false },
                    fontSize: 14,
                    wordWrap: 'on'
                  }}
                />
              </div>
            </div>
          )}
        </SplitPane>
      </div>
    </div>
  );
}