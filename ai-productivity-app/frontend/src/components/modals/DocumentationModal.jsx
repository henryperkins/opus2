import PropTypes from 'prop-types';
import { useState, useEffect } from 'react';
import { Brain, Search, Upload, MessageCircle, CheckCircle, Info } from 'lucide-react';
import Modal from '../common/Modal';

const DocumentationModal = ({ isOpen, onClose, defaultTab = 'overview' }) => {
  const [activeTab, setActiveTab] = useState(defaultTab);
  
  // Update tab when defaultTab prop changes
  useEffect(() => {
    if (isOpen && defaultTab) {
      setActiveTab(defaultTab);
    }
  }, [isOpen, defaultTab]);

  const tabs = [
    { id: 'overview', label: 'Overview', icon: <Info className="w-4 h-4" /> },
    { id: 'rag', label: 'RAG Features', icon: <Brain className="w-4 h-4" /> },
    { id: 'search', label: 'Search', icon: <Search className="w-4 h-4" /> },
    { id: 'knowledge', label: 'Knowledge', icon: <Upload className="w-4 h-4" /> },
    { id: 'chat', label: 'Chat', icon: <MessageCircle className="w-4 h-4" /> }
  ];

  const renderTabContent = () => {
    switch (activeTab) {
      case 'overview':
        return (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              Welcome to the AI Productivity App. This application combines powerful AI capabilities with your own knowledge base to provide contextual, accurate assistance.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 bg-blue-50 rounded-lg">
                <h5 className="font-medium text-blue-900">RAG Technology</h5>
                <p className="text-sm text-blue-700 mt-1">
                  Retrieval-Augmented Generation enhances AI responses with your specific documents and code.
                </p>
              </div>
              <div className="p-4 bg-green-50 rounded-lg">
                <h5 className="font-medium text-green-900">Smart Search</h5>
                <p className="text-sm text-green-700 mt-1">
                  Multiple search modes find exactly what you need, from concepts to specific code patterns.
                </p>
              </div>
            </div>
          </div>
        );

      case 'rag':
        return (
          <div className="space-y-4">
            <div>
              <h4 className="font-semibold text-gray-800 flex items-center gap-2">
                <Brain className="w-5 h-5 text-blue-600" />
                Understanding RAG (Retrieval-Augmented Generation)
              </h4>
              <p className="mt-2 text-sm text-gray-600">
                RAG enhances AI responses by searching your knowledge base for relevant information before generating answers.
              </p>
            </div>
            
            <div className="space-y-3">
              <div className="border-l-4 border-green-400 pl-4">
                <h5 className="font-medium text-gray-800">Active RAG (Green)</h5>
                <p className="text-sm text-gray-600">Your knowledge base contributed to this response with high confidence.</p>
              </div>
              <div className="border-l-4 border-yellow-400 pl-4">
                <h5 className="font-medium text-gray-800">Degraded RAG (Yellow)</h5>
                <p className="text-sm text-gray-600">Some relevant sources found, but confidence is lower. Consider adding more documentation.</p>
              </div>
              <div className="border-l-4 border-red-400 pl-4">
                <h5 className="font-medium text-gray-800">RAG Error (Red)</h5>
                <p className="text-sm text-gray-600">Technical issue accessing knowledge base. Response uses standard AI knowledge.</p>
              </div>
              <div className="border-l-4 border-gray-400 pl-4">
                <h5 className="font-medium text-gray-800">Standard Response (Gray)</h5>
                <p className="text-sm text-gray-600">No relevant knowledge found. Response uses AI's training data.</p>
              </div>
            </div>

            <div className="bg-blue-50 p-4 rounded-lg">
              <h5 className="font-medium text-blue-900">Citations</h5>
              <ul className="mt-2 space-y-1 text-sm text-blue-700">
                <li>• Click citations [1], [2] to view source content</li>
                <li>• Confidence percentages show source reliability</li>
                <li>• Rate citations to improve future results</li>
              </ul>
            </div>
          </div>
        );

      case 'search':
        return (
          <div className="space-y-4">
            <div>
              <h4 className="font-semibold text-gray-800">Search Modes</h4>
              <p className="mt-1 text-sm text-gray-600">
                Choose the right search mode for your needs:
              </p>
            </div>
            
            <div className="space-y-3">
              <div className="p-3 border border-gray-200 rounded-lg">
                <h5 className="font-medium text-purple-800">Semantic Search</h5>
                <p className="text-sm text-gray-600">Finds content by meaning, not just keywords.</p>
                <div className="mt-2 text-xs text-gray-500 font-mono bg-gray-50 p-2 rounded">
                  Example: "user authentication" → finds login code, auth middleware
                </div>
              </div>
              
              <div className="p-3 border border-gray-200 rounded-lg">
                <h5 className="font-medium text-blue-800">Keyword Search</h5>
                <p className="text-sm text-gray-600">Finds exact text matches in your codebase.</p>
                <div className="mt-2 text-xs text-gray-500 font-mono bg-gray-50 p-2 rounded">
                  Example: "useState" → finds React hooks
                </div>
              </div>
              
              <div className="p-3 border border-gray-200 rounded-lg">
                <h5 className="font-medium text-green-800">Structural Search</h5>
                <p className="text-sm text-gray-600">Finds code patterns and structures.</p>
                <div className="mt-2 text-xs text-gray-500 font-mono bg-gray-50 p-2 rounded">
                  Example: "function:login" → finds login function definitions
                </div>
              </div>
              
              <div className="p-3 border border-gray-200 rounded-lg">
                <h5 className="font-medium text-orange-800">Hybrid Search</h5>
                <p className="text-sm text-gray-600">Combines all modes for comprehensive results.</p>
              </div>
            </div>
          </div>
        );

      case 'knowledge':
        return (
          <div className="space-y-4">
            <div>
              <h4 className="font-semibold text-gray-800">Building Your Knowledge Base</h4>
              <p className="mt-1 text-sm text-gray-600">
                The more relevant content you add, the better your AI assistant becomes.
              </p>
            </div>
            
            <div className="space-y-3">
              <div className="flex items-start gap-3 p-3 border border-green-200 bg-green-50 rounded-lg">
                <Upload className="w-5 h-5 text-green-600 mt-0.5" />
                <div>
                  <h5 className="font-medium text-green-800">Upload Documents</h5>
                  <p className="text-sm text-green-700">Add PDFs, text files, documentation, and guides.</p>
                </div>
              </div>
              
              <div className="flex items-start gap-3 p-3 border border-blue-200 bg-blue-50 rounded-lg">
                <Brain className="w-5 h-5 text-blue-600 mt-0.5" />
                <div>
                  <h5 className="font-medium text-blue-800">Connect Repositories</h5>
                  <p className="text-sm text-blue-700">Link GitHub repos for automatic code indexing.</p>
                </div>
              </div>
              
              <div className="flex items-start gap-3 p-3 border border-purple-200 bg-purple-50 rounded-lg">
                <MessageCircle className="w-5 h-5 text-purple-600 mt-0.5" />
                <div>
                  <h5 className="font-medium text-purple-800">Knowledge Entries</h5>
                  <p className="text-sm text-purple-700">Add procedures, guidelines, and institutional knowledge.</p>
                </div>
              </div>
            </div>

            <div className="bg-yellow-50 p-4 rounded-lg">
              <h5 className="font-medium text-yellow-800">💡 Tips for Better Results</h5>
              <ul className="mt-2 space-y-1 text-sm text-yellow-700">
                <li>• Upload documentation related to your queries</li>
                <li>• Include README files and getting started guides</li>
                <li>• Add troubleshooting and FAQ documents</li>
                <li>• Connect repositories you frequently work with</li>
              </ul>
            </div>
          </div>
        );

      case 'chat':
        return (
          <div className="space-y-4">
            <div>
              <h4 className="font-semibold text-gray-800">Effective Chat Queries</h4>
              <p className="mt-1 text-sm text-gray-600">
                Learn how to ask questions that get the best results from your AI assistant.
              </p>
            </div>
            
            <div className="space-y-4">
              <div>
                <h5 className="font-medium text-gray-800">Process Questions</h5>
                <div className="mt-2 space-y-1">
                  <div className="text-sm text-gray-600 p-2 bg-gray-50 rounded border-l-4 border-blue-400">
                    "How do I deploy this application?"
                  </div>
                  <div className="text-sm text-gray-600 p-2 bg-gray-50 rounded border-l-4 border-blue-400">
                    "What is the testing strategy for this project?"
                  </div>
                </div>
              </div>
              
              <div>
                <h5 className="font-medium text-gray-800">Technical Queries</h5>
                <div className="mt-2 space-y-1">
                  <div className="text-sm text-gray-600 p-2 bg-gray-50 rounded border-l-4 border-green-400">
                    "Where is user authentication implemented?"
                  </div>
                  <div className="text-sm text-gray-600 p-2 bg-gray-50 rounded border-l-4 border-green-400">
                    "How does error handling work in this codebase?"
                  </div>
                </div>
              </div>
              
              <div>
                <h5 className="font-medium text-gray-800">Comparison Questions</h5>
                <div className="mt-2 space-y-1">
                  <div className="text-sm text-gray-600 p-2 bg-gray-50 rounded border-l-4 border-purple-400">
                    "What's the difference between approach A and B?"
                  </div>
                  <div className="text-sm text-gray-600 p-2 bg-gray-50 rounded border-l-4 border-purple-400">
                    "Should I use REST or GraphQL for this API?"
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-green-50 p-4 rounded-lg">
              <h5 className="font-medium text-green-800">✅ Best Practices</h5>
              <ul className="mt-2 space-y-1 text-sm text-green-700">
                <li>• Be specific about what you want to know</li>
                <li>• Include context when asking about concepts</li>
                <li>• Ask follow-up questions to dive deeper</li>
                <li>• Check citations to verify information</li>
              </ul>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Documentation" className="max-w-4xl">
      <div className="flex h-96">
        {/* Tab sidebar */}
        <div className="w-48 border-r border-gray-200 pr-4">
          <nav className="space-y-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md transition-colors ${
                  activeTab === tab.id
                    ? 'bg-blue-100 text-blue-700 font-medium'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content area */}
        <div className="flex-1 pl-6">
          <div className="h-full overflow-y-auto">
            {renderTabContent()}
          </div>
        </div>
      </div>
    </Modal>
  );
};

DocumentationModal.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  defaultTab: PropTypes.string,
};

export default DocumentationModal;
