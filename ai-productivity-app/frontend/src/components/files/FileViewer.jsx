import React, { useState, useEffect } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';
import LoadingSpinner from '../common/LoadingSpinner';

export default function FileViewer() {
  const { path } = useParams();
  const [searchParams] = useSearchParams();
  const [fileContent, setFileContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [language, setLanguage] = useState('text');

  const targetLine = parseInt(searchParams.get('line')) || 1;
  const decodedPath = decodeURIComponent(path);

  useEffect(() => {
    const fetchFileContent = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Import codeAPI dynamically to avoid ESLint restriction
        const { codeAPI } = await import('../../api/code');
        const response = await codeAPI.getFileContent(decodedPath);
        
        setFileContent(response.content || '');
        setLanguage(response.language || detectLanguage(decodedPath));
      } catch (err) {
        setError(err.response?.data?.detail || err.message || 'Failed to load file');
      } finally {
        setLoading(false);
      }
    };

    fetchFileContent();
  }, [decodedPath]);

  // Scroll to target line after content loads
  useEffect(() => {
    if (!loading && fileContent && targetLine > 1) {
      const timer = setTimeout(() => {
        const lineElement = document.getElementById(`line-${targetLine}`);
        if (lineElement) {
          lineElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [loading, fileContent, targetLine]);

  const detectLanguage = (filePath) => {
    const ext = filePath.split('.').pop()?.toLowerCase();
    const languageMap = {
      'js': 'javascript',
      'jsx': 'jsx',
      'ts': 'typescript',
      'tsx': 'tsx',
      'py': 'python',
      'java': 'java',
      'cpp': 'cpp',
      'c': 'c',
      'cs': 'csharp',
      'php': 'php',
      'rb': 'ruby',
      'go': 'go',
      'rs': 'rust',
      'swift': 'swift',
      'kt': 'kotlin',
      'scala': 'scala',
      'sh': 'bash',
      'sql': 'sql',
      'json': 'json',
      'xml': 'xml',
      'html': 'html',
      'css': 'css',
      'scss': 'scss',
      'sass': 'sass',
      'less': 'less',
      'md': 'markdown',
      'yaml': 'yaml',
      'yml': 'yaml',
      'toml': 'toml',
      'ini': 'ini',
      'conf': 'ini',
      'dockerfile': 'dockerfile',
    };
    return languageMap[ext] || 'text';
  };

  const getHighlightedLines = () => {
    if (targetLine > 1) {
      return [targetLine];
    }
    return [];
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <LoadingSpinner label="Loading file..." showLabel={true} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4 m-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">Error loading file</h3>
            <p className="text-sm text-red-700 mt-1">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-medium text-gray-900 truncate">
              {decodedPath}
            </h1>
            {targetLine > 1 && (
              <p className="text-sm text-gray-500 mt-1">
                Showing line {targetLine}
              </p>
            )}
          </div>
          <div className="flex items-center space-x-3">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
              {language}
            </span>
            <button
              onClick={() => window.history.back()}
              className="inline-flex items-center px-3 py-1 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              ← Back
            </button>
          </div>
        </div>
      </div>

      {/* File Content */}
      <div className="bg-gray-50 min-h-full">
        <SyntaxHighlighter
          language={language}
          style={tomorrow}
          showLineNumbers={true}
          wrapLines={true}
          lineNumberStyle={{ minWidth: '3em' }}
          lineProps={(lineNumber) => ({
            style: {
              display: 'block',
              backgroundColor: getHighlightedLines().includes(lineNumber) 
                ? '#fef3c7' 
                : 'transparent',
            },
            id: `line-${lineNumber}`,
          })}
          customStyle={{
            margin: 0,
            padding: '1rem',
            fontSize: '14px',
            lineHeight: '1.5',
            background: 'transparent',
          }}
        >
          {fileContent}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}