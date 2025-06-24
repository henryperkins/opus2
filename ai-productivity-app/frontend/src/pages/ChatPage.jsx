import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useChat } from '../hooks/useChat';
import { useProject } from '../hooks/useProjects';
import { useUser } from '../hooks/useAuth';
import { useKnowledgeChat } from '../hooks/useKnowledgeContext';
import { useModelSelection, useModelPerformance } from '../hooks/useModelSelect';
import { useResponseQualityTracking } from '../components/analytics/ResponseQuality';

// Components
import Header from '../components/common/Header';
import ResponsiveSplitPane from '../components/common/ResponsiveSplitPane';
import MobileBottomSheet from '../components/common/MobileBottomSheet';
import SkeletonLoader from '../components/common/SkeletonLoader';
import ErrorBoundary from '../components/common/ErrorBoundary';
import EmptyState from '../components/common/EmptyState';
import MonacoEditor from '@monaco-editor/react';

// Hooks
import useMediaQuery from '../hooks/useMediaQuery';

// Phase 1 - Knowledge Integration
import KnowledgeContextPanel from '../components/knowledge/KnowledgeContextPanel';
import SmartKnowledgeSearch from '../components/knowledge/SmartKnowledgeSearch';
import KnowledgeAssistant from '../components/chat/KnowledgeAssistant';
import EnhancedCommandInput from '../components/chat/EnhancedCommandInput';
import CitationRenderer from '../components/chat/CitationRenderer';

// Phase 2 - Model Configuration
import ModelSwitcher from '../components/chat/ModelSwitcher';
import PromptManager from '../components/settings/PromptManager';

// Phase 3 - Response Rendering
import StreamingMessage from '../components/chat/StreamingMessage';
import EnhancedMessageRenderer from '../components/chat/EnhancedMessageRenderer';
import InteractiveElements from '../components/chat/InteractiveElements';
import ResponseTransformer from '../components/chat/ResponseTransformer';
import ResponseQuality from '../components/analytics/ResponseQuality';

// Icons
import { Brain, Settings, Search, FileText, BarChart2, Sparkles } from 'lucide-react';

// Utility function to detect task type
function detectTaskType(content) {
  const lowerContent = content.toLowerCase();
  if (lowerContent.includes('explain') || lowerContent.includes('what is')) {
    return 'knowledge';
  } else if (lowerContent.includes('generate') || lowerContent.includes('create')) {
    return 'generation';
  } else if (lowerContent.includes('fix') || lowerContent.includes('debug')) {
    return 'debugging';
  }
  return 'general';
}

