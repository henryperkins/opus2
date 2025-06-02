import React, { useState, useRef, useEffect } from 'react';
import { searchAPI } from '../../api/search';

export default function CommandInput({ onSend, onTyping, projectId }) {
  const [message, setMessage] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef(null);
  const [isTyping, setIsTyping] = useState(false);

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

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!message.trim()) return;

    const metadata = {};

    // Check for file references
    const fileRefs = message.match(/[a-zA-Z0-9_\-./]+\.[a-zA-Z]+/g);
    if (fileRefs) {
      metadata.referenced_files = fileRefs;
    }

    onSend(message, metadata);
    setMessage('');
    setIsTyping(false);
    onTyping?.(false);
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

      {/* Input form */}
      <form onSubmit={handleSubmit} className="flex gap-2 p-4">
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
          disabled={!message.trim()}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Send
        </button>
      </form>
    </div>
  );
}
