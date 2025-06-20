// components/chat/EnhancedMessageRenderer.jsx
/* global navigator */
import React, { useState, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
// Use a simple theme object instead of importing
const codeTheme = {
  'code[class*="language-"]': {
    color: '#f8f8f2',
    background: 'none',
    fontFamily: 'Consolas, Monaco, "Andale Mono", "Ubuntu Mono", monospace',
    fontSize: '1em',
    textAlign: 'left',
    whiteSpace: 'pre',
    wordSpacing: 'normal',
    wordBreak: 'normal',
    wordWrap: 'normal',
    lineHeight: '1.5',
    tabSize: '4',
    hyphens: 'none',
  },
  'pre[class*="language-"]': {
    color: '#f8f8f2',
    background: '#2d3748',
    fontFamily: 'Consolas, Monaco, "Andale Mono", "Ubuntu Mono", monospace',
    fontSize: '1em',
    textAlign: 'left',
    whiteSpace: 'pre',
    wordSpacing: 'normal',
    wordBreak: 'normal',
    wordWrap: 'normal',
    lineHeight: '1.5',
    tabSize: '4',
    hyphens: 'none',
    padding: '1em',
    margin: '.5em 0',
    overflow: 'auto',
    borderRadius: '0.3em',
  },
};
import {
  Copy,
  Check,
  ExternalLink,
  FileText,
  Code,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

import CitationRenderer from './CitationRenderer';

/* ───────────────────────────────────────────────────────────
 * Inline helpers
 * ─────────────────────────────────────────────────────────── */
function ContextBanner({ summary }) {
  return (
    <div className="flex items-center gap-2 text-sm text-gray-600 bg-blue-50 px-3 py-2 rounded-lg">
      <FileText className="w-4 h-4" />
      <span>
        Using {summary.documentsFound} documents and {summary.codeSnippetsFound} code snippets
      </span>
      <span className="text-xs text-gray-500">
        ({Math.round(summary.confidence * 100)}% confidence)
      </span>
    </div>
  );
}

function MetadataPanel({ metadata, open, onToggle }) {
  return (
    <div className="mt-4 pt-4 border-t border-gray-200 text-sm">
      <button
        onClick={onToggle}
        className="flex items-center gap-2 text-gray-600 hover:text-gray-800"
      >
        <span>Metadata</span>
        {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>

      {open && (
        <div className="mt-2 space-y-2 text-xs text-gray-600">
          {metadata.model && <div>Model: {metadata.model}</div>}
          {metadata.timestamp && (
            <div>Time: {new Date(metadata.timestamp).toLocaleString()}</div>
          )}
          {metadata.tokens && (
            <div>
              Tokens: {metadata.tokens.prompt} prompt, {metadata.tokens.completion} completion
            </div>
          )}
          {metadata.citations && <div>Citations: {metadata.citations.length}</div>}
        </div>
      )}
    </div>
  );
}

/* ───────────────────────────────────────────────────────────
 * Main component
 * ─────────────────────────────────────────────────────────── */
export default function EnhancedMessageRenderer({
  message,
  onCodeApply,
  onCitationClick,
  showMetadata = false
}) {
  const [copiedBlocks, setCopiedBlocks] = useState(new Set());
  const [expandedBlocks, setExpandedBlocks] = useState(new Set());
  const [showFullMetadata, setShowFullMetadata] = useState(false);

  /* --------------------------------------------------------
   * Utils
   * -------------------------------------------------------- */
  const handleCopy = async (blockId, code) => {
    await navigator.clipboard.writeText(code);
    setCopiedBlocks((prev) => new Set(prev).add(blockId));
    setTimeout(() => {
      setCopiedBlocks((prev) => {
        const n = new Set(prev);
        n.delete(blockId);
        return n;
      });
    }, 2000);
  };

  const toggleBlockExpansion = (blockId) => {
    setExpandedBlocks((prev) => {
      const n = new Set(prev);
      n.has(blockId) ? n.delete(blockId) : n.add(blockId);
      return n;
    });
  };

  /* --------------------------------------------------------
   * Memo-ised (in case heavy messages)
   * -------------------------------------------------------- */
  const processedContent = useMemo(() => message.content, [message.content]);

  /* --------------------------------------------------------
   * Markdown renderers
   * -------------------------------------------------------- */
  const components = {
    code({ node, inline, className, children, ...props }) {
      const match = /language-(\w+)/.exec(className || '');
      const language = match ? match[1] : '';
      const codeString = String(children).replace(/\n$/, '');

      // 🔑 stable identifier = message.id + starting position of the node
      const { line, column } = node.position.start;
      const blockId = `${message.id}-${line}-${column}`;

      /* ---------- INLINE ---------- */
      if (inline || !language) {
        return (
          <code
            className="bg-gray-100 px-1 py-0.5 rounded text-sm"
            {...props}
          >
            {children}
          </code>
        );
      }

      /* ---------- FENCED BLOCK ---------- */
      const lines = codeString.split('\n');
      const needsTruncate = lines.length > 20;
      const isExpanded = expandedBlocks.has(blockId);
      const displayCode =
        needsTruncate && !isExpanded
          ? [...lines.slice(0, 20), '// …'].join('\n')
          : codeString;

      return (
        <div className="relative my-4 group">
          {/* header */}
          <div className="flex justify-between items-center bg-gray-800 text-gray-300 px-4 py-2 rounded-t-lg">
            <span className="flex items-center gap-2 font-mono text-sm">
              <Code className="w-4 h-4" />
              {language}
            </span>

            <span className="flex items-center gap-2">
              {onCodeApply && (
                <button
                  onClick={() => onCodeApply(codeString, language)}
                  className="p-1 hover:bg-gray-700 rounded"
                  title="Apply to editor"
                >
                  <ExternalLink className="w-4 h-4" />
                </button>
              )}

              <button
                onClick={() => handleCopy(blockId, codeString)}
                className="p-1 hover:bg-gray-700 rounded"
                title="Copy code"
              >
                {copiedBlocks.has(blockId) ? (
                  <Check className="w-4 h-4 text-green-400" />
                ) : (
                  <Copy className="w-4 h-4" />
                )}
              </button>

              {needsTruncate && (
                <button
                  onClick={() => toggleBlockExpansion(blockId)}
                  className="p-1 hover:bg-gray-700 rounded"
                  title={isExpanded ? 'Collapse' : 'Expand'}
                >
                  {isExpanded ? (
                    <ChevronUp className="w-4 h-4" />
                  ) : (
                    <ChevronDown className="w-4 h-4" />
                  )}
                </button>
              )}
            </span>
          </div>

          {/* code body */}
          <SyntaxHighlighter
            language={language}
            style={codeTheme}
            customStyle={{
              margin: 0,
              borderTopLeftRadius: 0,
              borderTopRightRadius: 0,
              fontSize: '0.875rem'
            }}
            {...props}
          >
            {displayCode}
          </SyntaxHighlighter>
        </div>
      );
    }
  };

  /* --------------------------------------------------------
   * JSX
   * -------------------------------------------------------- */
  return (
    <div className="space-y-4">
      {/* Context banner */}
      {message.metadata?.contextSummary && (
        <ContextBanner summary={message.metadata.contextSummary} />
      )}

      {/* Content (with inline citations if present) */}
      {message.metadata?.citations?.length ? (
        <CitationRenderer
          text={processedContent}
          citations={message.metadata.citations}
          inline
          onCitationClick={onCitationClick}
        />
      ) : (
        <div className="prose prose-sm max-w-none">
          <ReactMarkdown components={components}>{processedContent}</ReactMarkdown>
        </div>
      )}

      {/* Optional metadata */}
      {showMetadata && message.metadata && (
        <MetadataPanel
          metadata={message.metadata}
          open={showFullMetadata}
          onToggle={() => setShowFullMetadata((open) => !open)}
        />
      )}
    </div>
  );
}
