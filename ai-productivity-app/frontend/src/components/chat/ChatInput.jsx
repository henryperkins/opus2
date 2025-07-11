import { useState, useRef, useCallback, useEffect } from "react";
import { Send, Hash, Plus, X } from "lucide-react";
import PropTypes from "prop-types";
import ThinkingModeSelector from "./ThinkingModeSelector";

// Simple command suggestions component
function CommandSuggestions({ query, onSelect, onClose }) {
  const commonCommands = [
    {
      name: "/explain",
      description: "Explain code functionality",
      usage: "/explain [code or file]",
    },
    {
      name: "/generate-tests",
      description: "Generate unit tests",
      usage: "/generate-tests [function name]",
    },
    {
      name: "/summarize-pr",
      description: "Summarize changes",
      usage: "/summarize-pr [pr number]",
    },
    {
      name: "/grep",
      description: "Search codebase",
      usage: "/grep [search term]",
    },
    {
      name: "/refactor",
      description: "Suggest refactoring",
      usage: "/refactor [code or file]",
    },
    {
      name: "/docs",
      description: "Generate documentation",
      usage: "/docs [function or class]",
    },
  ];

  const filteredCommands = query
    ? commonCommands.filter(
        (cmd) =>
          cmd.name.includes(query.toLowerCase()) ||
          cmd.description.toLowerCase().includes(query.toLowerCase()),
      )
    : commonCommands;

  if (filteredCommands.length === 0) return null;

  return (
    <div className="absolute bottom-full mb-2 left-0 right-0 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg py-2 z-50">
      <div className="flex items-center justify-between px-3 py-1 border-b border-gray-200 dark:border-gray-700">
        <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
          Commands
        </span>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
        >
          <X className="w-3 h-3" />
        </button>
      </div>

      <div className="max-h-48 overflow-y-auto">
        {filteredCommands.map((command) => (
          <button
            key={command.name}
            onClick={() => onSelect(command)}
            className="w-full px-3 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-700 flex flex-col"
          >
            <div className="flex items-center gap-2">
              <Hash className="w-3 h-3 text-blue-500" />
              <span className="font-medium text-sm">{command.name}</span>
            </div>
            <span className="text-xs text-gray-500 dark:text-gray-400 ml-5">
              {command.description}
            </span>
            <span className="text-xs text-gray-400 dark:text-gray-500 ml-5 font-mono">
              {command.usage}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

// File attachment preview component
function AttachmentPreview({ attachments, onRemove }) {
  if (!attachments || attachments.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 mb-2">
      {attachments.map((attachment, index) => (
        <div
          key={index}
          className="flex items-center gap-2 px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded text-sm"
        >
          <span className="truncate max-w-32">{attachment.name}</span>
          <button
            onClick={() => onRemove(index)}
            className="text-blue-500 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-200"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      ))}
    </div>
  );
}

/**
 * Simplified chat input component
 * Replaces EnhancedCommandInput with cleaner, more maintainable implementation
 */
export default function ChatInput({
  onSend,
  onTyping,
  projectId,
  placeholder = "Type a message...",
  disabled = false,
  maxLength = 4000,
}) {
  const [message, setMessage] = useState("");
  const [attachments, setAttachments] = useState([]);
  const [showCommands, setShowCommands] = useState(false);
  const [commandQuery, setCommandQuery] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [thinkingMode, setThinkingMode] = useState("off");
  const [thinkingDepth, setThinkingDepth] = useState("detailed");

  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  // Auto-resize textarea
  const adjustTextareaHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      const newHeight = Math.min(textarea.scrollHeight, 200); // Max 200px
      textarea.style.height = `${newHeight}px`;
    }
  }, []);

  // Handle typing indicator
  useEffect(() => {
    if (onTyping && message.length > 0) {
      onTyping(true);
      const timer = setTimeout(() => onTyping(false), 1000);
      return () => clearTimeout(timer);
    }
  }, [message, onTyping]);

  // Handle input change
  const handleInputChange = (e) => {
    const value = e.target.value;

    if (value.length > maxLength) return;

    setMessage(value);
    adjustTextareaHeight();

    // Check for command mode
    const isCommand = value.startsWith("/");
    if (isCommand) {
      const query = value.slice(1);
      setCommandQuery(query);
      setShowCommands(true);
    } else {
      setShowCommands(false);
      setCommandQuery("");
    }
  };

  // Handle command selection
  const handleCommandSelect = (command) => {
    setMessage(command.name + " ");
    setShowCommands(false);
    setCommandQuery("");
    textareaRef.current?.focus();
  };

  // Handle file attachment
  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files || []);
    const newAttachments = files.map((file) => ({
      name: file.name,
      size: file.size,
      type: file.type,
      file,
    }));

    setAttachments((prev) => [...prev, ...newAttachments]);

    // Clear file input
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // Remove attachment
  const removeAttachment = (index) => {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!message.trim() || isSending || disabled) return;

    setIsSending(true);

    try {
      const messageData = {
        content: message.trim(),
        attachments: attachments.length > 0 ? attachments : undefined,
        projectId,
        thinkingMode: thinkingMode !== "off" ? thinkingMode : undefined,
        thinkingDepth: thinkingMode !== "off" ? thinkingDepth : undefined,
      };

      await onSend(messageData);

      // Clear form
      setMessage("");
      setAttachments([]);
      setShowCommands(false);
      setCommandQuery("");

      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    } catch (error) {
      console.error("Failed to send message:", error);
    } finally {
      setIsSending(false);
    }
  };

  // Handle keyboard shortcuts
  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }

    if (e.key === "Escape") {
      setShowCommands(false);
    }
  };

  return (
    <div className="chat-input-container">
      <form onSubmit={handleSubmit} className="max-w-4xl mx-auto p-4">
        {/* Attachments preview */}
        <AttachmentPreview
          attachments={attachments}
          onRemove={removeAttachment}
        />

        {/* Thinking Mode Selector */}
        <div className="mb-3">
          <ThinkingModeSelector
            value={thinkingMode}
            depth={thinkingDepth}
            onChange={setThinkingMode}
            onDepthChange={setThinkingDepth}
            disabled={disabled || isSending}
            compact={true}
          />
        </div>

        {/* Main input area */}
        <div className="relative">
          {/* Command suggestions */}
          {showCommands && (
            <CommandSuggestions
              query={commandQuery}
              onSelect={handleCommandSelect}
              onClose={() => setShowCommands(false)}
            />
          )}

          <div className="flex gap-2 items-end">
            {/* Attach file button */}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={disabled}
              className="p-3 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50 min-w-[44px] h-[44px] flex items-center justify-center"
              title="Attach file"
            >
              <Plus className="w-5 h-5" />
            </button>

            {/* Text input */}
            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={message}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                placeholder={placeholder}
                disabled={disabled || isSending}
                className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg resize-none
                  focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                  bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                  placeholder-gray-500 dark:placeholder-gray-400
                  disabled:opacity-50 disabled:cursor-not-allowed
                  transition-colors"
                rows={1}
                style={{ minHeight: "44px" }}
                maxLength={maxLength}
              />

              {/* Character count */}
              {message.length > maxLength * 0.8 && (
                <div className="absolute bottom-2 right-2 text-xs text-gray-400">
                  {message.length}/{maxLength}
                </div>
              )}
            </div>

            {/* Send button */}
            <button
              type="submit"
              disabled={!message.trim() || isSending || disabled}
              className="p-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700
                disabled:opacity-50 disabled:cursor-not-allowed
                transition-colors min-w-[44px] h-[44px] flex items-center justify-center"
              title="Send message"
            >
              {isSending ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>

          {/* Helper text */}
          <div className="mt-2 text-xs text-gray-500 dark:text-gray-400 flex justify-between">
            <span>
              Type{" "}
              <kbd className="px-1 py-0.5 bg-gray-200 dark:bg-gray-700 rounded font-mono">
                /
              </kbd>{" "}
              for commands
            </span>
            <span>
              <kbd className="px-1 py-0.5 bg-gray-200 dark:bg-gray-700 rounded font-mono">
                Enter
              </kbd>{" "}
              to send,
              <kbd className="px-1 py-0.5 bg-gray-200 dark:bg-gray-700 rounded font-mono ml-1">
                Shift+Enter
              </kbd>{" "}
              for new line
            </span>
          </div>
        </div>

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          onChange={handleFileSelect}
          className="hidden"
          accept=".txt,.md,.js,.jsx,.ts,.tsx,.py,.java,.cpp,.c,.html,.css,.json,.xml,.csv"
        />
      </form>
    </div>
  );
}

ChatInput.propTypes = {
  onSend: PropTypes.func.isRequired,
  onTyping: PropTypes.func,
  projectId: PropTypes.string.isRequired,
  placeholder: PropTypes.string,
  disabled: PropTypes.bool,
  maxLength: PropTypes.number,
};

CommandSuggestions.propTypes = {
  query: PropTypes.string.isRequired,
  onSelect: PropTypes.func.isRequired,
  onClose: PropTypes.func.isRequired,
};

AttachmentPreview.propTypes = {
  attachments: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string.isRequired,
      size: PropTypes.number,
      type: PropTypes.string,
      file: PropTypes.object,
    }),
  ),
  onRemove: PropTypes.func.isRequired,
};
