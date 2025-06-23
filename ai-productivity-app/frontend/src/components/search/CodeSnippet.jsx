// Code snippet display with syntax highlighting and line numbers
import React, { memo } from 'react';
import PropTypes from 'prop-types';

// Use a simple dark theme object instead of importing
const codeTheme = {
  'code[class*="language-"]': {
    color: '#f8f8f2',
    background: 'none',
    fontFamily: 'Consolas, Monaco, "Andale Mono", "Ubuntu Mono", monospace',
    fontSize: '0.875rem',
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
    fontSize: '0.875rem',
    textAlign: 'left',
    whiteSpace: 'pre',
    wordSpacing: 'normal',
    wordBreak: 'normal',
    wordWrap: 'normal',
    lineHeight: '1.5',
    tabSize: '4',
    hyphens: 'none',
    padding: '1em',
    margin: '0',
    overflow: 'auto',
    borderRadius: '0.375rem',
  },
};

import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter/dist/cjs/prism';
import { oneDark } from 'react-syntax-highlighter/dist/cjs/styles/prism';

const CodeSnippet = memo(({ content, language, startLine, highlightLines = [] }) => {
  // Limit preview to first 15 lines
  const lines = content.split('\n');
  const previewLines = lines.slice(0, 15);
  const hasMore = lines.length > 15;
  const previewContent = previewLines.join('\n');

  return (
    <div className="code-snippet-container">
      <div className="relative rounded-md overflow-hidden">
        <div className="absolute top-2 right-2 z-10">
          <span className="text-xs bg-gray-700 text-gray-300 px-2 py-1 rounded">
            {language}
          </span>
        </div>

        <SyntaxHighlighter
          language={language}
          style={oneDark}
          showLineNumbers
          startingLineNumber={startLine || 1}
          wrapLines
          lineProps={lineNumber => {
            const isHighlighted = highlightLines.includes(lineNumber);
            return {
              style: {
                backgroundColor: isHighlighted ? '#364152' : 'transparent',
                display: 'block',
                width: '100%'
              }
            };
          }}
          customStyle={{
            margin: 0,
            padding: '1rem',
            fontSize: '0.875rem',
            lineHeight: '1.5'
          }}
        >
          {previewContent}
        </SyntaxHighlighter>

        {hasMore && (
          <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-gray-900 to-transparent h-8 flex items-end justify-center pb-1">
            <span className="text-xs text-gray-400">
              {lines.length - 15} more lines...
            </span>
          </div>
        )}
      </div>
    </div>
  );
});

CodeSnippet.propTypes = {
  content: PropTypes.string.isRequired,
  language: PropTypes.string.isRequired,
  startLine: PropTypes.number,
  highlightLines: PropTypes.arrayOf(PropTypes.number),
};

CodeSnippet.displayName = 'CodeSnippet';

export default CodeSnippet;
