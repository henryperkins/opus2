import React, { useState, useRef, useEffect, useCallback } from 'react';
import MonacoEditor from '@monaco-editor/react';
import * as monaco from 'monaco-editor';
import {
  Search,
  Command,
  X,
  ChevronRight,
  Paperclip,
  Mic,
  Square,
  Send
} from 'lucide-react';
import { debounce } from 'lodash';
import { useProjectTimeline } from '../../hooks/useProjects';
import { KnowledgeCommandRegistry } from '../../utils/commands/knowledge-commands';
import PropTypes from 'prop-types';
import { toast } from '../common/Toast';

// Command registry + static commands
const commandRegistry = new KnowledgeCommandRegistry();

const standardCommands = [
  { name: '/explain', description: 'Explain code functionality' },
  { name: '/generate-tests', description: 'Generate unit tests' },
  { name: '/summarize-pr', description: 'Summarize changes' },
  { name: '/grep', description: 'Search codebase' }
];

const allCommands = [
  ...standardCommands,
  ...commandRegistry.getAll().map(c => ({
    name: c.name,
    description: c.description,
    usage: c.usage,
    aliases: c.aliases
  }))
];

export default function EnhancedCommandInput({
  onSend,
  onTyping,
  projectId,
  editorContent,
  selectedText,
  currentFile,
  userId
}) {
  const { addEvent } = useProjectTimeline(projectId);
  const [message, setMessage] = useState('');
  const [attachments, setAttachments] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [inputMode, setInputMode] = useState('simple');
  const [editorHeight, setEditorHeight] = useState(200);
  const [isSending, setIsSending] = useState(false);
  const [commandProcessing, setCommandProcessing] = useState(false);
  const [citations, setCitations] = useState([]);
  const [showCommandHelp, setShowCommandHelp] = useState(false);
  const [isTyping, setIsTyping] = useState(false);

  const inputRef = useRef(null);
  const textareaRef = useRef(null);
  const editorRef = useRef(null);

  // Debounced typing indicator
  const debouncedOnTyping = useCallback(
    debounce((typing) => {
      onTyping?.(typing);
    }, 300),
    [onTyping]
  );

  // Slash-command suggestions
  useEffect(() => {
    if (message.startsWith('/')) {
      const partial = message.split(' ')[0].toLowerCase();
      const matches = allCommands.filter(cmd =>
        cmd.name.toLowerCase().startsWith(partial) ||
        cmd.aliases?.some(a => a.toLowerCase().startsWith(partial))
      );
      setSuggestions(matches);
      setShowSuggestions(matches.length > 0);
    } else {
      setShowSuggestions(false);
    }
  }, [message]);

  // Typing indicator with debounce
  useEffect(() => {
    const currentlyTyping = Boolean(message.trim());
    if (currentlyTyping !== isTyping) {
      setIsTyping(currentlyTyping);
      debouncedOnTyping(currentlyTyping);
    }
  }, [message, isTyping, debouncedOnTyping]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      debouncedOnTyping.cancel();
    };
  }, [debouncedOnTyping]);

  // Monaco editor setup
  const handleEditorMount = (editor) => {
    editorRef.current = editor;
    
    // Add keyboard shortcut for send
    editor.addCommand(
      monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter,
      () => {
        handleSubmit(new Event('submit'));
      }
    );
  };

  // Utils
  const insertCitation = (citation) =>
    setMessage(prev => `${prev}[${citation.number}] `);

  // Clear citations - also removes citation numbers from message
  const clearCitations = () => {
    setCitations([]);
    // Remove all citation numbers from the message
    setMessage(prev => prev.replace(/\[\d+\]/g, '').trim());
  };

  // Knowledge command runner
  const runKnowledgeCommand = async (cmdLine) => {
    const context = {
      projectId,
      currentFile,
      selectedText,
      editorContent,
      userId
    };

    const result = await commandRegistry.execute(cmdLine, context);

    if (result.citations) setCitations(result.citations);

    if (result.requiresLLM) {
      return {
        payload: result.prompt ?? cmdLine,
        meta: {
          isCommand: true,
          commandType: 'knowledge',
          citations: result.citations ?? undefined
        },
        shouldSend: true
      };
    }

    toast.success(result.message || 'Command executed successfully');
    return { shouldSend: false };
  };

  // Submit handler
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!message.trim() || isSending) return;

    setIsSending(true);
    setCommandProcessing(true);

    try {
      const meta = citations.length ? { citations } : {};

      // Handle slash commands
      if (message.startsWith('/')) {
        const result = await runKnowledgeCommand(message);
        if (result.shouldSend) {
          await onSend(result.payload, { ...meta, ...result.meta });
        }
      } else {
        await onSend(message, meta);
      }

      // Clear state after successful send
      setMessage('');
      setCitations([]);
      setShowSuggestions(false);
      if (textareaRef.current) textareaRef.current.style.height = 'auto';

      // Add to project timeline for activity tracking
      addEvent({
        event_type: 'chat_message',
        title: 'Chat message sent',
        description: `Sent message: ${message.substring(0, 50)}...`,
        metadata: { hasAttachments: attachments.length > 0 }
      });
    } catch (error) {
      console.error('Failed to send message:', error);
      toast.error('Failed to send message');
    } finally {
      setIsSending(false);
      setCommandProcessing(false);
    }
  };

  // Handle file attachments
  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    setAttachments(prev => [...prev, ...files]);
  };

  const removeAttachment = (index) => {
    setAttachments(prev => prev.filter((_, i) => i !== index));
  };

  // Auto-resize textarea
  const handleTextareaChange = (e) => {
    const textarea = e.target;
    setMessage(textarea.value);
    
    // Auto-resize
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
  };

  // Keyboard navigation for suggestions
  const handleKeyDown = (e) => {
    if (!showSuggestions) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => 
          prev < suggestions.length - 1 ? prev + 1 : prev
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => prev > 0 ? prev - 1 : -1);
        break;
      case 'Enter':
        if (selectedIndex >= 0) {
          e.preventDefault();
          const selected = suggestions[selectedIndex];
          setMessage(selected.name + ' ');
          setShowSuggestions(false);
          setSelectedIndex(-1);
        }
        break;
      case 'Escape':
        setShowSuggestions(false);
        setSelectedIndex(-1);
        break;
    }
  };

  return (
    <div className="relative">
      {/* Command suggestions */}
      {showSuggestions && (
        <div className="absolute bottom-full mb-2 left-0 right-0 bg-white border rounded-lg shadow-lg max-h-48 overflow-y-auto">
          {suggestions.map((cmd, idx) => (
            <div
              key={cmd.name}
              className={`px-4 py-2 cursor-pointer ${
                idx === selectedIndex ? 'bg-blue-50' : 'hover:bg-gray-50'
              }`}
              onMouseDown={() => {
                setMessage(cmd.name + ' ');
                setShowSuggestions(false);
              }}
            >
              <div className="font-mono text-blue-600">{cmd.name}</div>
              <div className="text-gray-600 text-xs">{cmd.description}</div>
              {cmd.usage && <div className="text-gray-400 text-xs">{cmd.usage}</div>}
            </div>
          ))}
        </div>
      )}

      {/* Citation bar */}
      {citations.length > 0 && (
        <div className="px-4 py-2 bg-blue-50 border-b flex justify-between items-center">
          <span className="text-sm text-blue-700">
            {citations.length} citation{citations.length > 1 ? 's' : ''} ready
          </span>
          <div className="flex gap-1">
            {citations.map(c => (
              <button
                key={c.id}
                onClick={() => insertCitation(c)}
                className="px-2 text-xs rounded bg-brand-primary-50 hover:bg-brand-primary-100 text-brand-primary-700"
              >
                [{c.number}]
              </button>
            ))}
          </div>
          <button
            onClick={clearCitations}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            Clear
          </button>
        </div>
      )}

      {/* Mode / help bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b">
        <div className="flex gap-2">
          {['simple', 'editor'].map(mode => (
            <button
              key={mode}
              onClick={() => setInputMode(mode)}
              className={`px-2 py-1 rounded text-xs ${
                inputMode === mode ? 'bg-blue-500 text-white' : 'bg-gray-200'
              }`}
            >
              {mode}
            </button>
          ))}

          <button
            onClick={() => setShowCommandHelp(h => !h)}
            className="p-1 text-gray-500 hover:text-gray-700"
            title="Command help"
          >
            <Command className="w-4 h-4" />
          </button>
        </div>

        {inputMode === 'editor' && (
          <select
            value={editorHeight}
            onChange={e => setEditorHeight(+e.target.value)}
            className="text-xs border rounded px-1"
          >
            {[100, 200, 300].map(h => (
              <option key={h} value={h}>
                {h === 100 ? 'Small' : h === 200 ? 'Medium' : 'Large'} ({h}px)
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Command help */}
      {showCommandHelp && (
        <div className="px-4 py-2 bg-gray-50 border-b text-xs">
          <div className="font-semibold mb-1">Available Commands:</div>
          <div className="grid grid-cols-2 gap-1">
            {allCommands.slice(0, 6).map(cmd => (
              <div key={cmd.name} className="text-gray-600">
                <span className="font-mono text-blue-600">{cmd.name}</span> - {cmd.description}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Input form */}
      <form onSubmit={handleSubmit} className="p-2 sm:p-4">
        {/* Attachments */}
        {attachments.length > 0 && (
          <div className="mb-2 flex flex-nowrap sm:flex-wrap gap-2 overflow-x-auto pb-1">
            {attachments.map((file, idx) => (
              <div key={idx} className="flex items-center gap-1 bg-gray-100 rounded px-2 py-1 text-sm">
                <Paperclip className="w-3 h-3" />
                <span className="truncate max-w-[150px]">{file.name}</span>
                <button
                  type="button"
                  onClick={() => removeAttachment(idx)}
                  className="text-gray-500 hover:text-gray-700"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="flex items-end gap-2">
          {/* File attachment button */}
          <label className="cursor-pointer text-gray-500 hover:text-gray-700 flex-shrink-0">
            <input
              type="file"
              multiple
              className="hidden"
              onChange={handleFileSelect}
              accept=".py,.js,.jsx,.ts,.tsx,.java,.cpp,.c,.h,.md,.txt,.json,.yaml,.yml"
            />
            <Paperclip className="w-5 h-5" />
          </label>

          {/* Input area */}
          <div className="flex-1 min-w-0">
            {inputMode === 'simple' ? (
              <textarea
                ref={textareaRef}
                value={message}
                onChange={handleTextareaChange}
                onKeyDown={handleKeyDown}
                placeholder="Type a message or / for commands..."
                className="w-full px-3 py-2 border rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm sm:text-base"
                rows="1"
                disabled={isSending}
              />
            ) : (
              <div 
                className="border rounded-lg overflow-hidden dynamic-height"
                style={{ '--dynamic-height': editorHeight }}
              >
                <MonacoEditor
                  value={message}
                  onChange={setMessage}
                  onMount={handleEditorMount}
                  language="markdown"
                  theme="vs-light"
                  options={{
                    minimap: { enabled: false },
                    lineNumbers: 'off',
                    glyphMargin: false,
                    folding: false,
                    lineDecorationsWidth: 0,
                    lineNumbersMinChars: 0,
                    renderLineHighlight: 'none',
                    scrollBeyondLastLine: false,
                    wordWrap: 'on',
                    wrappingStrategy: 'advanced',
                    overviewRulerLanes: 0,
                    hideCursorInOverviewRuler: true,
                    scrollbar: {
                      vertical: 'hidden'
                    }
                  }}
                />
              </div>
            )}
          </div>

          {/* Send button */}
          <button
            type="submit"
            disabled={isSending || !message.trim()}
                className={`p-2 sm:p-3 rounded-lg flex-shrink-0 ${
              isSending || !message.trim()
                ? 'bg-gray-200 text-gray-400'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </form>
    </div>
  );
}

EnhancedCommandInput.propTypes = {
  onSend: PropTypes.func.isRequired,
  onTyping: PropTypes.func,
  projectId: PropTypes.string.isRequired,
  editorContent: PropTypes.string,
  selectedText: PropTypes.string,
  currentFile: PropTypes.string,
  userId: PropTypes.string
};