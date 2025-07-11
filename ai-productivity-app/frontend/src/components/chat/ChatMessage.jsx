import { useState } from "react";
import {
  Copy,
  Download,
  Play,
  Search,
  MoreHorizontal,
  Clock,
} from "lucide-react";
import PropTypes from "prop-types";
import MessageFeedback from "./MessageFeedback";
import ConfidenceWarning from "./ConfidenceWarning";

// Simple streaming text component
function StreamingText({ content }) {
  return (
    <div className="relative">
      {content}
      <span className="streaming-cursor">|</span>
    </div>
  );
}

// Message content renderer with basic markdown support
function MessageContent({ content, metadata }) {
  const hasCitations = metadata?.citations?.length > 0;

  return (
    <div className="message-content">
      {/* Simple markdown rendering - you can enhance this */}
      <div
        className="message-content max-w-none"
        dangerouslySetInnerHTML={{
          __html: content
            .replace(
              /```(\w*)\n([\s\S]*?)```/g,
              '<pre><code class="language-$1">$2</code></pre>',
            )
            .replace(/`([^`]+)`/g, "<code>$1</code>")
            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
            .replace(/\*(.*?)\*/g, "<em>$1</em>"),
        }}
      />

      {/* Citations display */}
      {hasCitations && (
        <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
          <div className="text-xs text-gray-600 dark:text-gray-400">
            Sources:{" "}
            {metadata.citations.map((citation, i) => (
              <span
                key={i}
                className="inline-block mx-1 px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded"
              >
                {citation.source?.title || `Source ${i + 1}`}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Format time helper
function formatTime(timestamp) {
  if (!timestamp) return "";
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
  return date.toLocaleDateString();
}

/**
 * Simplified chat message component with responsive design
 * Replaces complex EnhancedMessageRenderer with clean, maintainable code
 */
export default function ChatMessage({
  message,
  isStreaming = false,
  onAction,
  onMessageSelect,
  showActions = true,
  onFeedbackSubmit,
}) {
  const [showMenu, setShowMenu] = useState(false);
  const isUser = message.role === "user";
  const isAssistant = message.role === "assistant";

  const handleAction = (actionType, data) => {
    if (onAction) {
      onAction(actionType, { message, ...data });
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    handleAction("copy", { content: message.content });
  };

  const handleRunCode = () => {
    handleAction("runCode", { content: message.content });
  };

  const handleTransform = () => {
    handleAction("transform", { content: message.content });
  };

  const handleViewSource = () => {
    handleAction("viewSource", { metadata: message.metadata });
  };

  return (
    <div
      className={`
      flex ${isUser ? "justify-end" : "justify-start"}
      mb-4 px-4 group
    `}
    >
      <div
        className={`
        max-w-full md:max-w-3xl rounded-lg p-4 shadow-sm
        ${
          isUser
            ? "bg-blue-600 text-white"
            : "bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700"
        }
      `}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-2 text-xs opacity-75">
          <div className="flex items-center gap-2">
            <span className="font-medium">{isUser ? "You" : "AI"}</span>
            {/* Model indicator for assistant messages */}
            {isAssistant && message.metadata?.model && (
              <span className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-gray-600 dark:text-gray-400">
                {message.metadata.model}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* RAG indicator - simple inline badge */}
            {isAssistant && message.metadata?.ragUsed && (
              <div className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded">
                <div className="w-2 h-2 rounded-full bg-green-500" />
                <span>{message.metadata.citations?.length || 0} sources</span>
              </div>
            )}

            <time className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {formatTime(message.created_at)}
            </time>
          </div>
        </div>

        {/* Content */}
        <div
          className="cursor-pointer message-content"
          onClick={() => onMessageSelect && onMessageSelect(message)}
        >
          {isStreaming ? (
            <StreamingText content={message.content} />
          ) : (
            <MessageContent
              content={message.content}
              metadata={message.metadata}
            />
          )}
        </div>

        {/* Confidence Warnings for assistant messages */}
        {isAssistant &&
          !isStreaming &&
          message.metadata?.confidence_warnings && (
            <ConfidenceWarning
              warnings={message.metadata.confidence_warnings}
              ragMetadata={message.metadata.rag_metadata}
            />
          )}

        {/* Actions - only show for assistant messages and if enabled */}
        {showActions && isAssistant && !isStreaming && (
          <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700 opacity-0 group-hover:opacity-100 transition-opacity">
            <div className="flex items-center justify-between">
              {/* Quick actions */}
              <div className="flex gap-2">
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1 px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors"
                  title="Copy message"
                >
                  <Copy className="w-3 h-3" />
                  <span className="hidden sm:inline">Copy</span>
                </button>

                {message.content.includes("```") && (
                  <button
                    onClick={handleRunCode}
                    className="flex items-center gap-1 px-2 py-1 text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 hover:bg-green-200 dark:hover:bg-green-900/50 rounded transition-colors"
                    title="Run code"
                  >
                    <Play className="w-3 h-3" />
                    <span className="hidden sm:inline">Run</span>
                  </button>
                )}

                <button
                  onClick={handleTransform}
                  className="flex items-center gap-1 px-2 py-1 text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 hover:bg-purple-200 dark:hover:bg-purple-900/50 rounded transition-colors"
                  title="Transform content"
                >
                  <Download className="w-3 h-3" />
                  <span className="hidden sm:inline">Transform</span>
                </button>

                {message.metadata?.citations?.length > 0 && (
                  <button
                    onClick={handleViewSource}
                    className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-900/50 rounded transition-colors"
                    title="View sources"
                  >
                    <Search className="w-3 h-3" />
                    <span className="hidden sm:inline">Sources</span>
                  </button>
                )}
              </div>

              {/* More actions menu */}
              <div className="relative">
                <button
                  onClick={() => setShowMenu(!showMenu)}
                  className="p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded"
                  title="More actions"
                >
                  <MoreHorizontal className="w-4 h-4" />
                </button>

                {showMenu && (
                  <div className="absolute right-0 top-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg py-1 z-10 min-w-32">
                    <button
                      onClick={() => handleAction("edit")}
                      className="w-full px-3 py-1 text-left text-xs hover:bg-gray-100 dark:hover:bg-gray-700"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleAction("delete")}
                      className="w-full px-3 py-1 text-left text-xs text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30"
                    >
                      Delete
                    </button>
                    <button
                      onClick={() => handleAction("retry")}
                      className="w-full px-3 py-1 text-left text-xs hover:bg-gray-100 dark:hover:bg-gray-700"
                    >
                      Retry
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Message Feedback */}
            {onFeedbackSubmit && (
              <MessageFeedback
                messageId={message.id}
                onFeedbackSubmit={onFeedbackSubmit}
                initialFeedback={message.feedback}
                className="mt-2"
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

ChatMessage.propTypes = {
  message: PropTypes.shape({
    id: PropTypes.string.isRequired,
    role: PropTypes.oneOf(["user", "assistant"]).isRequired,
    content: PropTypes.string.isRequired,
    created_at: PropTypes.string,
    user_id: PropTypes.string,
    metadata: PropTypes.object,
    feedback: PropTypes.object,
  }).isRequired,
  isStreaming: PropTypes.bool,
  onAction: PropTypes.func,
  onMessageSelect: PropTypes.func,
  showActions: PropTypes.bool,
  onFeedbackSubmit: PropTypes.func,
};

StreamingText.propTypes = {
  content: PropTypes.string.isRequired,
};

MessageContent.propTypes = {
  content: PropTypes.string.isRequired,
  metadata: PropTypes.object,
};
