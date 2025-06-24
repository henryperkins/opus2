import React, { useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

// Data hooks
import { useChat } from '../hooks/useChat';
import { useProject } from '../hooks/useProjects';
import { useUser } from '../hooks/useAuth';
import { useCodeExecutor } from '../hooks/useCodeExecutor';
import { useKnowledgeChat } from '../hooks/useKnowledgeContext';

// Responsive helper
import useMediaQuery from '../hooks/useMediaQuery';

// UI components
import EnhancedMessageRenderer from '../components/chat/EnhancedMessageRenderer';
import EnhancedCommandInput from '../components/chat/EnhancedCommandInput';
import KnowledgeAssistant from '../components/chat/KnowledgeAssistant';
import ResponsiveSplitPane from '../components/common/ResponsiveSplitPane';
import MobileBottomSheet from '../components/common/MobileBottomSheet';
import ConnectionIndicator from '../components/common/ConnectionIndicator';

// Icons
import { Brain } from 'lucide-react';

export default function ProjectChatPage() {
  // -------------------------------------------------------------
  // Routing / identifiers
  // -------------------------------------------------------------
  const { projectId, sessionId: urlSessionId } = useParams();
  const navigate = useNavigate();

  // -------------------------------------------------------------
  // Responsive helpers
  // -------------------------------------------------------------
  const { isMobile } = useMediaQuery();

  // -------------------------------------------------------------
  // Data hooks
  // -------------------------------------------------------------
  const user = useUser();

  const { project, loading: projectLoading } = useProject(projectId);

  const {
    messages,
    sendMessage,
    connectionState,
    typingUsers,
    sendTypingIndicator,
    streamingMessages,
  } = useChat(projectId, urlSessionId);

  const { executeCode, results: executionResults } = useCodeExecutor(projectId);
  const knowledgeChat = useKnowledgeChat(projectId);

  // -------------------------------------------------------------
  // Local UI state
  // -------------------------------------------------------------
  const [editorContent, setEditorContent] = useState('');
  const [editorLanguage, setEditorLanguage] = useState('python');
  const [currentFile, setCurrentFile] = useState();

  const [showKnowledgeAssistant, setShowKnowledgeAssistant] = useState(true);

  // -------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------
  const handleCodeExecution = useCallback(async (code, language, messageId) => {
    try {
      return await executeCode(code, language, projectId, messageId);
    } catch (err) {
      console.error('Code execution failed:', err);
      return { output: '', error: err.message || 'Execution failed', execution_time: 0 };
    }
  }, [executeCode, projectId]);

  const handleCodeApply = useCallback((code, language) => {
    setEditorContent(code);
    setEditorLanguage(language || 'python');
  }, []);

  const handleSendMessage = useCallback(async (content, metadata = {}) => {
    // Include editor context if referenced
    if (content.includes('@editor') && editorContent) {
      metadata.code_snippets = [
        { language: editorLanguage, code: editorContent, file_path: currentFile || 'editor' },
      ];
    }

    // Include knowledge context if present
    if (knowledgeChat.currentContext.length) {
      metadata.referenced_chunks = knowledgeChat.currentContext.map((c) => c.id);
      metadata.referenced_files = [
        ...new Set(knowledgeChat.currentContext.map((c) => c.file_path).filter(Boolean)),
      ];
    }

    await sendMessage(content, metadata);
  }, [sendMessage, editorContent, editorLanguage, currentFile, knowledgeChat]);

  const handleSearchResultSelect = useCallback((result) => {
    knowledgeChat.addToCitations([result]);
  }, [knowledgeChat]);

  // -------------------------------------------------------------
  // Render helpers
  // -------------------------------------------------------------
  const renderMessage = (msg) => {
    const streaming = streamingMessages.has(msg.id);
    const streamingContent = streamingMessages.get(msg.id);
    const executionResult = executionResults.get(msg.id);

    return (
      <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} mb-4`}>
        <div
          className={`max-w-3xl rounded-lg px-4 py-3 ${
            msg.role === 'user' ? 'bg-blue-600 text-white dark:bg-blue-500' : 'bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-100'
          }`}
        >
          {streaming ? (
            <div className="space-y-2">
              <div className="text-sm opacity-75">AI Assistant (streaming…)</div>
              <div className="whitespace-pre-wrap">
                {streamingContent?.content || ''}
                <span className="inline-block w-2 h-4 bg-blue-500 ml-0.5 animate-pulse" />
              </div>
            </div>
          ) : (
            <EnhancedMessageRenderer
              message={msg}
              content={msg.content}
              metadata={msg.metadata}
              onCodeRun={(code, lang) => handleCodeExecution(code, lang, msg.id)}
              onCodeApply={handleCodeApply}
              executionResult={executionResult}
            />
          )}
        </div>
      </div>
    );
  };

  // -------------------------------------------------------------
  // Early states
  // -------------------------------------------------------------
  if (projectLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-gray-500">Loading project…</div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex items-center justify-center h-screen text-center">
        <div>
          <h2 className="text-xl font-semibold mb-2">Project not found</h2>
          <button onClick={() => navigate('/projects')} className="text-blue-600 hover:underline">
            Back to projects
          </button>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------
  // Panels
  // -------------------------------------------------------------
  const chatPanel = (
    <section className="flex flex-col h-full" aria-label="Project chat">
      <div className="flex-1 overflow-y-auto p-4">
        {messages.length ? (
          messages.map(renderMessage)
        ) : (
          <div className="text-center text-gray-500 mt-8">
            <p>Start a conversation about {project.title}</p>
            <p className="text-sm mt-2">Use @editor to reference editor contents.</p>
          </div>
        )}

        {typingUsers.size > 0 && (
          <div className="text-sm text-gray-500 italic ml-2">
            {typingUsers.size} user{typingUsers.size > 1 ? 's' : ''} typing…
          </div>
        )}
      </div>

      <footer className="border-t bg-white dark:bg-gray-900/50">
        <EnhancedCommandInput
          onSend={handleSendMessage}
          onTyping={sendTypingIndicator}
          projectId={projectId}
          editorContent={editorContent}
          currentFile={currentFile}
          userId={user?.id}
        />
      </footer>
    </section>
  );

  const assistantPanel = (
    <KnowledgeAssistant
      projectId={projectId}
      onSearchSelect={handleSearchResultSelect}
      showEditor
      editorContent={editorContent}
      onEditorChange={setEditorContent}
      editorLanguage={editorLanguage}
      onLanguageChange={setEditorLanguage}
    />
  );

  // -------------------------------------------------------------
  // Render
  // -------------------------------------------------------------
  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-800">
      {/* Header */}
      <header className="border-b bg-white dark:bg-gray-900 dark:border-gray-700 px-4 py-3 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-xl font-semibold truncate max-w-xs sm:max-w-none">{project.title}</h1>
            <ConnectionIndicator state={connectionState} />
          </div>

          <button
            onClick={() => setShowKnowledgeAssistant((v) => !v)}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg touch-safe"
            aria-label="Toggle Knowledge Assistant"
          >
            <Brain className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 overflow-hidden">
        {isMobile ? (
          <>
            {chatPanel}
            <MobileBottomSheet
              isOpen={showKnowledgeAssistant}
              onClose={() => setShowKnowledgeAssistant(false)}
              title="Knowledge Assistant"
              snapPoints={[0.4, 0.9]}
              initialSnap={0.9}
            >
              {assistantPanel}
            </MobileBottomSheet>
          </>
        ) : (
          <ResponsiveSplitPane left={chatPanel} right={assistantPanel} />
        )}
      </main>
    </div>
  );
}
