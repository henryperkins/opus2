import React, { useState, useRef, useEffect } from 'react';
import MonacoEditor from '@monaco-editor/react';
import { searchAPI } from '../../api/search';
import { toast } from '../common/Toast';
import { useProjectTimeline } from '../../hooks/useProjects';

export default function CommandInput({ onSend, onTyping, projectId }) {
  const { addEvent } = useProjectTimeline(projectId);
  const [message, setMessage] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef(null);
  const [isTyping, setIsTyping] = useState(false);
  const [inputMode, setInputMode] = useState('simple'); // 'simple' or 'editor'
  const [editorHeight, setEditorHeight] = useState(100);
  const [isSending, setIsSending] = useState(false);
  const [commandProcessing, setCommandProcessing] = useState(false);

  // Command suggestions
  const commands = [
    { name: '/explain', description: 'Explain code functionality' },
    { name: '/generate-tests', description: 'Generate unit tests' },
    { name: '/summarize-pr', description: 'Summarize changes' },
    { name: '/grep', description: 'Search codebase' }
  ];

  useEffect(() => {
    // Check for slash commands
    if (message.startsWith('/')) {
      const partial = message.split(' ')[0];
      const matches = commands.filter(cmd =>
        cmd.name.startsWith(partial)
      );
      setSuggestions(matches);
      setShowSuggestions(matches.length > 0);
    } else {
      setShowSuggestions(false);
    }
  }, [message]);

  // Handle typing indicator
  useEffect(() => {
    if (message && !isTyping) {
      setIsTyping(true);
      onTyping?.(true);
    } else if (!message && isTyping) {
      setIsTyping(false);
      onTyping?.(false);
    }
  }, [message, isTyping, onTyping]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!message.trim() || isSending) return;

    setIsSending(true);
    const metadata = {};

    try {
      // Check for file references
      const fileRefs = message.match(/[a-zA-Z0-9_\-./]+\.[a-zA-Z]+/g);
      if (fileRefs) {
        metadata.referenced_files = fileRefs;
      }

      // Handle special commands
      if (message.startsWith('/')) {
        setCommandProcessing(true);
        await handleCommand(message, metadata);
      } else {
        await onSend(message, metadata);
        
        // Add chat activity to timeline
        await addEvent({
          event_type: 'chat_message',
          title: 'Chat message sent',
          description: message.length > 50 ? message.substring(0, 50) + '...' : message,
          metadata: {
            message_type: 'user',
            message_length: message.length,
            has_code_snippets: !!metadata.code_snippets?.length,
            referenced_files: metadata.referenced_files
          }
        });
      }

      setMessage('');
      setIsTyping(false);
      onTyping?.(false);
      
    } catch (error) {
      toast.error('Failed to send message');
      console.error('Message send error:', error);
    } finally {
      setIsSending(false);
      setCommandProcessing(false);
    }
  };

  const handleCommand = async (command, metadata) => {
    const [cmd, ...args] = command.split(' ');
    
    switch (cmd) {
      case '/explain':
        toast.info('Processing code explanation...');
        break;
      case '/generate-tests':
        toast.info('Generating tests...');
        break;
      case '/summarize-pr':
        toast.info('Summarizing changes...');
        break;
      case '/grep':
        if (args.length > 0) {
          toast.info(`Searching for "${args.join(' ')}"...`);
        }
        break;
      default:
        toast.warning(`Unknown command: ${cmd}`);
    }
    
    await onSend(command, { ...metadata, isCommand: true });
    
    // Add command activity to timeline
    await addEvent({
      event_type: 'chat_message',
      title: `Command executed: ${cmd}`,
      description: args.length > 0 ? `with arguments: ${args.join(' ')}` : 'no arguments',
      metadata: {
        message_type: 'command',
        command: cmd,
        arguments: args,
        command_length: command.length
      }
    });
  };

  const handleKeyDown = (e) => {
    if (showSuggestions && suggestions.length > 0) {
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
        case 'Tab':
        case 'Enter':
          if (selectedIndex >= 0) {
            e.preventDefault();
            const selected = suggestions[selectedIndex];
            setMessage(selected.name + ' ');
            setShowSuggestions(false);
            inputRef.current?.focus();
          }
          break;
        case 'Escape':
          setShowSuggestions(false);
          break;
      }
    }
  };

  return (
    <div className="relative border-t border-gray-200">
      {/* Command suggestions */}
      {showSuggestions && (
        <div className="absolute bottom-full left-0 right-0 bg-white border border-gray-200 shadow-lg rounded-t-lg">
          {suggestions.map((cmd, index) => (
            <div
              key={cmd.name}
              className={
                `px-4 py-2 hover:bg-gray-100 cursor-pointer ${
                  index === selectedIndex ? 'bg-blue-50' : ''
                }`
              }
              onClick={() => {
                setMessage(cmd.name + ' ');
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

      {/* Input mode toggle */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b">
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setInputMode('simple')}
            className={`px-2 py-1 text-xs rounded ${
              inputMode === 'simple' 
                ? 'bg-blue-500 text-white' 
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Simple
          </button>
          <button
            onClick={() => setInputMode('editor')}
            className={`px-2 py-1 text-xs rounded ${
              inputMode === 'editor' 
                ? 'bg-blue-500 text-white' 
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Code Editor
          </button>
        </div>
        
        {inputMode === 'editor' && (
          <div className="flex items-center space-x-2">
            <label className="text-xs text-gray-600">Height:</label>
            <select 
              value={editorHeight} 
              onChange={(e) => setEditorHeight(Number(e.target.value))}
              className="text-xs border rounded px-1 py-0.5"
            >
              <option value={100}>Small</option>
              <option value={200}>Medium</option>
              <option value={300}>Large</option>
            </select>
          </div>
        )}
      </div>

      {/* Command Processing Indicator */}
      {commandProcessing && (
        <div className="px-4 py-2 bg-blue-50 border-b border-blue-200">
          <div className="flex items-center text-blue-700 text-sm">
            <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Processing command...
          </div>
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
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type a message or use /command..."
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="submit"
              disabled={!message.trim() || isSending}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              {isSending && (
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              )}
              {isSending ? 'Sending...' : 'Send'}
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            <div className="border border-gray-300 rounded-lg overflow-hidden">
              <MonacoEditor
                height={`${editorHeight}px`}
                defaultLanguage="markdown"
                value={message}
                onChange={(value) => setMessage(value || '')}
                theme="vs-light"
                options={{
                  fontSize: 14,
                  lineNumbers: 'off',
                  minimap: { enabled: false },
                  scrollBeyondLastLine: false,
                  wordWrap: 'on',
                  folding: false,
                  lineDecorationsWidth: 0,
                  lineNumbersMinChars: 0,
                  glyphMargin: false,
                  automaticLayout: true
                }}
              />
            </div>
            <div className="flex justify-between items-center">
              <div className="text-xs text-gray-500">
                Supports markdown, code blocks, and @mentions
              </div>
              <button
                type="submit"
                disabled={!message.trim() || isSending}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
              >
                {isSending && (
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                )}
                {isSending ? 'Sending...' : 'Send Message'}
              </button>
            </div>
          </div>
        )}
      </form>
    </div>
  );
}
