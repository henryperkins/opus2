import React, { useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

// Data hooks
import { useChat } from '../hooks/useChat';
import { useProject } from '../hooks/useProjects';
import { useUser } from '../hooks/useAuth';
import { useKnowledgeChat } from '../hooks/useKnowledgeContext';
import { useModelSelection, useModelPerformance } from '../hooks/useModelSelect';
import { useResponseQualityTracking } from '../components/analytics/ResponseQuality';

// UI and utility hooks
import useMediaQuery from '../hooks/useMediaQuery';

// Common components
import Header from '../components/common/Header';
import ResponsiveSplitPane from '../components/common/ResponsiveSplitPane';
import MobileBottomSheet from '../components/common/MobileBottomSheet';
import SkeletonLoader from '../components/common/SkeletonLoader';
import ErrorBoundary from '../components/common/ErrorBoundary';
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

// Model / settings components
import ModelSwitcher from '../components/chat/ModelSwitcher';
import PromptManager from '../components/settings/PromptManager';

// Analytics
import ResponseQuality from '../components/analytics/ResponseQuality';

// Icons
import { Brain, Settings, Search, BarChart2, Sparkles } from 'lucide-react';

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

export default function ChatPage() {
  // ---------------------------------------------------------------------------
  // Routing / identifiers
  // ---------------------------------------------------------------------------
  const { projectId } = useParams();
  const navigate = useNavigate();

  // ---------------------------------------------------------------------------
  // Global state & responsive helpers
  // ---------------------------------------------------------------------------
  const user = useUser();
  const { isMobile } = useMediaQuery();

  // ---------------------------------------------------------------------------
  // Project + chat data
  // ---------------------------------------------------------------------------
  const { project, loading: projectLoading } = useProject(projectId);

  const chat = useChat(projectId);
  const {
    messages,
    streamingMessages,
    sendMessage,
    sendTypingIndicator,
  } = chat;

  // ---------------------------------------------------------------------------
  // Knowledge, model & analytics hooks
  // ---------------------------------------------------------------------------
  const knowledgeChat = useKnowledgeChat(projectId);
  const modelSelection = useModelSelection();
  const [currentModel, setCurrentModel] = useState(modelSelection.currentModel);
  const modelPerformance = useModelPerformance(currentModel);
  useResponseQualityTracking(projectId); // side-effects only

  // ---------------------------------------------------------------------------
  // Local UI state
  // ---------------------------------------------------------------------------
  const [showKnowledgeAssistant, setShowKnowledgeAssistant] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const [showPromptManager, setShowPromptManager] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);

  // Editor context (for code snippets shared with assistant)
  const [editorContent, setEditorContent] = useState('');
  const [editorLanguage, setEditorLanguage] = useState('plaintext');
  const [currentFile, setCurrentFile] = useState();

  // ---------------------------------------------------------------------------
  // Message helpers
  // ---------------------------------------------------------------------------

  const handleSendMessage = useCallback(async (content, metadata = {}) => {
    const start = Date.now();

    // Model auto-selection
    const taskType = detectTaskType(content);
    const chosenModel = await modelSelection.autoSelectModel(taskType);
    if (chosenModel !== currentModel) setCurrentModel(chosenModel);

    // Assemble metadata
    const fullMeta = {
      ...metadata,
      taskType,
      model: chosenModel,
      timestamp: new Date().toISOString(),
    };

    if (content.includes('@editor') && editorContent) {
      fullMeta.code_snippets = [
        {
          language: editorLanguage,
          code: editorContent,
          file_path: currentFile || 'editor',
        },
      ];
    }

    try {
      const id = await sendMessage(content, fullMeta);
      modelPerformance.trackRequest(Date.now() - start, { input: content.length / 4, output: 0 }, false);
      return id;
    } catch (err) {
      modelPerformance.trackRequest(0, { input: 0, output: 0 }, true);
      throw err;
    }
  }, [sendMessage, modelSelection, currentModel, editorContent, editorLanguage, currentFile, modelPerformance]);

  // ---------------------------------------------------------------------------
  // Render helpers
  // ---------------------------------------------------------------------------

  const renderMessage = (msg) => {
    const streaming = streamingMessages.get(msg.id);

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
            <StreamingMessage messageId={msg.id} isStreaming content={streaming.content} />
          ) : msg.metadata?.citations?.length ? (
            <CitationRenderer text={msg.content} citations={msg.metadata.citations} inline />
          ) : (
            <EnhancedMessageRenderer
              message={msg}
              content={msg.content}
              metadata={msg.metadata}
              onCodeRun={() => {}}
              onCodeApply={(code, lang) => {
                setEditorContent(code);
                setEditorLanguage(lang);
              }}
            />
          )}

          {/* Interactive elements */}
          {msg.interactiveElements?.length > 0 && (
            <div className="mt-4">
              <InteractiveElements elements={msg.interactiveElements} onElementComplete={() => {}} />
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
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <SkeletonLoader type="websocket-connecting" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
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

  return (
    <div className="flex flex-col h-screen bg-gray-50 dark:bg-gray-900">
      <Header className="sticky top-0 z-20 bg-gray-50/90 dark:bg-gray-900/90 backdrop-blur">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-xl font-semibold truncate max-w-xs sm:max-w-none">
              {project.title}
            </h1>
            <ModelSwitcher compact={isMobile} currentModel={currentModel} onModelChange={setCurrentModel} />
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setShowKnowledgeAssistant(true)}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
              aria-label="Knowledge Assistant"
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
      </Header>

      {/* Main content */}
      <div className="flex-1">
        {isMobile ? (
          // --------------------------------------------------------------
          // Mobile view
          // --------------------------------------------------------------
          <div className="flex flex-col h-full overflow-hidden">
            {/* Message list */}
            <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
              {messages.map(renderMessage)}
            </div>

            {/* Knowledge assistant bottom sheet */}
            <MobileBottomSheet
              isOpen={showKnowledgeAssistant}
              onClose={() => setShowKnowledgeAssistant(false)}
              title="Knowledge Assistant"
              initialSnap={0.6}
              snapPoints={[0.4, 0.6, 0.9]}
            >
              <KnowledgeAssistant
                projectId={projectId}
                onSearchSelect={() => {}}
                showEditor
                editorContent={editorContent}
                onEditorChange={setEditorContent}
                editorLanguage={editorLanguage}
                onLanguageChange={setEditorLanguage}
              />
            </MobileBottomSheet>

            {/* Input */}
            <div className="border-t bg-white dark:bg-gray-900 dark:border-gray-700 px-2 pt-1 pb-2" style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}>
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
          // --------------------------------------------------------------
          // Desktop / tablet view
          // --------------------------------------------------------------
          <ResponsiveSplitPane split="vertical" minSize={300} defaultSize="70%">
            {/* Chat column */}
            <div className="flex flex-col h-screen">
              <div className="flex-1 overflow-y-auto px-4 py-6 max-w-3xl mx-auto">
                {messages.map(renderMessage)}
              </div>
              <div className="border-t bg-white">
                <div className="max-w-3xl mx-auto">
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
            </div>

            {/* Assistant / knowledge panel */}
            {showKnowledgeAssistant && (
              <KnowledgeAssistant
                projectId={projectId}
                onSearchSelect={() => {}}
                showEditor
                editorContent={editorContent}
                onEditorChange={setEditorContent}
                editorLanguage={editorLanguage}
                onLanguageChange={setEditorLanguage}
              />
            )}
          </ResponsiveSplitPane>
        )}
      </div>

      {/* Modals */}
      {showSearch && (
        <SmartKnowledgeSearch projectId={projectId} onSelect={() => {}} onClose={() => setShowSearch(false)} />
      )}

      {showPromptManager && (
        <PromptManager projectId={projectId} onClose={() => setShowPromptManager(false)} />
      )}
    </div>
  );
}
