import React, { useState, useCallback, useRef, useEffect } from 'react';
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

// Common components
import ResponsiveSplitPane from '../components/common/ResponsiveSplitPane';
import MobileBottomSheet from '../components/common/MobileBottomSheet';
import SkeletonLoader from '../components/common/SkeletonLoader';
import EmptyState from '../components/common/EmptyState';
import ConnectionIndicator from '../components/common/ConnectionIndicator';

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

// Model / settings components
import ModelSwitcher from '../components/chat/ModelSwitcher';
import PromptManager from '../components/settings/PromptManager';

// Analytics
import ResponseQuality from '../components/analytics/ResponseQuality';

// Icons
import { Brain, Settings, Search, BarChart2, Sparkles } from 'lucide-react';

// Utils
import { toast } from '../components/common/Toast';

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
  const { isMobile, matchesQuery } = useMediaQuery();

  // Detect very large desktop screens (≥ 1536px)
  const isDesktopXL = matchesQuery('(min-width: 1536px)');

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
  const [showKnowledgeAssistant, setShowKnowledgeAssistant] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const [showPromptManager, setShowPromptManager] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);

  // Editor context
  const [editorContent, setEditorContent] = useState('');
  const [editorLanguage, setEditorLanguage] = useState('python');
  const [currentFile, setCurrentFile] = useState();

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

  // Auto-scroll helper
  const scrollToBottom = useCallback(() => {
    if (messageListRef.current) {
      messageListRef.current.scrollTop = messageListRef.current.scrollHeight;
    }
  }, []);

  // Auto-scroll to bottom when messages or streaming updates arrive
  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingMessages, scrollToBottom]);

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

  const renderMessage = (msg) => {
    const streaming = streamingMessages.get(msg.id);
    const executionResult = executionResults.get(msg.id);

    return (
      <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} mb-6`}>
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
  };

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
  // Main render
  // ----------------------------------------------------------------------------------


  // Create assistant panels for different contexts
  const desktopAssistantPanel = (
    <KnowledgeAssistant
      projectId={projectId}
      onSuggestionApply={handleSuggestionApply}
      onContextAdd={handleContextAdd}
      containerMode="overlay"
      position="right"
    />
  );

  const mobileAssistantPanel = (
    <KnowledgeAssistant
      projectId={projectId}
      onSuggestionApply={handleSuggestionApply}
      onContextAdd={handleContextAdd}
      containerMode="inline"
    />
  );

  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-gray-900 overflow-hidden">
      {/* Debug info */}
      <div className="text-red-500 p-2">
        DEBUG: Project: {project?.title || 'No project'}, Messages: {messages?.length || 0}
      </div>

      {/* Page header with project info and controls */}
      <div className="bg-white/90 dark:bg-gray-900/90 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center space-x-4">
            <h1 className="text-xl font-semibold truncate max-w-xs sm:max-w-none">
              {project?.title || 'Loading...'}
            </h1>
            <div>Connection: {connectionState}</div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setShowKnowledgeAssistant((v) => !v)}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
              aria-label="Toggle Knowledge Assistant"
            >
              <Brain className="w-5 h-5" />
            </button>
            <button
              onClick={() => setShowSearch(true)}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
              aria-label="Knowledge Search"
            >
              <Search className="w-5 h-5" />
            </button>
            <button
              onClick={() => setShowPromptManager(true)}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
              aria-label="Prompt Manager"
            >
              <Settings className="w-5 h-5" />
            </button>
            <button
              onClick={() => setShowAnalytics((v) => !v)}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
              aria-label="Toggle analytics view"
            >
              <BarChart2 className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Main content */}
      <main className="flex-1 overflow-hidden min-h-0 flex flex-col">
        {isMobile ? (
          <div className="flex flex-col h-full overflow-hidden">
            {/* Message list */}
            <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4" ref={messageListRef}>
              {messages.map(renderMessage)}
              {streamingMessages.size > 0 && messages.length === 0 && renderTypingIndicator()}
              <div ref={messagesEndRef} />
            </div>

            {/* Knowledge assistant bottom sheet */}
            <MobileBottomSheet
              isOpen={showKnowledgeAssistant}
              onClose={() => setShowKnowledgeAssistant(false)}
              title="Knowledge Assistant"
              initialSnap={0.6}
              snapPoints={[0.4, 0.6, 0.9]}
            >
              {mobileAssistantPanel}
            </MobileBottomSheet>

            {/* Input - fixed at bottom */}
            <div className="flex-shrink-0">
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
        ) : (
          <ResponsiveSplitPane
            orientation="vertical"
            minSize={25}
            defaultSize={`${isDesktopXL ? 60 : 70}%`}
            left={(
              <div className="flex flex-col h-full overflow-hidden">
                <div
                  className="flex-1 overflow-y-auto px-4 py-6 max-w-3xl mx-auto"
                  ref={messageListRef}
                >
                  {messages.map(renderMessage)}
                  {streamingMessages.size > 0 && messages.length === 0 && renderTypingIndicator()}
                  <div ref={messagesEndRef} />
                </div>
                <div className="flex-shrink-0">
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
            )}
            right={showKnowledgeAssistant ? desktopAssistantPanel : null}
            leftTitle="Chat"
            rightTitle="Knowledge Assistant"
          />
        )}
      </main>

      {/* Modals */}
      {showSearch && (
        <SmartKnowledgeSearch projectId={projectId} onResultSelect={handleSearchResultSelect} onClose={() => setShowSearch(false)} />
      )}

      {showPromptManager && (
        <PromptManager projectId={projectId} onClose={() => setShowPromptManager(false)} />
      )}

      {/* Root container closing tag */}
    </div>
  );
}
