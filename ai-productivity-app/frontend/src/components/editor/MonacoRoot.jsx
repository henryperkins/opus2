import React, { Suspense, lazy, useEffect, useRef, forwardRef, useImperativeHandle } from 'react';
import LoadingSpinner from '../common/LoadingSpinner';
import { useTheme } from '../../hooks/useTheme';
import useCodeEditor from '../../hooks/useCodeEditor';

// Lazy load Monaco Editor to optimize bundle size
const MonacoEditor = lazy(() => import('@monaco-editor/react'));

/**
 * Monaco Editor wrapper with lazy loading and error boundary
 * This component handles loading states and provides a consistent interface
 */
const MonacoRoot = forwardRef(({
  value = '',
  defaultValue = '',
  language = 'javascript',
  theme: customTheme,
  height = '400px',
  width = '100%',
  options = {},
  onMount,
  onChange,
  onValidate,
  loading: loadingComponent,
  className = '',
  filename = null,
  enableCopilot = true,
  ...props 
}, ref) => {
  const { theme: appTheme } = useTheme();
  const editorRef = useRef(null);

  // Expose imperative API to parent components
  useImperativeHandle(ref, () => ({
    layout: () => editorRef.current?.layout(),
  }));
  
  // Use app theme if no custom theme is provided
  const effectiveTheme = customTheme || (appTheme === 'dark' ? 'vs-dark' : 'vs-light');
  
  // Initialize code editor with Monacopilot
  const { editorRef: codeEditorRef, copilotEnabled, triggerCompletion } = useCodeEditor({
    language,
    enableCopilot,
    filename,
    maxContextLines: 80
  });
  // Handle editor mount with proper disposal
  const handleEditorMount = (editor, monaco) => {
    editorRef.current = editor;
    
    // Call both the useCodeEditor mount handler and custom onMount
    if (codeEditorRef.onMount) {
      codeEditorRef.onMount(editor, monaco);
    }
    if (onMount) {
      onMount(editor, monaco);
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (editorRef.current) {
        editorRef.current.dispose();
      }
    };
  }, []);

  const defaultOptions = {
    automaticLayout: true,
    minimap: { enabled: false },
    fontFamily: 'Fira Code, Monaco, Menlo, "Ubuntu Mono", monospace',
    fontLigatures: true,
    fontSize: 14,
    lineNumbers: 'on',
    renderLineHighlight: 'all',
    scrollBeyondLastLine: false,
    wordWrap: 'on',
    inlineSuggest: { enabled: true },
    suggest: {
      preview: true,
      showKeywords: true,
      showSnippets: true,
    },
    bracketPairColorization: { enabled: true },
    guides: {
      bracketPairs: true,
      indentation: true,
    },
    ...options
  };

  const LoadingComponent = loadingComponent || (
    <div className="flex items-center justify-center h-full min-h-[200px]">
      <div className="text-center">
        <LoadingSpinner size="lg" />
        <p className="mt-2 text-sm text-gray-500">Loading editor...</p>
      </div>
    </div>
  );

  return (
    <div className={`monaco-root ${className}`}>
      <Suspense fallback={LoadingComponent}>
        <MonacoEditor
          value={value}
          defaultValue={defaultValue}
          language={language}
          theme={effectiveTheme}
          height={height}
          width={width}
          options={defaultOptions}
          onMount={handleEditorMount}
          onChange={onChange}
          onValidate={onValidate}
          loading={LoadingComponent}
          {...props}
        />
      </Suspense>
    </div>
  );
};

export default MonacoRoot;