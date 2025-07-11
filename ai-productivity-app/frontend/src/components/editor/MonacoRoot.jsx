/* eslint-env browser */
import React, {
  Suspense,
  lazy,
  useEffect,
  useRef,
  forwardRef,
  useImperativeHandle,
} from "react";
import PropTypes from "prop-types";
import LoadingSpinner from "../common/LoadingSpinner";
import { useTheme } from "../../hooks/useTheme";
import EditorErrorBoundary from "./EditorErrorBoundary";
import MobileCodeToolbar from "./MobileCodeToolbar";

// Lazy load Monaco Editor to optimize bundle size
const MonacoEditor = lazy(() => import("@monaco-editor/react"));

/**
 * Monaco Editor wrapper with lazy loading and error boundary
 * This component handles loading states and provides a consistent interface
 */
const MonacoRoot = forwardRef(
  (
    {
      value = "",
      defaultValue = "",
      language = "javascript",
      theme: customTheme,
      height = "400px",
      width = "100%",
      options = {},
      onMount,
      onChange,
      onValidate,
      loading: loadingComponent,
      className = "",
      filename = null,
      enableCopilot = true,
      maxFileSize = 1024 * 1024, // 1MB default limit
      enableVirtualization = true,
      showMobileToolbar = true,
      onLanguageChange,
      ...props
    },
    ref,
  ) => {
    const { theme: appTheme } = useTheme();
    const editorRef = useRef(null);

    // File size and virtualization checks
    const fileSize = value ? new Blob([value]).size : 0;
    const isLargeFile = fileSize > maxFileSize;
    const shouldVirtualize = enableVirtualization && isLargeFile;

    // Mobile detection
    const isMobile = typeof window !== "undefined" && window.innerWidth < 768;

    // Expose imperative API to parent components
    useImperativeHandle(
      ref,
      () => ({
        layout: () => {
          if (editorRef.current) {
            // Force update editor layout
            editorRef.current.layout();
            // Also update view zones if needed
            editorRef.current.changeViewZones(() => {});
          }
        },
        getFileSize: () => fileSize,
        isVirtualized: () => shouldVirtualize,
      }),
      [fileSize, shouldVirtualize],
    );

    // Use app theme if no custom theme is provided
    const effectiveTheme =
      customTheme || (appTheme === "dark" ? "vs-dark" : "vs-light");

    const resizeObserverRef = useRef(null);
    // Setup ResizeObserver for container size changes
    useEffect(() => {
      if (!editorRef.current) return;

      const container = editorRef.current.getContainerDomNode();
      if (!container) return;

      resizeObserverRef.current = new ResizeObserver((entries) => {
        // Only trigger layout if size actually changed
        for (const entry of entries) {
          const { width, height } = entry.contentRect;
          if (width > 0 && height > 0) {
            editorRef.current?.layout();
          }
        }
      });

      resizeObserverRef.current.observe(container);

      return () => {
        resizeObserverRef.current?.disconnect();
      };
    }, []);

    // Handle editor mount with proper disposal
    const handleEditorMount = (editor, monaco) => {
      editorRef.current = editor;

      // Ensure editor has correct dimensions on mount
      requestAnimationFrame(() => {
        editor.layout();
        // Double-check after a short delay for slow-rendering containers
        setTimeout(() => {
          editor.layout();
        }, 100);
      });

      // Disable TypeScript worker for large files to prevent excessive memory usage
      if (
        shouldVirtualize &&
        (language === "typescript" || language === "javascript")
      ) {
        monaco.languages.typescript.typescriptDefaults.setDiagnosticsOptions({
          noSemanticValidation: true,
          noSyntaxValidation: true,
          noSuggestionDiagnostics: true,
        });
        monaco.languages.typescript.javascriptDefaults.setDiagnosticsOptions({
          noSemanticValidation: true,
          noSyntaxValidation: true,
          noSuggestionDiagnostics: true,
        });
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

    // Force layout on visibility changes
    useEffect(() => {
      const handleVisibilityChange = () => {
        if (!document.hidden && editorRef.current) {
          editorRef.current.layout();
        }
      };
      document.addEventListener("visibilitychange", handleVisibilityChange);
      return () =>
        document.removeEventListener(
          "visibilitychange",
          handleVisibilityChange,
        );
    }, []);

    const defaultOptions = {
      automaticLayout: true,
      minimap: { enabled: false },
      fontFamily: 'Fira Code, Monaco, Menlo, "Ubuntu Mono", monospace',
      fontLigatures: true,
      fontSize: 14,
      lineNumbers: "on",
      renderLineHighlight: "all",
      scrollBeyondLastLine: false,
      wordWrap: "on",
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
      // Enhanced accessibility options
      accessibilitySupport: "auto",
      ariaLabel: filename ? `Code editor for ${filename}` : "Code editor",
      screenReaderAnnounceInlineSuggestion: true,
      accessibilityPageSize: 10,
      cursorSurroundingLines: 3,
      cursorSurroundingLinesStyle: "all",
      screenReaderMultiline: true,
      // Performance optimizations for large files
      ...(shouldVirtualize && {
        renderValidationDecorations: "off",
        renderWhitespace: "none",
        codeLens: false,
        folding: false,
        links: false,
        colorDecorators: false,
        matchBrackets: "never",
        occurrencesHighlight: false,
        selectionHighlight: false,
      }),
      // Mobile optimizations
      ...(isMobile && {
        fontSize: 16, // Prevent iOS zoom
        lineHeight: 1.5,
        scrollBeyondLastLine: false,
        quickSuggestions: {
          other: false,
          comments: false,
          strings: false,
        },
        parameterHints: { enabled: false },
        suggestOnTriggerCharacters: false,
        acceptSuggestionOnEnter: "off",
        tabCompletion: "off",
        wordBasedSuggestions: false,
        // Simplified scrolling for touch
        scrollbar: {
          vertical: "auto",
          horizontal: "auto",
          verticalScrollbarSize: 18,
          horizontalScrollbarSize: 18,
        },
      }),
      ...options,
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
        {/* Screen reader context announcement */}
        <div
          className="sr-only"
          aria-live="polite"
          id={`monaco-context-${filename || "editor"}`}
        >
          {filename ? `Editing ${filename}` : "Code editor"} in {language}{" "}
          language.
          {value ? `${value.split("\n").length} lines of code.` : "Empty file."}
          {shouldVirtualize && " Large file - performance mode enabled."}
        </div>

        {/* Large file warning */}
        {shouldVirtualize && (
          <div className="mb-2 px-3 py-2 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-md">
            <div className="flex items-center text-sm text-amber-800 dark:text-amber-200">
              <svg
                className="w-4 h-4 mr-2"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                  clipRule="evenodd"
                />
              </svg>
              Large file detected ({Math.round(fileSize / 1024)}KB). Some
              features disabled for performance.
            </div>
          </div>
        )}

        {/* Mobile toolbar */}
        {isMobile && showMobileToolbar && (
          <MobileCodeToolbar
            editorRef={editorRef}
            language={language}
            onLanguageChange={onLanguageChange}
          />
        )}

        <EditorErrorBoundary
          value={value}
          onFallback={(content) => {
            // Fallback to textarea if provided via props
            if (props.onEditorError) {
              props.onEditorError(content);
            }
          }}
        >
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
        </EditorErrorBoundary>
      </div>
    );
  },
);

MonacoRoot.displayName = "MonacoRoot";

MonacoRoot.propTypes = {
  value: PropTypes.string,
  defaultValue: PropTypes.string,
  language: PropTypes.string,
  theme: PropTypes.string,
  height: PropTypes.string,
  width: PropTypes.string,
  options: PropTypes.object,
  onMount: PropTypes.func,
  onChange: PropTypes.func,
  onValidate: PropTypes.func,
  loading: PropTypes.node,
  className: PropTypes.string,
  filename: PropTypes.string,
  enableCopilot: PropTypes.bool,
  maxFileSize: PropTypes.number,
  enableVirtualization: PropTypes.bool,
  showMobileToolbar: PropTypes.bool,
  onLanguageChange: PropTypes.func,
  onEditorError: PropTypes.func,
};

export default MonacoRoot;
