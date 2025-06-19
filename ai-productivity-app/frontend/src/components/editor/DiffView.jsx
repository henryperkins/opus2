import React, { useState } from 'react';
import MonacoEditor from '@monaco-editor/react';

const DiffView = ({ 
  original, 
  modified, 
  language = 'javascript',
  theme = 'vs-dark',
  height = '400px',
  className = '',
  onApplyChanges,
  onRejectChanges
}) => {
  const [isFullscreen, setIsFullscreen] = useState(false);

  const handleApply = () => {
    if (onApplyChanges) {
      onApplyChanges(modified);
    }
  };

  const handleReject = () => {
    if (onRejectChanges) {
      onRejectChanges();
    }
  };

  return (
    <div className={`diff-view ${className} ${isFullscreen ? 'fixed inset-0 z-50 bg-white' : ''}`}>
      <div className="flex items-center justify-between p-3 bg-gray-100 border-b">
        <div className="flex items-center space-x-4">
          <h3 className="text-sm font-medium text-gray-900">Code Diff</h3>
          <div className="flex items-center space-x-2 text-xs text-gray-600">
            <div className="flex items-center space-x-1">
              <div className="w-3 h-3 bg-red-200 border border-red-400 rounded"></div>
              <span>Removed</span>
            </div>
            <div className="flex items-center space-x-1">
              <div className="w-3 h-3 bg-green-200 border border-green-400 rounded"></div>
              <span>Added</span>
            </div>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-1 text-gray-600 hover:text-gray-900 rounded"
            title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {isFullscreen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
              )}
            </svg>
          </button>
        </div>
      </div>

      <div style={{ height: isFullscreen ? 'calc(100vh - 120px)' : height }}>
        <MonacoEditor
          original={original}
          modified={modified}
          language={language}
          theme={theme}
          options={{
            renderSideBySide: true,
            enableSplitViewResizing: true,
            renderIndicators: true,
            readOnly: false,
            fontSize: 14,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            wordWrap: 'on'
          }}
        />
      </div>

      {(onApplyChanges || onRejectChanges) && (
        <div className="flex items-center justify-end space-x-2 p-3 bg-gray-50 border-t">
          {onRejectChanges && (
            <button
              onClick={handleReject}
              className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-100"
            >
              Reject Changes
            </button>
          )}
          {onApplyChanges && (
            <button
              onClick={handleApply}
              className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700"
            >
              Apply Changes
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default DiffView;