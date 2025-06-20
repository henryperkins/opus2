// components/chat/EnhancedMessageRenderer.jsx
/* global navigator */
import React, { useState, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check, ExternalLink, FileText, Code, ChevronDown, ChevronUp } from 'lucide-react';
import CitationRenderer from './CitationRenderer';

export default function EnhancedMessageRenderer({
  message,
  onCodeApply,
  onCitationClick,
  showMetadata = false
}) {
  const [copiedBlocks, setCopiedBlocks] = useState(new Set());
  const [expandedBlocks, setExpandedBlocks] = useState(new Set());
  const [showFullMetadata, setShowFullMetadata] = useState(false);

  // Extract code blocks and citations from content
  const { processedContent, codeBlocks } = useMemo(() => {
    return extractCodeBlocks(message.content);
  }, [message.content]);

  const handleCopyCode = async (blockId, code) => {
    await navigator.clipboard.writeText(code);
    setCopiedBlocks(prev => new Set(prev).add(blockId));
    setTimeout(() => {
      setCopiedBlocks(prev => {
        const newSet = new Set(prev);
        newSet.delete(blockId);
        return newSet;
      });
    }, 2000);
  };

  const toggleBlockExpansion = (blockId) => {
    setExpandedBlocks(prev => {
      const newSet = new Set(prev);
      if (newSet.has(blockId)) {
        newSet.delete(blockId);
      } else {
        newSet.add(blockId);
      }
      return newSet;
    });
  };

  // Custom renderers for markdown
  const renderers = {
    code({ node, inline, className, children, ...props }) {
      const match = /language-(\w+)/.exec(className || '');
      const language = match ? match[1] : '';
      const codeString = String(children).replace(/\n$/, '');
      const blockId = `${message.id}-${Math.random().toString(36).substr(2, 9)}`;

      if (!inline && language) {
        const isExpanded = expandedBlocks.has(blockId);
        const shouldTruncate = codeString.split('\n').length > 20;
        const displayCode = shouldTruncate && !isExpanded
          ? codeString.split('\n').slice(0, 20).join('\n') + '\n// ...'
          : codeString;

        return (
          <div className="relative group my-4">
            {/* Code block header */}
            <div className="flex items-center justify-between bg-gray-800 text-gray-300 px-4 py-2 rounded-t-lg">
              <div className="flex items-center space-x-2">
                <Code className="w-4 h-4" />
                <span className="text-sm font-mono">{language}</span>
              </div>
              <div className="flex items-center space-x-2">
                {onCodeApply && (
                  <button
                    onClick={() => onCodeApply(codeString, language)}
                    className="p-1 hover:bg-gray-700 rounded transition-colors"
                    title="Apply to editor"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </button>
                )}
                <button
                  onClick={() => handleCopyCode(blockId, codeString)}
                  className="p-1 hover:bg-gray-700 rounded transition-colors"
                  title="Copy code"
                >
                  {copiedBlocks.has(blockId) ? (
                    <Check className="w-4 h-4 text-green-400" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </button>
                {shouldTruncate && (
                  <button
                    onClick={() => toggleBlockExpansion(blockId)}
                    className="p-1 hover:bg-gray-700 rounded transition-colors"
                    title={isExpanded ? "Collapse" : "Expand"}
                  >
                    {isExpanded ? (
                      <ChevronUp className="w-4 h-4" />
                    ) : (
                      <ChevronDown className="w-4 h-4" />
                    )}
                  </button>
                )}
              </div>
            </div>

            {/* Code content */}
            <SyntaxHighlighter
              language={language}
              style={vscDarkPlus}
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

      return <code className="bg-gray-100 px-1 py-0.5 rounded text-sm" {...props}>{children}</code>;
    }
  };

  return (
    <div className="space-y-4">
      {/* Context indicator */}
      {message.metadata?.contextSummary && (
        <div className="flex items-center space-x-2 text-sm text-gray-600 bg-blue-50 px-3 py-2 rounded-lg">
          <FileText className="w-4 h-4" />
          <span>
            Using {message.metadata.contextSummary.documentsFound} documents and{' '}
            {message.metadata.contextSummary.codeSnippetsFound} code snippets
          </span>
          <span className="text-xs text-gray-500">
            ({Math.round(message.metadata.contextSummary.confidence * 100)}% confidence)
          </span>
        </div>
      )}

      {/* Main content with citations */}
      {message.metadata?.citations && message.metadata.citations.length > 0 ? (
        <CitationRenderer
          text={processedContent}
          citations={message.metadata.citations}
          inline={true}
          onCitationClick={onCitationClick}
        />
      ) : (
        <div className="prose prose-sm max-w-none">
          <ReactMarkdown components={renderers}>
            {processedContent}
          </ReactMarkdown>
        </div>
      )}

      {/* Metadata section */}
      {showMetadata && message.metadata && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <button
            onClick={() => setShowFullMetadata(!showFullMetadata)}
            className="flex items-center space-x-2 text-sm text-gray-600 hover:text-gray-800"
          >
            <span>Metadata</span>
            {showFullMetadata ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>

          {showFullMetadata && (
            <div className="mt-2 space-y-2 text-xs text-gray-600">
              {message.metadata.model && (
                <div>Model: {message.metadata.model}</div>
              )}
              {message.metadata.timestamp && (
                <div>Time: {new Date(message.metadata.timestamp).toLocaleString()}</div>
              )}
              {message.metadata.tokens && (
                <div>
                  Tokens: {message.metadata.tokens.prompt} prompt, {message.metadata.tokens.completion} completion
                </div>
              )}
              {message.metadata.citations && (
                <div>Citations: {message.metadata.citations.length}</div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Helper function to extract code blocks
function extractCodeBlocks(content) {
  const codeBlocks = [];
  let blockIndex = 0;

  // This is a simplified extraction - in production, use a proper parser
  const processedContent = content.replace(
    /```(\w+)?\n([\s\S]*?)```/g,
    (match, language, code) => {
      const block = {
        id: `block-${blockIndex++}`,
        language: language || 'plaintext',
        code: code.trim()
      };
      codeBlocks.push(block);
      return match; // Keep original for markdown rendering
    }
  );

  return { processedContent, codeBlocks };
}
