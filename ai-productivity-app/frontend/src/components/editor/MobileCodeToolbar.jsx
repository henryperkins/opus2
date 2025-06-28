import React from 'react';
import { 
  ChevronLeft, 
  ChevronRight, 
  RotateCcw, 
  Copy, 
  Type,
  Indent,
  Outdent,
  Search
} from 'lucide-react';

/**
 * Mobile-optimized toolbar for code editing
 * Provides common actions for touch interfaces
 */
const MobileCodeToolbar = ({ 
  editorRef, 
  language, 
  onLanguageChange,
  onFormat,
  className = "" 
}) => {
  const insertText = (text) => {
    if (!editorRef.current) return;
    
    const editor = editorRef.current;
    const selection = editor.getSelection();
    const range = new monaco.Range(
      selection.startLineNumber,
      selection.startColumn,
      selection.endLineNumber,
      selection.endColumn
    );
    
    editor.executeEdits('mobile-toolbar', [{
      range: range,
      text: text,
      forceMoveMarkers: true
    }]);
    
    editor.focus();
  };

  const indentSelection = () => {
    if (!editorRef.current) return;
    editorRef.current.trigger('mobile-toolbar', 'editor.action.indentLines', null);
    editorRef.current.focus();
  };

  const outdentSelection = () => {
    if (!editorRef.current) return;
    editorRef.current.trigger('mobile-toolbar', 'editor.action.outdentLines', null);
    editorRef.current.focus();
  };

  const undo = () => {
    if (!editorRef.current) return;
    editorRef.current.trigger('mobile-toolbar', 'undo', null);
    editorRef.current.focus();
  };

  const copyContent = async () => {
    if (!editorRef.current) return;
    
    const selection = editorRef.current.getSelection();
    const model = editorRef.current.getModel();
    const text = selection.isEmpty() 
      ? model.getValue() 
      : model.getValueInRange(selection);
    
    try {
      await navigator.clipboard.writeText(text);
    } catch (err) {
      console.warn('Copy failed:', err);
    }
  };

  const showQuickActions = () => {
    if (!editorRef.current) return;
    editorRef.current.trigger('mobile-toolbar', 'editor.action.quickCommand', null);
  };

  const showFind = () => {
    if (!editorRef.current) return;
    editorRef.current.trigger('mobile-toolbar', 'actions.find', null);
  };

  return (
    <div className={`flex items-center gap-1 p-2 bg-gray-100 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 overflow-x-auto ${className}`}>
      {/* Common symbols for coding */}
      <div className="flex items-center gap-1 pr-2 border-r border-gray-300 dark:border-gray-600">
        <button
          onClick={() => insertText('{')}
          className="p-2 text-sm font-mono bg-white dark:bg-gray-700 rounded border touch-manipulation"
        >
          {'{'}
        </button>
        <button
          onClick={() => insertText('}')}
          className="p-2 text-sm font-mono bg-white dark:bg-gray-700 rounded border touch-manipulation"
        >
          {'}'}
        </button>
        <button
          onClick={() => insertText('(')}
          className="p-2 text-sm font-mono bg-white dark:bg-gray-700 rounded border touch-manipulation"
        >
          {'('}
        </button>
        <button
          onClick={() => insertText(')')}
          className="p-2 text-sm font-mono bg-white dark:bg-gray-700 rounded border touch-manipulation"
        >
          {')'}
        </button>
        <button
          onClick={() => insertText('=')}
          className="p-2 text-sm font-mono bg-white dark:bg-gray-700 rounded border touch-manipulation"
        >
          =
        </button>
        <button
          onClick={() => insertText(';')}
          className="p-2 text-sm font-mono bg-white dark:bg-gray-700 rounded border touch-manipulation"
        >
          ;
        </button>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1">
        <button
          onClick={indentSelection}
          className="p-2 bg-white dark:bg-gray-700 rounded border touch-manipulation"
          title="Indent"
        >
          <Indent className="w-4 h-4" />
        </button>
        <button
          onClick={outdentSelection}
          className="p-2 bg-white dark:bg-gray-700 rounded border touch-manipulation"
          title="Outdent"
        >
          <Outdent className="w-4 h-4" />
        </button>
        <button
          onClick={undo}
          className="p-2 bg-white dark:bg-gray-700 rounded border touch-manipulation"
          title="Undo"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
        <button
          onClick={copyContent}
          className="p-2 bg-white dark:bg-gray-700 rounded border touch-manipulation"
          title="Copy"
        >
          <Copy className="w-4 h-4" />
        </button>
        <button
          onClick={showFind}
          className="p-2 bg-white dark:bg-gray-700 rounded border touch-manipulation"
          title="Find"
        >
          <Search className="w-4 h-4" />
        </button>
        <button
          onClick={showQuickActions}
          className="p-2 bg-white dark:bg-gray-700 rounded border touch-manipulation"
          title="Commands"
        >
          <Type className="w-4 h-4" />
        </button>
      </div>

      {/* Language selector */}
      {onLanguageChange && (
        <div className="ml-auto">
          <select
            value={language}
            onChange={(e) => onLanguageChange(e.target.value)}
            className="p-2 text-sm bg-white dark:bg-gray-700 border rounded touch-manipulation"
          >
            <option value="javascript">JavaScript</option>
            <option value="python">Python</option>
            <option value="typescript">TypeScript</option>
            <option value="html">HTML</option>
            <option value="css">CSS</option>
            <option value="json">JSON</option>
            <option value="markdown">Markdown</option>
            <option value="sql">SQL</option>
            <option value="yaml">YAML</option>
            <option value="bash">Bash</option>
          </select>
        </div>
      )}
    </div>
  );
};

export default MobileCodeToolbar;