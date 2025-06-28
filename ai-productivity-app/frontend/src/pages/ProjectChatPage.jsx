import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

// Data hooks
import { useChat } from '../hooks/useChat';
import { useProject } from '../hooks/useProjects';
import { useUser } from '../hooks/useAuth';
import { useCodeExecutor } from '../hooks/useCodeExecutor';
import { useResponseQualityTracking } from '../components/analytics/ResponseQuality';

// Context providers
import { useModelContext } from '../contexts/ModelContext';
import { useKnowledgeContext } from '../contexts/KnowledgeContext';

// UI and utility hooks
import useMediaQuery from '../hooks/useMediaQuery';

// Layout components
import ChatLayout from '../components/chat/ChatLayout';
import ChatHeader from '../components/chat/ChatHeader';

// Common components
import SkeletonLoader from '../components/common/SkeletonLoader';
import EmptyState from '../components/common/EmptyState';

// Knowledge-related components
import SmartKnowledgeSearch from '../components/knowledge/SmartKnowledgeSearch';
import KnowledgeAssistant from '../components/chat/KnowledgeAssistant';

// Chat experience components
import EnhancedCommandInput from '../components/chat/EnhancedCommandInput';
import StreamingMessage from '../components/chat/StreamingMessage';
import EnhancedMessageRenderer from '../components/chat/EnhancedMessageRenderer';
import InteractiveElements from '../components/chat/InteractiveElements';
import CitationRenderer from '../components/chat/CitationRenderer';
import ResponseTransformer from '../components/chat/ResponseTransformer';
import RAGStatusIndicator from '../components/chat/RAGStatusIndicator';
import SessionRAGBadge from '../components/chat/SessionRAGBadge';

// Model / settings components
import ModelSwitcher from '../components/chat/ModelSwitcher';
import PromptManager from '../components/settings/PromptManager';

// Editor components
import MonacoRoot from '../components/editor/MonacoRoot';

// Analytics
import ResponseQuality from '../components/analytics/ResponseQuality';

// Icons
import { Sparkles } from 'lucide-react';

// Utils
import { toast } from '../components/common/Toast';

// Chat list component
import ProjectChatList from '../components/chat/ProjectChatList';
import { Link } from 'react-router-dom';
import LoadingSpinner from '../components/common/LoadingSpinner';

// ----------------------------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------------------------

function detectTaskType(content) {
  const text = content.toLowerCase();
  if (text.includes('explain') || text.includes('what is')) return 'knowledge';
  if (text.includes('generate') || text.includes('create')) return 'generation';
  if (text.includes('fix') || text.includes('debug')) return 'debugging';
  return 'general';
}

// ----------------------------------------------------------------------------------
// Main component
// ----------------------------------------------------------------------------------

