import React, { Suspense, lazy } from 'react';
import LoadingSpinner from '../common/LoadingSpinner';

// Lazy load Monaco Editor to optimize bundle size
const MonacoEditor = lazy(() => import('@monaco-editor/react'));

/**
 * Monaco Editor wrapper with lazy loading and error boundary
 * This component handles loading states and provides a consistent interface
 */
const MonacoRoot = ({ 
  value = '',
  defaultValue = '',
  language = 'javascript',
  theme = 'vs-dark',
  height = '400px',
  width = '100%',
  options = {},
  onMount,
  onChange,
  onValidate,
  loading: loadingComponent,
  className = '',
  ...props 
}) => {
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
          theme={theme}
          height={height}
          width={width}
          options={defaultOptions}
          onMount={onMount}
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