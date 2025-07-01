// components/chat/EnhancedMessageRenderer.jsx
/* eslint-env browser */
import React, { useState, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter/dist/cjs/prism';
import { oneDark } from 'react-syntax-highlighter/dist/cjs/styles/prism';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import mermaid from 'mermaid';
import 'katex/dist/katex.min.css';

import {
  Copy,
  Check,
  Play,
  ExternalLink,
  FileText,
  Code as CodeIcon,
  ChevronDown,
  ChevronUp,
  Table,
  BarChart2,
  Hash,
  RotateCcw
} from 'lucide-react';

import CitationRenderer from './CitationRenderer';

// Fallback icon component
const FallbackIcon = ({ className }) => (
  <span className={className} style={{ display: 'inline-block', width: '1rem', height: '1rem' }}>⚫</span>
);

// Initialize mermaid
mermaid.initialize({ startOnLoad: false, theme: 'dark' });

/* ───────────────────────────────────────────────────────────
 * Inline helpers
 * ─────────────────────────────────────────────────────────── */
function ContextBanner({ summary }) {
  return (
    <div className="flex items-center gap-2 text-sm text-gray-600 bg-blue-50 dark:bg-blue-900/20 px-3 py-2 rounded-lg">
      <FileText className="w-4 h-4" />
      <span>
        Using {summary.documentsFound} documents and {summary.codeSnippetsFound} code snippets
      </span>
      <span className="text-xs text-gray-500 dark:text-gray-400">
        ({Math.round(summary.confidence * 100)}% confidence)
      </span>
    </div>
  );
}

function MetadataPanel({ metadata, open, onToggle }) {
  return (
    <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 text-sm">
      <button
        onClick={onToggle}
        className="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
      >
        <span>Metadata</span>
        {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>

      {open && (
        <div className="mt-2 space-y-2 text-xs text-gray-600 dark:text-gray-400">
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
 * Special content renderers
 * ─────────────────────────────────────────────────────────── */
// Mermaid diagram renderer
const MermaidDiagram = ({ chart, onClick }) => {
  const [svg, setSvg] = useState('');
  const [error, setError] = useState(null);

  React.useEffect(() => {
    const renderDiagram = async () => {
      try {
        const id = `mermaid-${Date.now()}`;
        const { svg } = await mermaid.render(id, chart);
        setSvg(svg);
      } catch (err) {
        setError('Failed to render diagram');
        console.error('Mermaid error:', err);
      }
    };

    renderDiagram();
  }, [chart]);

  if (error) {
    return (
      <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg text-red-600 dark:text-red-400">
        {error}
      </div>
    );
  }

  return (
    <div
      className="my-4 bg-gray-50 dark:bg-gray-800 rounded-lg p-4 overflow-x-auto cursor-pointer"
      onClick={onClick}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
};

// Interactive table component
const InteractiveTable = ({ data }) => {
  const [sortColumn, setSortColumn] = useState(null);
  const [sortDirection, setSortDirection] = useState('asc');

  const sortedData = useMemo(() => {
    if (sortColumn === null || data.length < 2) return data;

    const [header, ...rows] = data;
    const sorted = [...rows].sort((a, b) => {
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];

      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
      }

      return sortDirection === 'asc'
        ? String(aVal).localeCompare(String(bVal))
        : String(bVal).localeCompare(String(aVal));
    });

    return [header, ...sorted];
  }, [data, sortColumn, sortDirection]);

  const handleSort = (columnIndex) => {
    if (sortColumn === columnIndex) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(columnIndex);
      setSortDirection('asc');
    }
  };

  if (data.length === 0) return null;

  const [header, ...rows] = sortedData;

  return (
    <div className="my-4 overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
        <thead className="bg-gray-50 dark:bg-gray-800">
          <tr>
            {header.map((cell, idx) => (
              <th
                key={idx}
                onClick={() => handleSort(idx)}
                className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                <div className="flex items-center space-x-1">
                  <span>{cell}</span>
                  <Hash className="w-3 h-3 opacity-50" />
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
          {rows.map((row, rowIdx) => (
            <tr key={rowIdx} className="hover:bg-gray-50 dark:hover:bg-gray-800">
              {row.map((cell, cellIdx) => (
                <td key={cellIdx} className="px-4 py-2 text-sm text-gray-900 dark:text-gray-100">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

// Chart renderer (placeholder - would integrate with a charting library)
const ChartRenderer = ({ type, data }) => {
  return (
    <div className="my-4 p-8 bg-gray-50 dark:bg-gray-800 rounded-lg text-center">
      <BarChart2 className="w-12 h-12 mx-auto mb-2 text-gray-400" />
      <p className="text-sm text-gray-600 dark:text-gray-400">
        {type} chart visualization would appear here
      </p>
    </div>
  );
};

/* ───────────────────────────────────────────────────────────
 * Main component
 * ─────────────────────────────────────────────────────────── */
export default function EnhancedMessageRenderer({
  message,
  content,  // Support both message.content and direct content
  metadata, // Support both message.metadata and direct metadata
  onCodeRun,
  onCodeApply,
  onDiagramClick,
  onCitationClick,
  onRetry,
  showMetadata = false
}) {
  const [activeTab, setActiveTab] = useState('rendered');
  const [copiedBlocks, setCopiedBlocks] = useState(new Set());
  const [expandedBlocks, setExpandedBlocks] = useState(new Set());
  const [showFullMetadata, setShowFullMetadata] = useState(false);
  const [messageCopied, setMessageCopied] = useState(false);

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

  const handleCopyMessage = async () => {
    await navigator.clipboard.writeText(messageContent);
    setMessageCopied(true);
    setTimeout(() => {
      setMessageCopied(false);
    }, 2000);
  };

  /* --------------------------------------------------------
   * Content processing
   * -------------------------------------------------------- */
  // Handle both message object style and direct content style
  const messageContent = message?.content || content;
  const messageMetadata = message?.metadata || metadata;
  const messageId = message?.id || 'msg';

  // Parse special content blocks with optimized regex processing
  const { processedContent, specialBlocks } = useMemo(() => {
    // Skip processing if content is empty or very short
    if (!messageContent || messageContent.length < 10) {
      return { processedContent: messageContent, specialBlocks: [] };
    }

    let processed = messageContent;
    const blocks = [];

    // Batch regex operations for better performance
    try {
      // Extract mermaid diagrams
      if (processed.includes('```mermaid')) {
        const mermaidRegex = /```mermaid\n([\s\S]*?)```/g;
        processed = processed.replace(mermaidRegex, (match, diagram) => {
          const id = `mermaid-${blocks.length}`;
          blocks.push({ type: 'mermaid', id, content: diagram.trim() });
          return `<div id="${id}"></div>`;
        });
      }

      // Extract tables (simple markdown tables) - only if contains table markers
      if (processed.includes('|') && processed.includes('\n')) {
        const tableRegex = /\|(.+)\|[\s\S]*?\n\|(.+)\|/g;
        const tables = processed.match(tableRegex);
        if (tables && tables.length > 0) {
          tables.forEach((table, idx) => {
            try {
              const rows = table.trim().split('\n')
                .filter(row => row.includes('|') && !row.match(/^\|[-:\s|]+\|$/))
                .map(row => row.split('|').slice(1, -1).map(cell => cell.trim()));

              if (rows.length > 1) {
                const id = `table-${idx}`;
                blocks.push({ type: 'table', id, content: rows });
              }
            } catch (e) {
              console.warn('Table parsing error:', e);
            }
          });
        }
      }
    } catch (error) {
      console.warn('Content processing error:', error);
      return { processedContent: messageContent, specialBlocks: [] };
    }

    return { processedContent: processed, specialBlocks: blocks };
  }, [messageContent]);

  /* --------------------------------------------------------
   * Markdown renderers
   * -------------------------------------------------------- */
  const components = {
    code({ node, inline, className, children, ...props }) {
      const match = /language-(\w+)/.exec(className || '');
      const language = match ? match[1] : '';
      const codeString = String(children).replace(/\n$/, '');

      // 🔑 stable identifier = message.id + starting position of the node
      const position = node.position || { start: { line: 0, column: 0 } };
      const { line, column } = position.start;
      const blockId = `${messageId}-${line}-${column}`;

      /* ---------- INLINE ---------- */
      if (inline || !language) {
        return (
          <code
            className="bg-gray-100 dark:bg-gray-800 px-1 py-0.5 rounded text-sm"
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
              {CodeIcon ? <CodeIcon className="w-4 h-4" /> : <FallbackIcon className="w-4 h-4" />}
              {language}
            </span>

            <span className="flex items-center gap-2">
              {['python', 'javascript', 'typescript'].includes(language) && onCodeRun && (
                <button
                  onClick={() => onCodeRun(codeString, language)}
                  className="p-1 hover:bg-green-600 bg-green-700 rounded"
                  title="Run code"
                >
                  {Play ? <Play className="w-4 h-4" /> : <FallbackIcon className="w-4 h-4" />}
                </button>
              )}

              {onCodeApply && (
                <button
                  onClick={() => onCodeApply(codeString, language)}
                  className="p-1 hover:bg-blue-600 bg-blue-700 rounded"
                  title="Apply to editor"
                >
                  {ExternalLink ? <ExternalLink className="w-4 h-4" /> : <FallbackIcon className="w-4 h-4" />}
                </button>
              )}

              <button
                onClick={() => handleCopy(blockId, codeString)}
                className="p-1 hover:bg-gray-700 rounded"
                title="Copy code"
              >
                {copiedBlocks.has(blockId) ? (
                  Check ? <Check className="w-4 h-4 text-green-400" /> : <FallbackIcon className="w-4 h-4 text-green-400" />
                ) : (
                  Copy ? <Copy className="w-4 h-4" /> : <FallbackIcon className="w-4 h-4" />
                )}
              </button>

              {needsTruncate && (
                <button
                  onClick={() => toggleBlockExpansion(blockId)}
                  className="p-1 hover:bg-gray-700 rounded"
                  title={isExpanded ? 'Collapse' : 'Expand'}
                >
                  {isExpanded ? (
                    ChevronUp ? <ChevronUp className="w-4 h-4" /> : <FallbackIcon className="w-4 h-4" />
                  ) : (
                    ChevronDown ? <ChevronDown className="w-4 h-4" /> : <FallbackIcon className="w-4 h-4" />
                  )}
                </button>
              )}
            </span>
          </div>

          {/* code body */}
          {SyntaxHighlighter ? (
            <SyntaxHighlighter
              language={language}
              style={oneDark || {}}
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
          ) : (
            <pre className="bg-gray-800 text-gray-100 p-4 rounded-b-lg overflow-x-auto">
              <code className="text-sm font-mono">{displayCode}</code>
            </pre>
          )}
        </div>
      );
    }
  };

  // Render special blocks
  const renderSpecialBlock = (block) => {
    switch (block.type) {
      case 'mermaid':
        return (
          <MermaidDiagram
            key={block.id}
            chart={block.content}
            onClick={() => onDiagramClick?.(block.content)}
          />
        );
      case 'table':
        return (
          <InteractiveTable
            key={block.id}
            data={block.content}
          />
        );
      case 'chart':
        return (
          <ChartRenderer
            key={block.id}
            type={block.chartType}
            data={block.content}
          />
        );
      default:
        return null;
    }
  };

  /* --------------------------------------------------------
   * JSX
   * -------------------------------------------------------- */
  return (
    <div className="space-y-4">
      {/* Context banner */}
      {messageMetadata?.contextSummary && (
        <ContextBanner summary={messageMetadata.contextSummary} />
      )}

      {/* Tab switcher for raw/rendered view */}
      <div className="flex items-center justify-end mb-2 space-x-2">
        <button
          onClick={() => setActiveTab('rendered')}
          className={`text-xs px-2 py-1 rounded ${
            activeTab === 'rendered'
              ? 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <FileText className="w-3 h-3 inline mr-1" />
          Rendered
        </button>
        <button
          onClick={() => setActiveTab('raw')}
          className={`text-xs px-2 py-1 rounded ${
            activeTab === 'raw'
              ? 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          {CodeIcon ? (
            <CodeIcon className="w-3 h-3 inline mr-1" />
          ) : (
            <FallbackIcon className="w-3 h-3 inline mr-1" />
          )}
          Raw
        </button>
      </div>

      {activeTab === 'rendered' ? (
        <div>
          {/* Content (with inline citations if present) */}
          {messageMetadata?.citations?.length ? (
            <CitationRenderer
              text={processedContent}
              citations={messageMetadata.citations}
              inline
              onCitationClick={onCitationClick}
            />
          ) : (
            <div className="message-content max-w-none">
              <ReactMarkdown
                components={components}
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeKatex]}
              >
                {processedContent}
              </ReactMarkdown>
            </div>
          )}

          {/* Render special blocks */}
          {specialBlocks.map(block => renderSpecialBlock(block))}

          {/* Render metadata charts/tables if any */}
          {messageMetadata?.charts?.map((chart, idx) => (
            <ChartRenderer
              key={`meta-chart-${idx}`}
              type={chart.type}
              data={chart.data}
            />
          ))}

          {messageMetadata?.tables?.map((table, idx) => (
            <InteractiveTable
              key={`meta-table-${idx}`}
              data={table}
            />
          ))}
        </div>
      ) : (
        <pre className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg overflow-x-auto">
          <code className="text-sm">{messageContent}</code>
        </pre>
      )}

      {/* Action buttons */}
      <div className="mt-3 flex justify-end gap-2">
        {/* Retry button for assistant messages */}
        {message?.role === 'assistant' && onRetry && (
          <button
            onClick={() => onRetry(message.id)}
            className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
            title="Regenerate response"
          >
            <RotateCcw className="w-4 h-4" />
            <span>Retry</span>
          </button>
        )}
        
        {/* Copy message button */}
        <button
          onClick={handleCopyMessage}
          className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
          title="Copy entire message"
        >
          {messageCopied ? (
            <>
              <Check className="w-4 h-4 text-green-500" />
              <span className="text-green-500">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-4 h-4" />
              <span>Copy message</span>
            </>
          )}
        </button>
      </div>

      {/* Optional metadata */}
      {showMetadata && messageMetadata && (
        <MetadataPanel
          metadata={messageMetadata}
          open={showFullMetadata}
          onToggle={() => setShowFullMetadata((open) => !open)}
        />
      )}
    </div>
  );
}
