// components/chat/EnhancedCommandInput.jsx
import React, { useState, useRef, useEffect } from 'react';
import MonacoEditor from '@monaco-editor/react';
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

import { useProjectTimeline } from '../../hooks/useProjects';
import { KnowledgeCommandRegistry } from '../../utils/commands/knowledge-commands';
import PropTypes from 'prop-types';
import { toast } from '../common/Toast';


// ────────────────────────────────────────────────────────────
// Command registry + static commands
// ────────────────────────────────────────────────────────────
const commandRegistry = new KnowledgeCommandRegistry();

const standardCommands = [
  { name: '/explain',       description: 'Explain code functionality' },
  { name: '/generate-tests',description: 'Generate unit tests' },
  { name: '/summarize-pr',  description: 'Summarize changes' },
  { name: '/grep',          description: 'Search codebase' }
];

const allCommands = [
  ...standardCommands,
  ...commandRegistry.getAll().map(c => ({
    name:        c.name,
    description: c.description,
    usage:       c.usage,
    aliases:     c.aliases
  }))
];

// ────────────────────────────────────────────────────────────
// Main component
// ────────────────────────────────────────────────────────────
export default function EnhancedCommandInput({
  onSend,
  onTyping,
  projectId,
  editorContent,
  selectedText,
  currentFile,
  userId
}) {
  /* ---------------- state ---------------- */
  const { addEvent }   = useProjectTimeline(projectId);
  const [message,          setMessage]          = useState('');
  const [attachments,      setAttachments]      = useState([]);     // NEW
  const [suggestions,      setSuggestions]      = useState([]);
  const [showSuggestions,  setShowSuggestions]  = useState(false);
  const [selectedIndex,    setSelectedIndex]    = useState(-1);
  const [inputMode,        setInputMode]        = useState('simple');
  const [editorHeight,     setEditorHeight]     = useState(200);
  const [isSending,        setIsSending]        = useState(false);
  const [commandProcessing,setCommandProcessing]= useState(false);
  const [citations,        setCitations]        = useState([]);
  const [showCommandHelp,  setShowCommandHelp]  = useState(false);
  const [isTyping,         setIsTyping]         = useState(false);

  const inputRef    = useRef(null);
  const textareaRef = useRef(null);

  /* ---------------- slash-command suggestions ---------------- */
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

  /* ---------------- typing indicator ---------------- */
  useEffect(() => {
    const currentlyTyping = Boolean(message.trim());
    if (currentlyTyping !== isTyping) {
      setIsTyping(currentlyTyping);
      onTyping?.(currentlyTyping);
    }
  }, [message, isTyping, onTyping]);

  /* ---------------- utils ---------------- */
  const insertCitation = (citation) =>
    setMessage(prev => `${prev}[${citation.number}] `);


  /* ---------------- knowledge command runner ---------------- */
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

    // If the command prepares a prompt for the LLM, send that up;
    // otherwise we are done locally.
    if (result.requiresLLM) {
      return {
        payload: result.prompt ?? cmdLine,
        meta: {
          isCommand: true,
          commandType: 'knowledge',
          citations : result.citations ?? undefined
        },
        shouldSend: true
      };
    }

    toast.success(result.message || 'Command executed successfully');
    return { shouldSend: false };
  };

  /* ---------------- submit ---------------- */
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!message.trim() || isSending) return;

    setIsSending(true);
    setCommandProcessing(true);

    try {
      const meta = citations.length ? { citations } : {};

      if (message.startsWith('/')) {
        const firstToken   = message.split(' ')[0];
        const knowledgeCmd = commandRegistry.get(firstToken);

        if (knowledgeCmd) {
          const { payload, meta: extraMeta, shouldSend } =
            await runKnowledgeCommand(message);

          if (shouldSend) {
            await onSend(payload, { ...meta, ...extraMeta });
          }
        } else {
          // standard (non-knowledge) slash command
          await onSend(message, { ...meta, isCommand: true });
        }
      } else {
        // plain chat message
        if (message.includes('@editor') && editorContent) {
          meta.code_snippets = [{ language: 'auto', code: editorContent }];
        }

        if (attachments.length) meta.attachments = attachments;

        await onSend(message, meta);
      }

      // timeline
      await addEvent({
        event_type : 'comment',
        title      : message.startsWith('/') ? 'Command executed' : 'Message sent',
        description: message.slice(0, 100),
        metadata   : { chat: true, has_citations: citations.length > 0 }
      });

      // reset
      setMessage('');
      setCitations([]);
      setAttachments([]);
    } catch (err) {
      toast.error('Failed to send message');
      console.error(err);
    } finally {
      setIsSending(false);
      setCommandProcessing(false);
    }
  };

  /* ---------------- key handling ---------------- */
  const handleKeyDown = (e) => {
    // suggestions navigation
    if (showSuggestions && suggestions.length) {
      if (['ArrowDown', 'ArrowUp'].includes(e.key)) {
        e.preventDefault();
        setSelectedIndex(idx =>
          e.key === 'ArrowDown'
            ? (idx + 1) % suggestions.length
            : idx <= 0 ? suggestions.length - 1 : idx - 1
        );
        return;
      }
      if (['Enter', 'Tab'].includes(e.key) && selectedIndex >= 0) {
        e.preventDefault();
        const cmd = suggestions[selectedIndex];
        setMessage(cmd.name + ' ');
        setShowSuggestions(false);
        setSelectedIndex(-1);
        return;
      }
    }

    // plain Enter to send (textarea only)
    if (e.key === 'Enter' && !e.shiftKey && inputMode === 'simple') {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  /* ---------------- jsx ---------------- */
  return (
    <div className="border-t border-gray-200 relative bg-white">
      {/* ─── Suggestions dropdown ────────────────────── */}
      {showSuggestions && (
        <div className="absolute bottom-full mb-2 w-full max-h-60 overflow-y-auto
                        bg-white shadow border rounded-lg z-10">
          {suggestions.map((cmd, idx) => (
            <div
              key={cmd.name}
              className={`px-4 py-3 cursor-pointer text-sm
                         ${idx === selectedIndex ? 'bg-blue-50' : 'hover:bg-gray-50'}`}
              onMouseDown={() => {
                // onMouseDown so the input does not lose focus
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

      {/* ─── Citation bar ────────────────────────────── */}
      {citations.length > 0 && (
        <div className="px-4 py-2 bg-blue-50 border-b flex justify-between items-center">
          <span className="text-sm text-blue-700">
            {citations.length} citation{citations.length > 1 && 's'} ready
          </span>
          <div className="flex gap-1">
            {citations.map(c => (
              <button
                key={c.id}
                onClick={() => insertCitation(c)}
                className="px-2 text-xs bg-blue-100 hover:bg-blue-200 rounded text-blue-800"
              >
                [{c.number}]
              </button>
            ))}
          </div>
          <button
            onClick={() => setCitations([])}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            Clear
          </button>
        </div>
      )}

      {/* ─── Mode / help bar ─────────────────────────── */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b">
        <div className="flex gap-2">
          {['simple', 'editor'].map(mode => (
            <button
              key={mode}
              onClick={() => setInputMode(mode)}
              className={`px-2 py-1 rounded text-xs
                         ${inputMode === mode ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
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
              <option key={h} value={h}>{h === 100 ? 'Small' : h === 200 ? 'Medium' : 'Large'}</option>
            ))}
          </select>
        )}
      </div>

      {/* ─── Command help dropdown ───────────────────── */}
      {showCommandHelp && (
        <div className="px-4 py-3 bg-gray-50 border-b max-h-48 overflow-y-auto text-xs">
          {allCommands.map(c => (
            <div key={c.name} className="mb-1">
              <span className="font-mono text-blue-600">{c.name}</span>
              <span className="ml-2 text-gray-600">{c.description}</span>
            </div>
          ))}
        </div>
      )}

      {/* ─── Processing indicator ───────────────────── */}
      {commandProcessing && (
        <div className="px-4 py-2 bg-blue-50 text-blue-700 border-b text-sm">
          <span className="animate-spin inline-block mr-1">⏳</span>
          Processing command…
        </div>
      )}

      {/* ─── Input form ─────────────────────────────── */}
      <form onSubmit={handleSubmit} className="p-4 space-y-2">
        {/* context badges */}
        {(currentFile || selectedText || editorContent) && (
          <div className="flex flex-wrap gap-2 text-xs">
            {currentFile   && <span className="badge-blue">📄 {currentFile}</span>}
            {selectedText  && <span className="badge-green">✂️ Selected text</span>}
            {editorContent && <span className="badge-purple">💻 Editor content</span>}
          </div>
        )}

        {/* attachments preview */}
        {attachments.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {attachments.map((a,i) => (
              <div key={i} className="flex items-center space-x-1 bg-gray-100 px-2 py-1 rounded">
                <span className="text-sm">{a.name}</span>
                <button
                  type="button"
                  onClick={() => setAttachments(prev => prev.filter((_,idx)=>idx!==i))}
                  className="text-gray-500 hover:text-red-500"
                >×</button>
              </div>
            ))}
          </div>
        )}

        {/* ---------------- input area ---------------- */}
        {inputMode === 'simple' ? (
          <div className="flex gap-2">
            <textarea
              ref={textareaRef}
              value={message}
              onChange={e => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              style={{ maxHeight: 120 }}
              placeholder="Type a message or use / for commands …"
              className="flex-1 resize-none rounded-lg border px-3 py-2 focus:ring-2
                         focus:ring-blue-500 focus:border-transparent"
            />

            {/* action buttons */}
            <div className="flex flex-col gap-1">
              <button
                type="button"
                onClick={() => {}}
                disabled
                className="icon-btn"
                title="Attach file (coming soon)"
              >
                <Paperclip className="w-5 h-5" />
              </button>
              <button
                type="button"
                onClick={() => {}}
                disabled
                className="icon-btn"
                title="Voice recording (coming soon)"
              >
                <Mic className="w-5 h-5" />
              </button>
              <button
                type="submit"
                disabled={isSending || (!message.trim() && attachments.length === 0)}
                className="icon-btn text-blue-500 disabled:text-gray-300"
                title="Send"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        ) : (
          <>
            <MonacoEditor
              height={editorHeight}
              language="markdown"
              value={message}
              onChange={(v)=>setMessage(v ?? '')}
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
                disabled={!message.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg
                           hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSending ? 'Sending…' : 'Send'}
              </button>
            </div>
          </>
        )}

      </form>
    </div>
  );
}

/* ════════════════ tiny badge css helpers (tailwind) ════════════════
.badge-blue   { @apply px-2 py-1 rounded bg-blue-100  text-blue-700;  }
.badge-green  { @apply px-2 py-1 rounded bg-green-100 text-green-700; }
.badge-purple { @apply px-2 py-1 rounded bg-purple-100 text-purple-700; }
.icon-btn     { @apply p-2 rounded-lg hover:bg-gray-100 text-gray-500; }
*/