export default function ProjectChatPage() {
  // ---------------------------------------------------------------------------
  // Routing / identifiers
  // ---------------------------------------------------------------------------
  const { projectId, sessionId: urlSessionId } = useParams();
  const navigate = useNavigate();

  // ---------------------------------------------------------------------------
  // Global state & responsive helpers
  // ---------------------------------------------------------------------------
  const user = useUser();

  // ---------------------------------------------------------------------------
  // Project + chat data
  // ---------------------------------------------------------------------------
  const { project, loading: projectLoading } = useProject(projectId);

  const {
    messages,
    sendMessage,
    connectionState,
    sendTypingIndicator,
    streamingMessages,
  } = useChat(projectId, urlSessionId);

  // ---------------------------------------------------------------------------
  // Knowledge, model & analytics hooks
  // ---------------------------------------------------------------------------
  const { executeCode, results: executionResults } = useCodeExecutor(projectId);

  // Use unified context providers instead of multiple hooks
  const {
    currentModel,
    setModel,
    autoSelectModel,
    trackPerformance
  } = useModelContext();

  const {
    addToCitations,
    clearCitations,
    currentContext,
    analyzeMessage
  } = useKnowledgeContext();

  useResponseQualityTracking(projectId); // side-effects only

  // ---------------------------------------------------------------------------
  // Local UI state
  // ---------------------------------------------------------------------------
  const [showKnowledgeAssistant, setShowKnowledgeAssistant] = useState(false); // Hidden by default, user can toggle
  const [showSearch, setShowSearch] = useState(false);
  const [showPromptManager, setShowPromptManager] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [showMonacoEditor, setShowMonacoEditor] = useState(false);

  // Editor context
  const [editorContent, setEditorContent] = useState('');
  const [editorLanguage, setEditorLanguage] = useState('python');
  const [currentFile, setCurrentFile] = useState();

  // Ref to access Monaco editor imperatively
  const monacoRef = useRef(null);
  const [panelSizes, setPanelSizes] = useState([]);

  // Refs for auto-scroll
  const messagesEndRef = useRef(null);
  const messageListRef = useRef(null);

  // -------------------------------------------------------------
  // Knowledge-assistant helpers – must run every render to keep
  // hook order stable (fixes “Rendered more hooks…” error)
  // -------------------------------------------------------------
  const handleSuggestionApply = useCallback(
    (suggestion, citations) => {
      setEditorContent(suggestion);
      if (citations?.length) addToCitations(citations);
    },
    [addToCitations]
  );

  const handleContextAdd = useCallback(
    (context) => {
      addToCitations([context]);
    },
    [addToCitations]
  );

  // ---------------------------------------------------------------------------
  // Callbacks
  // ---------------------------------------------------------------------------

  const handleCodeExecution = useCallback(async (code, language, messageId) => {
    try {
      return await executeCode(code, language, projectId, messageId);
    } catch (err) {
      console.error('Code execution failed:', err);
      toast.error(`Code execution failed: ${err.message || 'Unknown error'}`);
      return { output: '', error: err.message || 'Execution failed', execution_time: 0 };
    }
  }, [executeCode, projectId]);

  const handleCodeApply = useCallback((code, language) => {
    setEditorContent(code);
    setEditorLanguage(language || 'python');
  }, []);

  const handleSendMessage = useCallback(async (content, metadata = {}) => {
    // Check connection state before sending
    if (connectionState !== 'connected') {
      toast.error('Cannot send message: Not connected to server');
      return;
    }

    const start = Date.now();

    // Model auto-selection using unified context
    const taskType = detectTaskType(content);
    const chosenModel = await autoSelectModel(taskType, { content });

    // Assemble metadata
    const fullMeta = {
      ...metadata,
      taskType,
      model: chosenModel,
      timestamp: new Date().toISOString(),
    };

    // Include editor context if referenced
    if (content.includes('@editor') && editorContent) {
      fullMeta.code_snippets = [
        { language: editorLanguage, code: editorContent, file_path: currentFile || 'editor' },
      ];
    }

    // Include knowledge context if present using unified context
    if (currentContext.length) {
      fullMeta.referenced_chunks = currentContext.map((c) => c.id || c.source);
      fullMeta.referenced_files = [
        ...new Set(currentContext.map((c) => c.source || c.file_path).filter(Boolean)),
      ];
    }

    // Analyze message for knowledge suggestions
    analyzeMessage(content, projectId);

    try {
      const id = await sendMessage(content, fullMeta);

      // Track performance using unified context
      trackPerformance(chosenModel, {
        responseTime: Date.now() - start,
        inputTokens: Math.ceil(content.length / 4),
        outputTokens: 0 // Will be updated when response completes
      });

      return id;
    } catch (err) {
      // Track error using unified context
      trackPerformance(chosenModel, {
        responseTime: 0,
        inputTokens: 0,
        outputTokens: 0
      }, err.message);
      toast.error(`Failed to send message: ${err.message || 'Unknown error'}`);
      throw err;
    }
  }, [sendMessage, autoSelectModel, editorContent, editorLanguage, currentFile, currentContext, analyzeMessage, projectId, trackPerformance, connectionState]);

  const handleSearchResultSelect = useCallback((result) => {
    // Use unified knowledge context instead of separate hook
    addToCitations([result]);
    // Optionally close the panel/modal after selection
    setShowSearch(false);
  }, [addToCitations]);

  const handleInteractiveElement = useCallback(async (elementId, result) => {
    try {
      console.log('Interactive element completed:', { elementId, result });

      // Track analytics for interactive element usage
      // TODO: Send analytics data to backend

      // Handle post-completion actions based on element type or result
      if (result && result.type) {
        switch (result.type) {
          case 'code_execution':
            // Code execution completed, result contains output/error
            console.log('Code execution result:', result);
            break;

          case 'form_submission':
            // Form was submitted, result contains form data
            console.log('Form submission result:', result);
            // TODO: Send form data to backend for processing
            break;

          case 'decision_made':
            // Decision tree selection made
            console.log('Decision result:', result);
            break;

          case 'query_built':
            // Query builder completed
            console.log('Query result:', result);
            break;

          case 'action_triggered':
            // Action button was clicked
            console.log('Action result:', result);
            break;

          default:
            console.log('Generic interactive element result:', result);
        }
      }

      // Return success to indicate handling completed
      return { success: true };

    } catch (error) {
      console.error('Interactive element handling failed:', error);
      toast.error(`Interactive element failed: ${error.message || 'Unknown error'}`);
      return {
        success: false,
        error: error.message || 'Interactive element handling failed'
      };
    }
  }, []);

  const handleCitationClick = useCallback((citation) => {
    // Open knowledge assistant if not already open
    if (!showKnowledgeAssistant) {
      setShowKnowledgeAssistant(true);
    }

    // Add citation to context
    addToCitations([citation]);

    // TODO: Could also switch to context tab if in another tab
  }, [showKnowledgeAssistant, addToCitations]);

  // Smart auto-scroll helper - only scrolls if user is near bottom
  const scrollToBottom = useCallback(() => {
    if (messageListRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = messageListRef.current;
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 100; // Within 100px of bottom

      if (isNearBottom) {
        messageListRef.current.scrollTop = messageListRef.current.scrollHeight;
      }
    }
  }, []);

  // Auto-scroll to bottom when messages or streaming updates arrive (only if user is at bottom)
  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingMessages, scrollToBottom]);

  // Re-layout Monaco editor when its container size changes
  useEffect(() => {
    monacoRef.current?.layout();
  }, [showMonacoEditor, panelSizes]);

  // ---------------------------------------------------------------------------
  // Render helpers
  // ---------------------------------------------------------------------------

  const renderTypingIndicator = () => (
    <div className="flex justify-start mb-6">
      <div className="max-w-3xl rounded-lg px-4 py-3 bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-100">
        <div className="flex items-center space-x-2">
          <div className="flex space-x-1">
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
          </div>
          <span className="text-sm text-gray-500">AI is typing...</span>
        </div>
      </div>
    </div>
  );

  // Memoized message component to prevent unnecessary re-renders
  const MessageItem = React.memo(({ msg, streaming, executionResult }) => {
    return (
      <div className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} mb-6`}>
        <div
          className={`max-w-3xl rounded-lg px-4 py-3 ${
            msg.role === 'user'
              ? 'bg-blue-600 text-white dark:bg-blue-500'
              : 'bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-100'
          }`}
        >
          {/* Header row */}
          <div className="flex items-center justify-between mb-2 text-xs opacity-75">
            <span>{msg.role === 'assistant' ? 'AI Assistant' : 'You'}</span>
            {msg.metadata?.model && (
              <span className="flex items-center space-x-1">
                <Sparkles className="w-3 h-3" />
                <span>{msg.metadata.model}</span>
              </span>
            )}
          </div>

          {/* RAG Status Indicator for assistant messages */}
          {msg.role === 'assistant' && (
            <div className="mb-3">
              <RAGStatusIndicator
                ragUsed={msg.metadata?.ragUsed || false}
                sourcesCount={msg.metadata?.citations?.length || 0}
                confidence={msg.metadata?.ragConfidence}
                searchQuery={msg.metadata?.searchQuery}
                contextTokensUsed={msg.metadata?.contextTokensUsed}
                status={msg.metadata?.ragStatus}
                errorMessage={msg.metadata?.ragError}
              />
            </div>
          )}

          {/* Body */}
          {streaming ? (
            <StreamingMessage messageId={msg.id} isStreaming={streaming.isStreaming} content={streaming.content} />
          ) : msg.metadata?.citations?.length ? (
            <CitationRenderer text={msg.content} citations={msg.metadata.citations} inline onCitationClick={handleCitationClick} />
          ) : (
            <EnhancedMessageRenderer
              message={msg}
              content={msg.content}
              metadata={msg.metadata}
              onCodeRun={(code, lang) => handleCodeExecution(code, lang, msg.id)}
              onCodeApply={handleCodeApply}
              executionResult={executionResult}
              onCitationClick={handleCitationClick}
            />
          )}

          {/* Interactive elements */}
          {msg.interactiveElements?.length > 0 && (
            <div className="mt-4">
              <InteractiveElements
                elements={msg.interactiveElements}
                onElementComplete={handleInteractiveElement}
                codeExecutor={handleCodeExecution}
              />
            </div>
          )}

          {/* Quality / transforms */}
          {msg.role === 'assistant' && !streaming && (
            <div className="mt-4 pt-3 border-t border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <ResponseTransformer content={msg.content} allowedTransforms={[]} />
                <ResponseQuality messageId={msg.id} content={msg.content} showDetailedMetrics={showAnalytics} />
              </div>
            </div>
          )}
        </div>
      </div>
    );
  });

  const renderMessage = useCallback((msg) => {
    const streaming = streamingMessages.get(msg.id);
    const executionResult = executionResults.get(msg.id);

    return (
      <MessageItem
        key={msg.id}
        msg={msg}
        streaming={streaming}
        executionResult={executionResult}
      />
    );
  }, [streamingMessages, executionResults, handleCitationClick, handleCodeExecution, handleCodeApply, handleInteractiveElement, showAnalytics]);

  // ----------------------------------------------------------------------------------
  // Early states (loading / not-found)
  // ----------------------------------------------------------------------------------

  if (projectLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <SkeletonLoader type="websocket-connecting" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex items-center justify-center h-64">
        <EmptyState
          type="projects"
          title="Project not found"
          description="The requested project could not be found or you don't have access to it."
          action={{ label: 'Back to Projects', onClick: () => navigate('/projects') }}
        />
      </div>
    );
  }

  // ----------------------------------------------------------------------------------
  // If no sessionId in URL, show the chat list
  // ----------------------------------------------------------------------------------
  if (!urlSessionId) {
    return (
      <div className="h-full bg-gray-50 dark:bg-gray-900">
        <div className="max-w-4xl mx-auto p-6">
          {/* Project Header */}
          <div className="mb-6">
            <Link 
              to={`/projects/${projectId}`}
              className="text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 mb-2 inline-block"
            >
              ← Back to Project
            </Link>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {project?.name || 'Project'} - Chats
            </h1>
          </div>

          {/* Chat List */}
          <ProjectChatList projectId={projectId} project={project} />
        </div>
      </div>
    );
  }

  // ----------------------------------------------------------------------------------
  // Main render
  // ----------------------------------------------------------------------------------

  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-gray-900 overflow-hidden">
      {/* Chat Header */}
      <ChatHeader
        project={project}
        connectionState={connectionState}
        messages={messages}
        showKnowledgeAssistant={showKnowledgeAssistant}
        showEditor={showMonacoEditor}
        onToggleKnowledge={() => setShowKnowledgeAssistant(!showKnowledgeAssistant)}
        onToggleEditor={() => setShowMonacoEditor(!showMonacoEditor)}
        onOpenSearch={() => setShowSearch(true)}
        onOpenPromptManager={() => setShowPromptManager(true)}
        onToggleAnalytics={() => setShowAnalytics(v => !v)}
      />

      {/* Main Layout */}
      <ChatLayout
        showSidebar={showKnowledgeAssistant}
        showEditor={showMonacoEditor}
        onSidebarClose={() => setShowKnowledgeAssistant(false)}
        onEditorClose={() => setShowMonacoEditor(false)}
        onLayout={setPanelSizes}
        sidebar={
          <KnowledgeAssistant
            projectId={projectId}
            onSuggestionApply={handleSuggestionApply}
            onContextAdd={handleContextAdd}
            containerMode="inline"
          />
        }
        editor={
          <div className="h-full p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Code Editor</h3>
            </div>
            <MonacoRoot
              ref={monacoRef}
              value={editorContent}
              onChange={setEditorContent}
              language={editorLanguage}
              height="100%"
              className="min-h-[200px]"
              filename={currentFile}
              enableCopilot={true}
            />
          </div>
        }
      >
        {/* Chat Interface */}
        <div className="flex flex-col h-full">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4" ref={messageListRef}>
            <div className="max-w-3xl mx-auto space-y-4">
              {messages.map(renderMessage)}
              {streamingMessages.size > 0 && messages.length === 0 && renderTypingIndicator()}
              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Input - Always visible */}
          <div className="sticky bottom-0 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 p-4">
            <EnhancedCommandInput
              onSend={handleSendMessage}
              onTyping={sendTypingIndicator}
              projectId={projectId}
              editorContent={editorContent}
              currentFile={currentFile}
              userId={user?.id}
            />
          </div>
        </div>
      </ChatLayout>

      {/* Modals */}
      {showSearch && (
        <SmartKnowledgeSearch
          projectId={projectId}
          onResultSelect={handleSearchResultSelect}
          onClose={() => setShowSearch(false)}
        />
      )}

      {showPromptManager && (
        <PromptManager
          projectId={projectId}
          onClose={() => setShowPromptManager(false)}
        />
      )}
    </div>
  );
}
