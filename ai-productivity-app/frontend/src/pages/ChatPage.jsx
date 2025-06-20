// pages/EnhancedChatPage.tsx
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
import SplitPane from '../components/common/SplitPane';
import MonacoEditor from '@monaco-editor/react';

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
import RichMessageRenderer from '../components/chat/RichMessageRenderer';
import InteractiveElements from '../components/chat/InteractiveElements';
import ResponseTransformer from '../components/chat/ResponseTransformer';
import ResponseQuality from '../components/analytics/ResponseQuality';

// Icons
import { Brain, Settings, Search, FileText, BarChart2, Sparkles } from 'lucide-react';

// Types
import { createCitation } from '../types/knowledge';

interface EnhancedMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant' | 'system';
  isStreaming?: boolean;
  metadata?: {
    model?: string;
    citations?: Citation[];
    contextSummary?: any;
    responseTime?: number;
    tokens?: {
      prompt: number;
      completion: number;
    };
  };
  interactiveElements?: any[];
}

export default function EnhancedChatPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const user = useUser();

  // Core hooks
  const { project, loading: projectLoading } = useProject(projectId!);
  const {
    messages,
    connectionState,
    typingUsers,
    sendMessage,
    editMessage,
    deleteMessage,
    sendTypingIndicator
  } = useChat(projectId!);

  // Knowledge integration
  const knowledgeChat = useKnowledgeChat(projectId!);

  // Model configuration
  const modelSelection = useModelSelection();
  const modelPerformance = useModelPerformance(modelSelection.currentModel);

  // Response quality tracking
  const qualityTracking = useResponseQualityTracking(projectId!);

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
  const [currentFile, setCurrentFile] = useState<string | undefined>();

  // Message state
  const [streamingMessages, setStreamingMessages] = useState<Map<string, string>>(new Map());
  const [messageQualities, setMessageQualities] = useState<Map<string, any>>(new Map());

  // Enhanced message sending with all integrations
  const handleSendMessage = useCallback(async (content: string, metadata: any) => {
    const startTime = Date.now();

    try {
      // Auto-detect task type for model selection
      const taskType = detectTaskType(content);
      if (modelSelection.currentModel !== await modelSelection.autoSelectModel(taskType)) {
        // Model was switched, notify user
        toast.info(`Switched to optimal model for ${taskType}`);
      }

      // Build enhanced metadata
      const enhancedMetadata = {
        ...metadata,
        model: modelSelection.currentModel,
        taskType,
        timestamp: new Date().toISOString()
      };

      // Add editor context if referenced
      if (content.includes('@editor') && editorContent) {
        enhancedMetadata.code_snippets = [{
          language: editorLanguage,
          code: editorContent,
          file_path: currentFile || 'editor'
        }];
      }

      // Send message
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
  }, [sendMessage, editorContent, editorLanguage, currentFile, modelSelection, modelPerformance]);

  // Handle streaming responses
  const handleStreamingUpdate = useCallback((messageId: string, chunk: string, done: boolean) => {
    if (done) {
      setStreamingMessages(prev => {
        const updated = new Map(prev);
        updated.delete(messageId);
        return updated;
      });
    } else {
      setStreamingMessages(prev => {
        const updated = new Map(prev);
        const current = updated.get(messageId) || '';
        updated.set(messageId, current + chunk);
        return updated;
      });
    }
  }, []);

  // Handle interactive elements
  const handleInteractiveElement = useCallback(async (element: any) => {
    // Process interactive element action
    console.log('Interactive element:', element);
  }, []);

  // Handle knowledge search result selection
  const handleSearchResultSelect = useCallback((result: any) => {
    // Add to citations and inject into context
    const citations = knowledgeChat.addToCitations([result]);
    toast.success('Added to context');
    setShowSearch(false);
  }, [knowledgeChat]);

  // Handle response quality feedback
  const handleQualityFeedback = useCallback((messageId: string, feedback: any) => {
    console.log('Quality feedback:', messageId, feedback);
    // Send feedback to backend
  }, []);

  // Render enhanced message with all features
  const renderMessage = (message: EnhancedMessage) => {
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
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-900'
          } rounded-lg px-4 py-3`}
        >
          {/* Message Header */}
          <div className="flex items-center justify-between mb-2 text-xs opacity-75">
            <span>{message.role === 'assistant' ? 'AI Assistant' : 'You'}</span>
            {message.metadata?.model && (
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
              content={streamingContent || ''}
              model={message.metadata?.model}
            />
          ) : message.metadata?.citations && message.metadata.citations.length > 0 ? (
            <CitationRenderer
              text={message.content}
              citations={message.metadata.citations}
              inline={true}
            />
          ) : (
            <RichMessageRenderer
              content={message.content}
              metadata={message.metadata}
              onCodeRun={handleInteractiveElement}
              onCodeApply={(code, language) => {
                setEditorContent(code);
                setEditorLanguage(language);
              }}
            />
          )}

          {/* Interactive Elements */}
          {message.interactiveElements && message.interactiveElements.length > 0 && (
            <div className="mt-4">
              <InteractiveElements
                elements={message.interactiveElements}
                onElementComplete={handleInteractiveElement}
              />
            </div>
          )}

          {/* Response Actions & Quality */}
          {message.role === 'assistant' && !isStreaming && (
            <div className="mt-4 pt-3 border-t border-gray-200">
              <div className="flex items-center justify-between">
                <ResponseTransformer
                  content={message.content}
                  onTransform={(transformed, format) => {
                    console.log('Transformed:', format);
                  }}
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
      {/* Chat Header with Controls */}
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <h2 className="text-lg font-semibold text-gray-900">
              {project.name} - Enhanced AI Chat
            </h2>
            {connectionState !== 'connected' && (
              <span className="text-xs text-orange-600">
                {connectionState}
              </span>
            )}
          </div>

          <div className="flex items-center space-x-2">
            {/* Model Switcher */}
            <ModelSwitcher
              compact
              onModelChange={(model) => console.log('Model changed:', model)}
            />

            {/* Feature Toggles */}
            <button
              onClick={() => setShowKnowledgePanel(!showKnowledgePanel)}
              className={`p-2 rounded-lg transition-colors ${
                showKnowledgePanel
                  ? 'bg-blue-100 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              title="Knowledge Context"
            >
              <FileText className="w-5 h-5" />
            </button>

            <button
              onClick={() => setShowKnowledgeAssistant(!showKnowledgeAssistant)}
              className={`p-2 rounded-lg transition-colors ${
                showKnowledgeAssistant
                  ? 'bg-blue-100 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              title="AI Assistant"
            >
              <Brain className="w-5 h-5" />
            </button>

            <button
              onClick={() => setShowSearch(true)}
              className="p-2 text-gray-500 hover:text-gray-700 rounded-lg"
              title="Search Knowledge Base"
            >
              <Search className="w-5 h-5" />
            </button>

            <button
              onClick={() => setShowAnalytics(!showAnalytics)}
              className={`p-2 rounded-lg transition-colors ${
                showAnalytics
                  ? 'bg-purple-100 text-purple-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              title="Analytics"
            >
              <BarChart2 className="w-5 h-5" />
            </button>

            <button
              onClick={() => setShowPromptManager(true)}
              className="p-2 text-gray-500 hover:text-gray-700 rounded-lg"
              title="Prompt Templates"
            >
              <Settings className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Knowledge Context Panel */}
      {showKnowledgePanel && (
        <div className="border-b border-gray-200 max-h-64 overflow-y-auto">
          <KnowledgeContextPanel
            query={knowledgeChat.activeQuery}
            projectId={projectId!}
            onDocumentSelect={(doc) => knowledgeChat.toggleItemSelection(doc.id)}
            onCodeSelect={(snippet) => knowledgeChat.toggleItemSelection(snippet.id)}
          />
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {messages.map((msg) => renderMessage(msg as EnhancedMessage))}

        {/* Typing indicators */}
        {typingUsers.size > 0 && (
          <div className="flex justify-start mb-6">
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

      {/* Enhanced Command Input */}
      <EnhancedCommandInput
        onSend={handleSendMessage}
        onTyping={sendTypingIndicator}
        projectId={projectId!}
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
        </div>
      </div>

      {/* Monaco Editor */}
      <div className="flex-1">
        <MonacoEditor
          value={editorContent}
          language={editorLanguage}
          onChange={(value) => setEditorContent(value || '')}
          onMount={(editor) => {
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
            automaticLayout: true
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

      {/* Floating Components */}

      {/* Knowledge Assistant */}
      <KnowledgeAssistant
        projectId={projectId!}
        message={messages[messages.length - 1]?.content || ''}
        onSuggestionApply={(suggestion, citations) => {
          handleSendMessage(suggestion, { citations });
        }}
        onContextAdd={(context) => {
          console.log('Context added:', context);
        }}
        isVisible={showKnowledgeAssistant}
        position="right"
      />

      {/* Search Modal */}
      {showSearch && (
        <SmartKnowledgeSearch
          projectId={projectId!}
          onResultSelect={handleSearchResultSelect}
          onClose={() => setShowSearch(false)}
        />
      )}

      {/* Prompt Manager Modal */}
      {showPromptManager && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-6xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-2xl font-bold">Prompt Templates</h2>
                <button
                  onClick={() => setShowPromptManager(false)}
                  className="text-gray-500 hover:text-gray-700"
                >
                  ✕
                </button>
              </div>
              <PromptManager />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Helper function to detect task type from message
function detectTaskType(message: string): string {
  const lower = message.toLowerCase();

  if (lower.includes('explain') || lower.includes('what is') || lower.includes('how does')) {
    return 'code-explanation';
  }
  if (lower.includes('generate') || lower.includes('create') || lower.includes('write')) {
    return 'code-generation';
  }
  if (lower.includes('debug') || lower.includes('error') || lower.includes('fix')) {
    return 'debugging';
  }
  if (lower.includes('test') || lower.includes('unit test')) {
    return 'testing';
  }
  if (lower.includes('document') || lower.includes('docs')) {
    return 'documentation';
  }
  if (lower.includes('architect') || lower.includes('design')) {
    return 'architecture';
  }

  return 'quick-answer';
}
