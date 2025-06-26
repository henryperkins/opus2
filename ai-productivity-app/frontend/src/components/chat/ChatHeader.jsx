import { Brain, Settings, Search, BarChart2, Code2 } from 'lucide-react';
import ConnectionIndicator from '../common/ConnectionIndicator';
import SessionRAGBadge from './SessionRAGBadge';

/**
 * Simplified chat header component
 * Extracted from ProjectChatPage to reduce complexity
 */
export default function ChatHeader({
  project,
  connectionState,
  messages = [],
  showKnowledgeAssistant = false,
  showEditor = false,
  onToggleKnowledge,
  onToggleEditor,
  onOpenSearch,
  onOpenPromptManager,
  onToggleAnalytics
}) {
  return (
    <div className="bg-white/90 dark:bg-gray-900/90 border-b border-gray-200 dark:border-gray-700">
      <div className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center space-x-4">
          <h1 className="text-xl font-semibold truncate max-w-xs sm:max-w-none">
            {project?.title || 'Loading...'}
          </h1>
          <div className="hidden md:block">
            <ConnectionIndicator state={connectionState} />
          </div>

          {/* Session-wide RAG status badge */}
          <SessionRAGBadge messages={messages} />
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={onToggleKnowledge}
            className={`p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors ${
              showKnowledgeAssistant ? 'bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-400' : 'text-gray-600 dark:text-gray-400'
            }`}
            aria-label="Toggle Knowledge Assistant"
            title={showKnowledgeAssistant ? 'Hide Knowledge Assistant' : 'Show Knowledge Assistant'}
          >
            <Brain className="w-5 h-5" />
          </button>

          <button
            onClick={onOpenSearch}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg text-gray-600 dark:text-gray-400 transition-colors"
            aria-label="Knowledge Search"
            title="Knowledge Search"
          >
            <Search className="w-5 h-5" />
          </button>

          <button
            onClick={onToggleEditor}
            className={`p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors ${
              showEditor ? 'bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-400' : 'text-gray-600 dark:text-gray-400'
            }`}
            aria-label="Toggle Code Editor"
            title={showEditor ? 'Hide Code Editor' : 'Show Code Editor'}
          >
            <Code2 className="w-5 h-5" />
          </button>

          <button
            onClick={onOpenPromptManager}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg text-gray-600 dark:text-gray-400 transition-colors"
            aria-label="Prompt Manager"
            title="Prompt Manager"
          >
            <Settings className="w-5 h-5" />
          </button>

          <button
            onClick={onToggleAnalytics}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg text-gray-600 dark:text-gray-400 transition-colors"
            aria-label="Toggle analytics view"
            title="Toggle Analytics"
          >
            <BarChart2 className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
