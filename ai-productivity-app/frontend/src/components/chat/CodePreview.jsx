import React from 'react';
import { Light as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomOneDark } from 'react-syntax-highlighter/dist/cjs/styles/hljs/atom-one-dark';

export default function CodePreview({ snippets, onApply }) {
  if (!snippets || snippets.length === 0) return null;

  return (
    <div className="border-t border-gray-200 bg-gray-50 p-4">
      <h3 className="text-sm font-medium text-gray-900 mb-3">
        Code Suggestions
      </h3>

      <div className="space-y-3 max-h-64 overflow-y-auto">
        {snippets.map((snippet, index) => (
          <div key={index} className="bg-white rounded border border-gray-200">
            <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200">
              <span className="text-xs font-medium text-gray-600">
                {snippet.language}
              </span>
              {onApply && (
                <button
                  onClick={() => onApply(snippet.code)}
                  className="text-xs bg-blue-500 text-white px-2 py-1 rounded hover:bg-blue-600"
                >
                  Apply to Editor
                </button>
              )}
            </div>

            <div className="p-2">
              <SyntaxHighlighter
                language={snippet.language}
                style={atomOneDark}
                customStyle={{
                  margin: 0,
                  padding: '0.5rem',
                  fontSize: '0.75rem',
                  maxHeight: '150px',
                  overflow: 'auto'
                }}
              >
                {snippet.code}
              </SyntaxHighlighter>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
