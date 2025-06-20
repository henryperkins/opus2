// components/chat/EnhancedCommandInput.jsx
import React, { useState, useRef, useEffect, useCallback } from 'react';
import MonacoEditor from '@monaco-editor/react';
import { Search, Command, X, ChevronRight } from 'lucide-react';
import { toast } from '../common/Toast';
import { useProjectTimeline } from '../../hooks/useProjects';
import { KnowledgeCommandRegistry } from '../../commands/knowledge-commands';
import { Citation } from '../../types/knowledge';
import PropTypes from 'prop-types';

const commandRegistry = new KnowledgeCommandRegistry();

// Existing slash commands
const standardCommands = [
  { name: '/explain', description: 'Explain code functionality' },
  { name: '/generate-tests', description: 'Generate unit tests' },
  { name: '/summarize-pr', description: 'Summarize changes' },
  { name: '/grep', description: 'Search codebase' },
];

// Combine with knowledge commands
const allCommands = [
  ...standardCommands,
  ...commandRegistry.getAll().map(cmd => ({
    name: cmd.name,
    description: cmd.description,
    usage: cmd.usage,
    aliases: cmd.aliases
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
}: EnhancedCommandInputProps) {
  const { addEvent } = useProjectTimeline(projectId);
  const [message, setMessage] = useState('');
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [inputMode, setInputMode] = useState('simple');
  const [editorHeight, setEditorHeight] = useState(100);
  const [isSending, setIsSending] = useState(false);
  const [commandProcessing, setCommandProcessing] = useState(false);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [showCommandHelp, setShowCommandHelp] = useState(false);

  const inputRef = useRef<HTMLInputElement>(null);
  const [isTyping, setIsTyping] = useState(false);

  // Command suggestions
  useEffect(() => {
    if (message.startsWith('/')) {
      const partial = message.split(' ')[0].toLowerCase();
      const matches = allCommands.filter(cmd =>
        cmd.name.toLowerCase().startsWith(partial) ||
        cmd.aliases?.some(alias => alias.toLowerCase().startsWith(partial))
      );
      setSuggestions(matches);
      setShowSuggestions(matches.length > 0);
    } else {
      setShowSuggestions(false);
    }
  }, [message]);

  // Typing indicator
  useEffect(() => {
    const typingNow = Boolean(message.trim());
    if (typingNow !== isTyping) {
      setIsTyping(typingNow);
      onTyping?.(typingNow);
    }
  }, [message, isTyping, onTyping]);

  const handleKnowledgeCommand = async (commandLine: string): Promise<{
    result: any;
    shouldSend: boolean
  }> => {
    const context = {
      projectId,
      currentFile,
      selectedText,
      editorContent,
      userId
    };

    const result = await commandRegistry.execute(commandLine, context);

    if (result.citations) {
      setCitations(result.citations);
    }

    if (result.requiresLLM) {
      // Command needs LLM processing
      return {
        result: {
          ...result,
          metadata: {
            isCommand: true,
            commandType: 'knowledge',
            citations: result.citations
          }
        },
        shouldSend: true
      };
    }

    // Command completed without needing LLM
    toast.success(result.message || 'Command executed successfully');
    return { result, shouldSend: false };
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || isSending) return;

    setIsSending(true);
    setCommandProcessing(true);

    try {
      const metadata: any = {
        citations: citations.length > 0 ? citations : undefined
      };

      // Check if it's a knowledge command
      if (message.startsWith('/')) {
        const [cmd] = message.split(' ');
        const knowledgeCmd = commandRegistry.get(cmd);

        if (knowledgeCmd) {
          const { result, shouldSend } = await handleKnowledgeCommand(message);

          if (shouldSend) {
            await onSend(result.prompt || message, {
              ...metadata,
              ...result.metadata
            });
          }
        } else {
          // Standard command
          await onSend(message, {
            ...metadata,
            isCommand: true
          });
        }
      } else {
        // Regular message
        // Check for @references
        if (message.includes('@editor') && editorContent) {
          metadata.code_snippets = [{
            language: 'auto',
            code: editorContent
          }];
        }

        await onSend(message, metadata);
      }

      // Clear state
      setMessage('');
      setCitations([]);

      // Log to timeline
      try {
        await addEvent({
          event_type: 'comment',
          title: message.startsWith('/') ? 'Command executed' : 'Message sent',
          description: message.slice(0, 100),
          metadata: { message_type: 'chat', has_citations: citations.length > 0 }
        });
      } catch (error) {
        console.warn('Failed to log timeline event:', error);
      }
    } catch (error) {
      toast.error('Failed to send message');
      console.error('Send error:', error);
    } finally {
      setIsSending(false);
      setCommandProcessing(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (showSuggestions && suggestions.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(prev => (prev + 1) % suggestions.length);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(prev => prev <= 0 ? suggestions.length - 1 : prev - 1);
      } else if (e.key === 'Tab' || e.key === 'Enter') {
        if (selectedIndex >= 0 && suggestions[selectedIndex]) {
          e.preventDefault();
          const cmd = suggestions[selectedIndex];
          setMessage(cmd.name + ' ');
          setShowSuggestions(false);
          setSelectedIndex(-1);
        }
      }
    }
  };

  const insertCitation = (citation: Citation) => {
    const citationText = `[${citation.number}]`;
    setMessage(prev => prev + citationText + ' ');
  };

  return (
    <div className="border-t border-gray-200">
      {/* Command suggestions */}
      {showSuggestions && (
        <div className="absolute bottom-full mb-2 w-full bg-white rounded-lg shadow-lg border border-gray-200 max-h-64 overflow-y-auto">
          {suggestions.map((cmd, idx) => (
            <div
              key={cmd.name}
              className={`px-4 py-3 cursor-pointer ${
                idx === selectedIndex ? 'bg-blue-50' : 'hover:bg-gray-50'
              }`}
              onClick={() => {
                setMessage(cmd.name + ' ');
                setShowSuggestions(false);
                inputRef.current?.focus();
              }}
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-sm">{cmd.name}</div>
                  <div className="text-xs text-gray-500">{cmd.description}</div>
                  {cmd.usage && (
                    <div className="text-xs text-gray-400 mt-1 font-mono">{cmd.usage}</div>
                  )}
                </div>
                {cmd.aliases && cmd.aliases.length > 0 && (
                  <div className="text-xs text-gray-400">
                    Aliases: {cmd.aliases.join(', ')}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Citation bar */}
      {citations.length > 0 && (
        <div className="px-4 py-2 bg-blue-50 border-b border-blue-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="text-sm text-blue-700">
                {citations.length} citation{citations.length > 1 ? 's' : ''} ready
              </span>
              <div className="flex space-x-1">
                {citations.map(cite => (
                  <button
                    key={cite.id}
                    onClick={() => insertCitation(cite)}
                    className="px-2 py-0.5 text-xs bg-blue-100 hover:bg-blue-200 rounded text-blue-800"
                  >
                    [{cite.number}] {cite.source.title.slice(0, 20)}...
                  </button>
                ))}
              </div>
            </div>
            <button
              onClick={() => setCitations([])}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              Clear
            </button>
          </div>
        </div>
      )}

      {/* Input modes */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b">
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setInputMode('simple')}
            className={`px-2 py-1 rounded text-xs ${
              inputMode === 'simple' ? 'bg-blue-500 text-white' : 'bg-gray-200'
            }`}
          >
            Simple
          </button>
          <button
            onClick={() => setInputMode('editor')}
            className={`px-2 py-1 rounded text-xs ${
              inputMode === 'editor' ? 'bg-blue-500 text-white' : 'bg-gray-200'
            }`}
          >
            Editor
          </button>
          <button
            onClick={() => setShowCommandHelp(!showCommandHelp)}
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
            <option value={100}>Small</option>
            <option value={200}>Medium</option>
            <option value={300}>Large</option>
          </select>
        )}
      </div>

      {/* Command help */}
      {showCommandHelp && (
        <div className="px-4 py-3 bg-gray-50 border-b max-h-48 overflow-y-auto">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Available Commands</h4>
          <div className="space-y-1">
            {allCommands.map(cmd => (
              <div key={cmd.name} className="text-xs">
                <span className="font-mono text-blue-600">{cmd.name}</span>
                <span className="text-gray-600 ml-2">{cmd.description}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Processing indicator */}
      {commandProcessing && (
        <div className="px-4 py-2 bg-blue-50 text-blue-700 border-b">
          <span className="animate-spin inline-block mr-2">⏳</span> Processing command...
        </div>
      )}

      {/* Input form */}
      <form onSubmit={handleSubmit} className="p-4">
        {inputMode === 'simple' ? (
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={message}
              onChange={e => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type a message or use / for commands..."
              className="flex-1 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={isSending}
            />
            <button
              type="submit"
              disabled={!message.trim() || isSending}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSending ? 'Sending...' : 'Send'}
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            <MonacoEditor
              height={editorHeight}
              language="markdown"
              value={message}
              onChange={value => setMessage(value || '')}
              options={{
                fontSize: 14,
                minimap: { enabled: false },
                wordWrap: 'on',
                automaticLayout: true
              }}
            />
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={!message.trim() || isSending}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSending ? 'Sending...' : 'Send Message'}
              </button>
            </div>
          </div>
        )}
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
  userId: PropTypes.string.isRequired
};