export default function ChatPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const user = useUser();
  const { isMobile, isTablet, isTouchDevice } = useMediaQuery();

  // Core hooks
  const projectData = useProject(projectId);
  const project = projectData.project;
  const projectLoading = projectData.loading;
  const chatData = useChat(projectId);
  const messages = chatData.messages;
  const connectionState = chatData.connectionState;
  const typingUsers = chatData.typingUsers;
  const sendMessage = chatData.sendMessage;
  const editMessage = chatData.editMessage;
  const deleteMessage = chatData.deleteMessage;
  const sendTypingIndicator = chatData.sendTypingIndicator;
  const streamingMessages = chatData.streamingMessages;

  // Knowledge integration
  const knowledgeChat = useKnowledgeChat(projectId);

  // Model configuration
  const modelSelection = useModelSelection();
  const [currentModel, setCurrentModel] = useState(modelSelection.currentModel);
  const modelPerformance = useModelPerformance(currentModel);

  // Response quality tracking
  const qualityTracking = useResponseQualityTracking(projectId);

  // UI State
  const [splitView, setSplitView] = useState(true);
  const [showKnowledgeAssistant, setShowKnowledgeAssistant] = useState(true);
  const [showKnowledgePanel, setShowKnowledgePanel] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const [showPromptManager, setShowPromptManager] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);

  // Editor state
  const [editorContent, setEditorContent] = useState('');
  const [editorLanguage, setEditorLanguage] = useState('python');
  const [selectedText, setSelectedText] = useState('');
  const [currentFile, setCurrentFile] = useState();

  // Message state
  const [messageQualities, setMessageQualities] = useState(new Map());

  // Enhanced message sending with all integrations
  const handleSendMessage = useCallback(async function(content, metadata) {
    const startTime = Date.now();

    try {
      // Auto-detect task type for model selection
      const taskType = detectTaskType(content);
      const newModel = await modelSelection.autoSelectModel(taskType);
      if (currentModel !== newModel) {
        console.log('Switched to optimal model for ' + taskType);
        setCurrentModel(newModel);
      }

      // Build enhanced metadata
      const enhancedMetadata = {
        model: currentModel,
        taskType: taskType,
        timestamp: new Date().toISOString()
      };
      for (var key in metadata) {
        if (metadata.hasOwnProperty(key)) {
          enhancedMetadata[key] = metadata[key];
        }
      }

      // Add editor context if referenced
      if (content.includes('@editor') && editorContent) {
        enhancedMetadata.code_snippets = [{
          language: editorLanguage,
          code: editorContent,
          file_path: currentFile || 'editor'
        }];
      }

      // Send message and wait for ID
      const messageId = await sendMessage(content, enhancedMetadata);

      // Track performance
      const responseTime = Date.now() - startTime;
      modelPerformance.trackRequest(
        responseTime,
        { input: content.length / 4, output: 0 }, // Will be updated when response completes
        false
      );

      return messageId;
    } catch (error) {
      console.error('Failed to send message:', error);
      modelPerformance.trackRequest(0, { input: 0, output: 0 }, true);
      throw error;
    }
  }, [sendMessage, editorContent, editorLanguage, currentFile, currentModel, modelSelection, modelPerformance]);

  // Handle interactive elements
  const handleInteractiveElement = useCallback(async function(element) {
    console.log('Interactive element:', element);
  }, []);

  // Handle knowledge search result selection
  const handleSearchResultSelect = useCallback((result) => {
    const citations = knowledgeChat.addToCitations([result]);
    console.log('Added to context');
    setShowSearch(false);
  }, [knowledgeChat]);

  // Handle response quality feedback
  const handleQualityFeedback = useCallback((messageId, feedback) => {
    console.log('Quality feedback:', messageId, feedback);
  }, []);

  // Render enhanced message with all features
  const renderMessage = (message) => {
    const isStreaming = streamingMessages.has(message.id);
    const streamingContent = streamingMessages.get(message.id);

    return (
      <div
        key={message.id}
        className={`flex ${
          message.role === 'user' ? 'justify-end' : 'justify-start'
        } mb-6`}
      >
        <div
          className={`max-w-3xl ${
            message.role === 'user'
              ? 'bg-blue-600 text-white dark:bg-blue-500'
              : 'bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-100'
          } rounded-lg px-4 py-3`}
        >
          {/* Message Header */}
          <div className="flex items-center justify-between mb-2 text-xs opacity-75">
            <span>{message.role === 'assistant' ? 'AI Assistant' : 'You'}</span>
            {message.metadata && message.metadata.model && (
              <span className="flex items-center space-x-1">
                <Sparkles className="w-3 h-3" />
                <span>{message.metadata.model}</span>
              </span>
            )}
          </div>

          {/* Message Content */}
          {isStreaming ? (
            <StreamingMessage
              messageId={message.id}
              isStreaming={true}
              content={streamingContent?.content || ''}
              model={message.metadata?.model || ''}
              onStop={() => console.log('Stop streaming')}
              onRetry={() => console.log('Retry streaming')}
            />
          ) : message.metadata?.citations?.length > 0 ? (
            <CitationRenderer
              text={message.content}
              citations={message.metadata.citations}
              inline={true}
            />
          ) : (
            <EnhancedMessageRenderer
              message={message}
              content={message.content}
              metadata={message.metadata}
              onCodeRun={handleInteractiveElement}
              onCodeApply={(code, language) => {
                setEditorContent(code);
                setEditorLanguage(language);
              }}
              onDiagramClick={(diagram) => console.log('Diagram clicked:', diagram)}
              onCitationClick={(citation) => console.log('Citation clicked:', citation)}
            />
          )}

          {/* Interactive Elements */}
          {message.interactiveElements?.length > 0 && (
            <div className="mt-4">
              <InteractiveElements
                elements={message.interactiveElements}
                onElementComplete={handleInteractiveElement}
              />
            </div>
          )}

          {/* Response Actions & Quality */}
          {message.role === 'assistant' && !isStreaming && (
            <div className="mt-4 pt-3 border-t border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <ResponseTransformer
                  content={message.content}
                  onTransform={(transformed, format) => {
                    console.log('Transformed:', format);
                  }}
                  allowedTransforms={[]}
                />

                <ResponseQuality
                  messageId={message.id}
                  content={message.content}
                  metadata={message.metadata}
                  onFeedback={(feedback) => handleQualityFeedback(message.id, feedback)}
                  showDetailedMetrics={showAnalytics}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  // Loading state with context-aware skeleton
  if (projectLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <ErrorBoundary>
          <div className="flex items-center justify-center min-h-screen">
            <SkeletonLoader
              type="websocket-connecting"
              className="max-w-md"
            />
          </div>
        </ErrorBoundary>
      </div>
    );
  }

  // Project not found with enhanced error state
  if (!project) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <ErrorBoundary>
          <div className="flex items-center justify-center min-h-screen">
            <EmptyState
              type="projects"
              title="Project not found"
              description="The requested project could not be found or you don't have access to it."
              action={{
                label: 'Back to Projects',
                onClick: () => navigate('/projects')
              }}
            />
          </div>
        </ErrorBoundary>
      </div>
    );
  }

  // Main chat interface
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <ErrorBoundary>
        {/* Header with model switcher */}
        <Header>
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center space-x-4">
              <h1 className="text-xl font-semibold">{project.title}</h1>
              <ModelSwitcher
                currentModel={currentModel}
                onModelChange={setCurrentModel}
                compact={isMobile}
              />
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => setShowKnowledgeAssistant(!showKnowledgeAssistant)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
                aria-label="Toggle Knowledge Assistant"
              >
                <Brain className="w-5 h-5" />
              </button>
              <button
                onClick={() => setShowSearch(!showSearch)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
                aria-label="Open Knowledge Search"
              >
                <Search className="w-5 h-5" />
              </button>
              <button
                onClick={() => setShowPromptManager(!showPromptManager)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
                aria-label="Open Prompt Manager"
              >
                <Settings className="w-5 h-5" />
              </button>
              <button
                onClick={() => setShowAnalytics(!showAnalytics)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
                aria-label="Toggle Analytics View"
              >
                <BarChart2 className="w-5 h-5" />
              </button>
            </div>
          </div>
        </Header>

        {/* Main content area */}
        <div className="flex-1">
          {isMobile ? (
            // Mobile layout with bottom sheet
            <div className="flex flex-col h-screen">
              <div className="flex-1 overflow-y-auto">
                <div className="px-4 py-6">
                  {messages.map(renderMessage)}
                </div>
              </div>

              <MobileBottomSheet
                isOpen={showKnowledgePanel}
                onClose={() => setShowKnowledgePanel(false)}
                title="Knowledge Context"
                initialSnap={0.5}
              >
                <KnowledgeContextPanel
                  projectId={projectId}
                  onSelect={handleSearchResultSelect}
                />
              </MobileBottomSheet>

              <div className="border-t bg-white dark:bg-gray-900 dark:border-gray-700">
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
          ) : (
            // Desktop layout with split pane
            <ResponsiveSplitPane
              split="vertical"
              minSize={300}
              defaultSize="70%"
              resizerStyle={{
                background: '#e5e7eb',
                cursor: 'col-resize',
                width: '4px'
              }}
            >
              {/* Chat panel */}
              <div className="flex flex-col h-screen">
                <div className="flex-1 overflow-y-auto">
                  <div className="max-w-3xl mx-auto px-4 py-6">
                    {messages.map(renderMessage)}
                  </div>
                </div>

                <div className="border-t bg-white">
                  <div className="max-w-3xl mx-auto">
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
              </div>

              {/* Knowledge/Editor panel */}
              {showKnowledgeAssistant && (
                <KnowledgeAssistant
                  projectId={projectId}
                  onSearchSelect={handleSearchResultSelect}
                  showEditor={true}
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
          <SmartKnowledgeSearch
            projectId={projectId}
            onSelect={handleSearchResultSelect}
            onClose={() => setShowSearch(false)}
          />
        )}

        {showPromptManager && (
          <PromptManager
            projectId={projectId}
            onClose={() => setShowPromptManager(false)}
          />
        )}
      </ErrorBoundary>
    </div>
  );
}