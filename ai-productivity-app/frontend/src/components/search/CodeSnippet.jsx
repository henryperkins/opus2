// Code snippet display with syntax highlighting and line numbers
import React, { memo } from 'react';
import { Light as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomOneDark } from 'react-syntax-highlighter/dist/esm/styles/hljs';
import python from 'react-syntax-highlighter/dist/esm/languages/hljs/python';
import javascript from 'react-syntax-highlighter/dist/esm/languages/hljs/javascript';
import typescript from 'react-syntax-highlighter/dist/esm/languages/hljs/typescript';

// Register languages
SyntaxHighlighter.registerLanguage('python', python);
SyntaxHighlighter.registerLanguage('javascript', javascript);
SyntaxHighlighter.registerLanguage('typescript', typescript);

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
          style={atomOneDark}
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

CodeSnippet.displayName = 'CodeSnippet';

export default CodeSnippet;
