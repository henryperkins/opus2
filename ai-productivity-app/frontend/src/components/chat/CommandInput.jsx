/* eslint-env browser */
import { useState, useRef, useEffect, useCallback } from 'react';
import MonacoEditor from '@monaco-editor/react';
import { toast } from '../common/Toast';
import { useProjectTimeline } from '../../hooks/useProjects';
import PropTypes from 'prop-types';

export default function CommandInput({ onSend, onTyping = null, projectId }) {
  const { addEvent } = useProjectTimeline(projectId);
  const [message, setMessage] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef(null);
  const [isTyping, setIsTyping] = useState(false);
  const [inputMode, setInputMode] = useState('simple');
  const [editorHeight, setEditorHeight] = useState(100);
  const [isSending, setIsSending] = useState(false);
  const [commandProcessing, setCommandProcessing] = useState(false);

  const commands = useRef([
    { name: '/explain', description: 'Explain code functionality' },
    { name: '/generate-tests', description: 'Generate unit tests' },
    { name: '/summarize-pr', description: 'Summarize changes' },
    { name: '/grep', description: 'Search codebase' },
  ]).current;

  useEffect(() => {
    if (message.startsWith('/')) {
      const partial = message.split(' ')[0];
      const matches = commands.filter(cmd => cmd.name.startsWith(partial));
      setSuggestions(matches);
      setShowSuggestions(matches.length > 0);
    } else {
      setShowSuggestions(false);
    }
  }, [message, commands]);

  useEffect(() => {
    const typingNow = Boolean(message.trim());
    if (typingNow !== isTyping) {
      setIsTyping(typingNow);
      onTyping?.(typingNow);
    }
  }, [message, isTyping, onTyping]);

  const handleCommand = useCallback(async (command, metadata) => {
    const [cmd, ...args] = command.split(' ');
    toast.info(`Executing command: ${cmd}`);

    await onSend(command, { ...metadata, isCommand: true });

    // Create timeline event (non-blocking)
    try {
      await addEvent({
        event_type: 'chat_message',
        title: `Command executed: ${cmd}`,
        description: args.length ? `Arguments: ${args.join(' ')}` : 'No arguments',
        metadata: {
          message_type: 'command',
          command: cmd,
          arguments: args,
        },
      });
    } catch (error) {
      console.warn('Failed to create timeline event for command:', error);
      // Don't block chat functionality - timeline events are non-critical
    }
  }, [onSend, addEvent]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!message.trim() || isSending) return;

    setIsSending(true);
    const metadata = {};
    const fileRefs = message.match(/[a-zA-Z0-9_\-./]+\.[a-zA-Z]+/g);
    if (fileRefs) metadata.referenced_files = fileRefs;

    try {
      if (message.startsWith('/')) {
        setCommandProcessing(true);
        await handleCommand(message, metadata);
      } else {
        await onSend(message, metadata);
        // Create timeline event (non-blocking)
        try {
          await addEvent({
            event_type: 'chat_message',
            title: 'Chat message sent',
            description: message.slice(0, 50),
            metadata: {
              message_type: 'user',
              message_length: message.length,
              referenced_files: metadata.referenced_files,
            },
          });
        } catch (error) {
          console.warn('Failed to create timeline event for message:', error);
          // Don't block chat functionality - timeline events are non-critical
        }
      }

      setMessage('');
    } catch (error) {
      toast.error('Failed to send message');
      console.error(error);
    } finally {
      setIsSending(false);
      setCommandProcessing(false);
    }
  };

  const handleKeyDown = (e) => {
    if (!showSuggestions) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(i => Math.min(i + 1, suggestions.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(i => Math.max(i - 1, 0));
    } else if (['Tab', 'Enter'].includes(e.key)) {
      if (selectedIndex >= 0) {
        e.preventDefault();
        setMessage(`${suggestions[selectedIndex].name} `);
        setShowSuggestions(false);
        inputRef.current?.focus();
      }
    } else if (e.key === 'Escape') {
      setShowSuggestions(false);
    }
  };

  return (
    <div className="relative border-t border-gray-200">
      {showSuggestions && (
        <div className="absolute bottom-full inset-x-0 bg-white border shadow rounded-t-lg">
          {suggestions.map((cmd, i) => (
            <div
              key={cmd.name}
              className={`px-4 py-2 cursor-pointer ${i === selectedIndex ? 'bg-blue-50' : 'hover:bg-gray-100'}`}
              onClick={() => {
                setMessage(`${cmd.name} `);
                setShowSuggestions(false);
                inputRef.current?.focus();
              }}
            >
              <div className="font-medium text-sm">{cmd.name}</div>
              <div className="text-xs text-gray-500">{cmd.description}</div>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b">
        <div className="flex space-x-2">
          <button
            onClick={() => setInputMode('simple')}
            className={`px-2 py-1 rounded text-xs ${inputMode === 'simple' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
          >
            Simple
          </button>
          <button
            onClick={() => setInputMode('editor')}
            className={`px-2 py-1 rounded text-xs ${inputMode === 'editor' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
          >
            Editor
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

      {commandProcessing && (
        <div className="px-4 py-2 bg-blue-50 text-blue-700 border-b">
          <span className="animate-spin inline-block mr-2">⏳</span> Processing command...
        </div>
      )}

      <form onSubmit={handleSubmit} className="p-4">
        {inputMode === 'simple' ? (
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={message}
              onChange={e => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type or use /command"
              className="flex-1 px-3 py-2 border rounded-lg focus:ring-2"
            />
            <button disabled={!message.trim() || isSending} className="px-4 py-2 bg-blue-600 text-white rounded-lg disabled:opacity-50">
              {isSending ? 'Sending...' : 'Send'}
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            <MonacoEditor
              height={editorHeight}
              language="markdown"
              value={message}
              onChange={setMessage}
              options={{
                fontSize: 14,
                minimap: { enabled: false },
                wordWrap: 'on',
                automaticLayout: true,
              }}
            />
            <div className="flex justify-end">
              <button disabled={!message.trim() || isSending} className="px-4 py-2 bg-blue-600 text-white rounded-lg disabled:opacity-50">
                {isSending ? 'Sending...' : 'Send Message'}
              </button>
            </div>
          </div>
        )}
      </form>
    </div>
  );
}

CommandInput.propTypes = {
  onSend: PropTypes.func.isRequired,
  onTyping: PropTypes.func,
  projectId: PropTypes.string.isRequired,
};

