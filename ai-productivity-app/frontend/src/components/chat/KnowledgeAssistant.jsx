// components/chat/KnowledgeAssistant.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { Brain, Search, X, ChevronRight, ChevronUp, ChevronDown, Sparkles, Upload, GitBranch, Network } from 'lucide-react';
import { useKnowledgeChat } from '../../hooks/useKnowledgeContext';
import { knowledgeAPI } from '../../api/knowledge';
import KnowledgeContextPanel from '../knowledge/KnowledgeContextPanel';
import SmartKnowledgeSearch from '../knowledge/SmartKnowledgeSearch';
import FileUpload from '../knowledge/FileUpload';
import RepositoryConnect from '../knowledge/RepositoryConnect';
import DependencyGraph from '../knowledge/DependencyGraph';
import PageErrorBoundary from '../common/PageErrorBoundary';

// Custom styles for scrollbar (Tailwind scrollbar plugin might not be available)
const scrollbarStyle = {
  scrollbarWidth: 'thin',
  scrollbarColor: '#CBD5E0 #F7FAFC',
};

function KnowledgeAssistantCore({
  projectId,
  message: incomingMessage,
  onSuggestionApply,
  onContextAdd,
  isVisible = true,
  position = 'right',
  containerMode = 'overlay' // 'overlay' for desktop, 'inline' for mobile
}) {
  // Normalise *message* so that downstream code always sees a *string*
  const message = typeof incomingMessage === 'string' ? incomingMessage : '';
  const {
    analyzeMutation,
    retrieveMutation,
    buildContextForQuery,
    addToCitations,
    clearCitations,
    citations,
    currentContext,
  } = useKnowledgeChat(projectId, {}, knowledgeAPI);

  // Initialize missing state locally since the hook doesn't provide them
  const [selectedItems, setSelectedItems] = useState(new Set());
  const [activeQuery, setActiveQuery] = useState('');
  const [context, setContext] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Helper functions for missing functionality
  const toggleItemSelection = useCallback((id) => {
    setSelectedItems(prev => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  }, []);

  const clearSelections = useCallback(() => {
    setSelectedItems(new Set());
  }, []);

  const updateContextFromChat = useCallback(async (message) => {
    if (!message || message.length < 10) return;

    setLoading(true);
    setActiveQuery(message);
    try {
      const result = await buildContextForQuery(message);
      setContext(result);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [buildContextForQuery]);

  const search = useCallback(async (query) => {
    setLoading(true);
    setActiveQuery(query);
    try {
      const result = await buildContextForQuery(query);
      setContext(result);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [buildContextForQuery]);

  const [showSearch, setShowSearch] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  // Allow minimize functionality
  const [isMinimized, setIsMinimized] = useState(false);
  const [activeTab, setActiveTab] = useState('context'); // 'context', 'upload', 'repository', 'graph'

  // Update context based on chat message
  useEffect(() => {
    if (message.length > 10) {
      updateContextFromChat(message);
    }
  }, [message, updateContextFromChat]);

  // Generate smart suggestions based on context
  useEffect(() => {
    if (context && context.confidence > 0.6) {
      const newSuggestions = generateSuggestions(context, message);
      setSuggestions(newSuggestions);
    } else {
      setSuggestions([]);
    }
  }, [context, message]);

  const handleDocumentSelect = useCallback((doc) => {
    toggleItemSelection(doc.id);
  }, [toggleItemSelection]);

  const handleCodeSelect = useCallback((snippet) => {
    toggleItemSelection(snippet.id);
  }, [toggleItemSelection]);

  const handleApplyContext = useCallback(() => {
    if (!context) return;

    // Get selected items
    const selectedDocs = context.relevantDocs.filter(doc => selectedItems.has(doc.id));
    const selectedCode = context.codeSnippets.filter(snippet => selectedItems.has(snippet.id));

    // Create citations
    const newCitations = addToCitations([...selectedDocs, ...selectedCode]);

    // Build context summary
    const contextSummary = {
      documents: selectedDocs.map(d => ({ id: d.id, title: d.title, path: d.path })),
      codeSnippets: selectedCode.map(s => ({ id: s.id, content: s.content.slice(0, 100) })),
      citations: newCitations
    };

    onContextAdd(contextSummary);
    clearSelections();
  }, [context, selectedItems, addToCitations, onContextAdd, clearSelections]);

  const handleSearchResult = useCallback((result) => {
    // Add search result to citations
    const newCitations = addToCitations([result]);
    onSuggestionApply(`Referenced: ${result.title}`, newCitations);
    setShowSearch(false);
  }, [addToCitations, onSuggestionApply]);

  const handleFileUploadSuccess = useCallback(() => {
    // Refresh embeddings after successful file upload
    if (context) {
      updateContextFromChat(message);
    }
  }, [context, message, updateContextFromChat]);

  if (!isVisible) return null;

  // Determine container styles based on mode
  const containerClass = containerMode === 'overlay'
    ? `fixed ${position === 'right' ? 'right-2 sm:right-4' : 'left-2 sm:left-4'} top-20 w-80 sm:w-96 z-50 max-h-[calc(var(--dvh)-6rem)]`
    : 'w-full h-full flex flex-col';

  const panelClass = containerMode === 'overlay'
    ? `bg-white rounded-lg shadow-xl border border-gray-200 overflow-hidden transition-all duration-300 ${
        isMinimized ? 'h-12' : 'h-auto max-h-full'
      }`
    : `bg-white border-t border-gray-200 overflow-hidden transition-all duration-300 flex-1 ${
        isMinimized ? 'h-12 flex-none' : 'flex flex-col'
      }`;

  return (
    <div className={containerClass}>
      {/* Main Assistant Panel */}
      <div className={panelClass}>
        {/* Header - Always expanded */}
        <div className="px-4 py-3 bg-gradient-to-r from-blue-500 to-purple-500 text-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Brain className="w-5 h-5" />
              <span className="font-medium">Knowledge Assistant</span>
              <div className="bg-white/20 px-2 py-0.5 rounded-full text-xs">
                {isMinimized ? 'Minimized' : 'Active'}
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setShowSearch(true)}
                className="p-1 hover:bg-white/20 rounded"
                title="Search knowledge base"
              >
                <Search className="w-4 h-4" />
              </button>
              <button
                onClick={() => setIsMinimized(!isMinimized)}
                className="p-1 hover:bg-white/20 rounded"
                title={isMinimized ? 'Expand' : 'Minimize'}
              >
                {isMinimized ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>
            </div>
          </div>
        </div>

        {/* Show content only when not minimized */}
        {!isMinimized && (
          <div>
            {/* Tab Navigation */}
            <div className="flex border-b border-gray-200 overflow-x-auto">
              <button
                onClick={() => setActiveTab('context')}
                className={`flex items-center px-3 sm:px-4 py-2 text-xs sm:text-sm font-medium whitespace-nowrap ${
                  activeTab === 'context'
                    ? 'text-blue-600 border-b-2 border-blue-600'
                    : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                <Search className="w-4 h-4 mr-1" />
                <span className="hidden sm:inline">Context</span>
              </button>
              <button
                onClick={() => setActiveTab('upload')}
                className={`flex items-center px-3 sm:px-4 py-2 text-xs sm:text-sm font-medium whitespace-nowrap ${
                  activeTab === 'upload'
                    ? 'text-blue-600 border-b-2 border-blue-600'
                    : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                <Upload className="w-4 h-4 mr-1" />
                <span className="hidden sm:inline">Upload</span>
              </button>
              <button
                onClick={() => setActiveTab('repository')}
                className={`flex items-center px-3 sm:px-4 py-2 text-xs sm:text-sm font-medium whitespace-nowrap ${
                  activeTab === 'repository'
                    ? 'text-blue-600 border-b-2 border-blue-600'
                    : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                <GitBranch className="w-4 h-4 mr-1" />
                <span className="hidden sm:inline">Repository</span>
              </button>
              <button
                onClick={() => setActiveTab('graph')}
                className={`flex items-center px-3 sm:px-4 py-2 text-xs sm:text-sm font-medium whitespace-nowrap ${
                  activeTab === 'graph'
                    ? 'text-blue-600 border-b-2 border-blue-600'
                    : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                <Network className="w-4 h-4 mr-1" />
                <span className="hidden sm:inline">Dependencies</span>
              </button>
            </div>

            {/* Tab Content */}
            <div 
              className={containerMode === 'overlay' 
                ? "overflow-y-auto max-h-[calc(70vh-8rem)]" 
                : "flex-1 overflow-auto"}
              style={containerMode === 'overlay' ? scrollbarStyle : undefined}>
              {/* Context Tab */}
              {activeTab === 'context' && (
                <>
                  {/* Active Query Indicator */}
                  {activeQuery && (
                    <div className="px-4 py-2 bg-blue-50 border-b border-blue-100">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-blue-700">
                          Searching: "{activeQuery}"
                        </span>
                        {loading && (
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Suggestions */}
                  {suggestions.length > 0 && (
                    <div className="p-4 border-b border-gray-200">
                      <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center">
                        <Sparkles className="w-4 h-4 mr-1 text-yellow-500" />
                        Smart Suggestions
                      </h4>
                      <div className="space-y-2">
                        {suggestions.map((suggestion, idx) => (
                          <button
                            key={idx}
                            onClick={() => onSuggestionApply(suggestion, citations)}
                            className="w-full text-left px-3 py-2 text-sm bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors"
                          >
                            {suggestion}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Knowledge Context */}
                  <div className={containerMode === 'overlay' ? "max-h-96" : "flex-1"}>
                    <KnowledgeContextPanel
                      query={activeQuery}
                      projectId={projectId}
                      onDocumentSelect={handleDocumentSelect}
                      onCodeSelect={handleCodeSelect}
                      className="h-full"
                      maxHeight={containerMode === 'overlay' ? "300px" : undefined}
                    />
                  </div>

                  {/* Actions */}
                  {selectedItems && selectedItems.size > 0 && (
                    <div className="px-4 py-3 border-t border-gray-200 bg-gray-50">
                      <button
                        onClick={handleApplyContext}
                        className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                      >
                        Add {selectedItems.size} item{selectedItems.size > 1 ? 's' : ''} as context
                      </button>
                    </div>
                  )}
                </>
              )}

              {/* Upload Tab */}
              {activeTab === 'upload' && (
                <div className="p-4">
                  <FileUpload
                    projectId={projectId}
                    onSuccess={handleFileUploadSuccess}
                  />
                </div>
              )}

              {/* Repository Tab */}
              {activeTab === 'repository' && (
                <div className="p-4">
                  <RepositoryConnect
                    projectId={projectId}
                    onConnectSuccess={() => {
                      // Refresh context after repository connection
                      updateContextFromChat(message);
                    }}
                  />
                </div>
              )}

              {/* Dependencies Tab */}
              {activeTab === 'graph' && (
                <div className={`p-4 ${containerMode === 'overlay' ? 'h-96' : 'h-full'}`}>
                  <DependencyGraph projectId={projectId} />
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Search Modal */}
      {showSearch && (
        <SmartKnowledgeSearch
          projectId={projectId}
          onResultSelect={handleSearchResult}
          onClose={() => setShowSearch(false)}
        />
      )}
    </div>
  );
}

// Helper function to generate smart suggestions
function generateSuggestions(context, message) {
  const suggestions = [];

  // Based on context confidence and type
  if (context.confidence > 0.8) {
    suggestions.push('Include relevant code examples from knowledge base');
  }

  // Based on message content
  if (message.toLowerCase().includes('how')) {
    suggestions.push('Add step-by-step explanation with examples');
  }

  if (message.toLowerCase().includes('error') || message.toLowerCase().includes('bug')) {
    suggestions.push('Search for similar issues and solutions');
  }

  if (message.toLowerCase().includes('implement') || message.toLowerCase().includes('create')) {
    suggestions.push('Include implementation patterns from codebase');
  }

  // Based on available context
  if (context.codeSnippets.length > 0) {
    suggestions.push(`Reference ${context.codeSnippets.length} related code examples`);
  }

  if (context.relevantDocs.length > 0) {
    suggestions.push(`Cite ${context.relevantDocs.length} relevant documents`);
  }

  return suggestions.slice(0, 3); // Max 3 suggestions
}

// Wrap with error boundary to prevent SPA crashes
export default function KnowledgeAssistant(props) {
  return (
    <PageErrorBoundary pageName="Knowledge Assistant">
      <KnowledgeAssistantCore {...props} />
    </PageErrorBoundary>
  );
}
