/*
 * useCodeEditor – React hook wrapping a Monaco editor instance
 * -----------------------------------------------------------
 * The hook centralises the boilerplate required to work with
 * `@monaco-editor/react` inside functional components.
 *
 * Key features
 * ------------
 * 1. Exposes a *ref* (editorRef) that must be passed to the `onMount` prop of
 *    the MonacoEditor component.  The ref holds the *IStandaloneCodeEditor*
 *    instance provided by Monaco.
 * 2. Provides convenient `getValue()` and `setValue(code: string)` helpers
 *    that delegate to the underlying editor.  When the editor has not yet
 *    mounted they transparently fallback to the last known value.
 * 3. Maintains an internal `code` state that is kept in-sync with the editor
 *    by listening to its `onDidChangeModelContent` event.  You can also update
 *    the code by calling `setCode` – this will update both the state *and*
 *    the Monaco model.
 * 4. Offers a lightweight `getDiff(original?: string)` helper that returns a
 *    list of changed lines in unified diff format (uses Monaco's own diff
 *    algorithm when available, otherwise falls back to a simple JS diff).
 *
 * Usage example
 * -------------
 *   const {
 *     editorRef,
 *     code,
 *     setCode,
 *     getValue,
 *     getDiff,
 *   } = useCodeEditor({ initialCode: '', language: 'python' });
 *
 *   <MonacoEditor
 *     defaultLanguage="python"
 *     onMount={editorRef.onMount}
 *     value={code}
 *   />
 */

import { useCallback, useEffect, useRef, useState } from "react";
import * as monaco from "monaco-editor";
import { registerCompletion } from "monacopilot";

export function useCodeEditor({
  initialCode = "",
  language = "plaintext",
  enableCopilot = true,
  copilotEndpoint = "/api/v1/code/copilot",
  maxContextLines = 60,
  filename = null,
  relatedFiles = [],
  technologies = [],
} = {}) {
  const editorInstanceRef = useRef(null);
  const copilotRef = useRef(null);
  const [code, setCodeState] = useState(initialCode);
  const [copilotEnabled, setCopilotEnabled] = useState(enableCopilot);

  // Keep code state in sync with external edits (e.g. setCode())
  const setCode = useCallback((newCode) => {
    setCodeState(newCode);
    if (
      editorInstanceRef.current &&
      newCode !== editorInstanceRef.current.getValue()
    ) {
      editorInstanceRef.current.setValue(newCode);
    }
  }, []);

  // Editor onMount callback – passed to MonacoEditor
  const handleEditorMount = useCallback(
    (editor) => {
      editorInstanceRef.current = editor;

      // Sync initial language
      const currentModel = editor.getModel();
      if (currentModel) {
        monaco.editor.setModelLanguage(currentModel, language);
      }

      // Keep internal state up-to-date with user edits
      const disposable = editor.onDidChangeModelContent(() => {
        const value = editor.getValue();
        setCodeState(value);
      });

      // Initialize Monacopilot if enabled
      if (copilotEnabled) {
        try {
          copilotRef.current = registerCompletion(monaco, editor, {
            endpoint: copilotEndpoint,
            language,
            trigger: "onIdle",
            maxContextLines,
            filename,
            relatedFiles,
            technologies,
            onError: (error) => {
              console.warn("Monacopilot error:", error);
            },
          });
        } catch (error) {
          console.error("Failed to initialize Monacopilot:", error);
        }
      }

      // Cleanup listeners and copilot on unmount
      return () => {
        disposable.dispose();
        if (copilotRef.current) {
          copilotRef.current.deregister();
          copilotRef.current = null;
        }
      };
    },
    [
      language,
      copilotEnabled,
      copilotEndpoint,
      maxContextLines,
      filename,
      relatedFiles,
      technologies,
    ],
  );

  // Cleanup effect to prevent memory leaks
  useEffect(() => {
    return () => {
      if (editorInstanceRef.current) {
        const model = editorInstanceRef.current.getModel();
        if (model) {
          model.dispose();
        }
      }
    };
  }, []);

  // ---------------------------------------------------------------------------
  // Helper functions
  // ---------------------------------------------------------------------------

  const getValue = useCallback(() => {
    if (editorInstanceRef.current) {
      return editorInstanceRef.current.getValue();
    }
    return code;
  }, [code]);

  const setValue = useCallback(
    (val) => {
      setCode(val);
    },
    [setCode],
  );

  const getDiff = useCallback(
    (original = initialCode) => {
      // Prefer Monaco's diffing when a model exists – it's more accurate and
      // preserves syntax tokens.
      if (editorInstanceRef.current) {
        const currentModel = editorInstanceRef.current.getModel();
        const originalModel = monaco.editor.createModel(original, language);
        const diff = monaco.editor.computeLinesDiff(
          originalModel,
          currentModel,
        );
        originalModel.dispose();

        return diff.changes;
      }

      // Fallback: naive line-by-line diff
      const diff = [];
      const a = original.split("\n");
      const b = code.split("\n");
      const len = Math.max(a.length, b.length);
      for (let i = 0; i < len; i += 1) {
        if (a[i] !== b[i]) {
          diff.push({
            lineNumber: i + 1,
            original: a[i] || "",
            modified: b[i] || "",
          });
        }
      }
      return diff;
    },
    [code, initialCode, language],
  );

  // Update model language when `language` param changes
  useEffect(() => {
    if (editorInstanceRef.current) {
      const model = editorInstanceRef.current.getModel();
      if (model) {
        monaco.editor.setModelLanguage(model, language);
      }
    }
  }, [language]);

  // Toggle Copilot on/off
  const toggleCopilot = useCallback(() => {
    setCopilotEnabled((prev) => !prev);
  }, []);

  // Trigger completion manually
  const triggerCompletion = useCallback(() => {
    if (copilotRef.current && copilotRef.current.trigger) {
      copilotRef.current.trigger();
    }
  }, []);

  return {
    // Pass this directly: <MonacoEditor onMount={editorRef.onMount} />
    editorRef: { onMount: handleEditorMount },

    code,
    setCode,
    getValue,
    setValue,
    getDiff,

    language,
    setLanguage: (lang) => {
      if (editorInstanceRef.current) {
        const model = editorInstanceRef.current.getModel();
        monaco.editor.setModelLanguage(model, lang);
      }
    },

    // Copilot controls
    copilotEnabled,
    toggleCopilot,
    triggerCompletion,

    // Access to editor instance for advanced usage
    editorInstance: editorInstanceRef.current,
  };
}

export default useCodeEditor;
