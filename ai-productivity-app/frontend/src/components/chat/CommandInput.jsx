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
