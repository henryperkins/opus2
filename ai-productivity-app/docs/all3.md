Below is the same content, re-rendered with consistent Markdown headings, fenced code-blocks, tidy lists and tables, while preserving every word, emoji (🔖) and internal anchor reference.

---

```markdown
# 🧭 Master guide – Monaco Editor + Monacopilot + react-resizable-panels

This document is **tailored to the `ai-productivity-app` code-base**.
It shows

* how each library slots into the existing hooks (`useCodeEditor`, `useCodeExecutor`, `SplitPane ⇒ react-resizable-panels`);
* what extra power-features you can tap; and
* a toolbox of performance, security and testing tips that work with **Vite**, **FastAPI** and the current folder structure.

Read the book end-to-end once, then dip back into the 🔖 bookmarks when you hit a specific need.

---

## 📑 Table of contents
1. Folder & naming conventions
2. Dependency matrix & install script
3. Vite bundling—workers · Buffer shim · tree-shaking
4. react-resizable-panels patterns
5. Monaco Editor: configuration catalogue
6. Monacopilot: registration recipes
7. Extending `useCodeEditor` safely
8. Wiring the Editor into **ProjectChatPage**
9. Streaming execution & diff workflow
10. Accessibility & keyboard UX
11. Performance tuning checklist
12. Security & quota management
13. Testing (unit + E2E)
14. Troubleshooting quick-ref

---

## 1 · Folder & naming conventions 🔖
```text
frontend/
└─ src/
   ├─ components/editor/
   │   ├─ MonacoRoot.jsx        # lazy-loaded wrapper
   │   ├─ LanguageSelector.jsx
   │   ├─ DiffView.jsx
   │   └─ index.js              # barrel export
   ├─ hooks/
   │   ├─ useCodeEditor.js      # Monaco + Monacopilot glue
   │   ├─ useCodeExecutor.js
   ├─ components/layout/
   │   └─ SplitPane.jsx         # proxy to react-resizable-panels
   └─ pages/ProjectChat/
       └─ ProjectChatPage.jsx   # two-pane cockpit
```
* All editor code lives under **`components/editor`** → predictable chunk-splits.
* `MonacoRoot.jsx` is the **only** place that imports `* as monaco`.

---

## 2 · Dependency matrix & install script 🔖
```bash
# Essential
npm i monaco-editor monacopilot react-resizable-panels

# Vite helpers
npm i -D vite-plugin-monaco-editor buffer @rollup/plugin-inject

# Optional dev tooling
npm i -D @types/monaco-editor eslint-plugin-monaco-editor
```
Keep **buffer** + **@rollup/plugin-inject**; Monacopilot calls `Buffer.from`.

---

## 3 · Vite bundling 🔖 (workers · Buffer shim · tree-shaking)
```ts
// vite.config.ts
import { defineConfig } from 'vite';
import react  from '@vitejs/plugin-react';
import monaco from 'vite-plugin-monaco-editor';
import inject from '@rollup/plugin-inject';

export default defineConfig({
  plugins: [
    react(),
    monaco({
      languageWorkers: ['typescript', 'json', 'html', 'python'],
      features       : ['coreCommands', 'find', 'inlineCompletions']
    }),
    inject({ Buffer: ['buffer', 'Buffer'] })
  ],
  build: { target: 'esnext' }   // native ESM workers
});
```
Add languages once → bundle shrinks dramatically.

---

## 4 · react-resizable-panels patterns 🔖
```jsx
import {
  Panel,
  PanelGroup,
  PanelResizeHandle
} from 'react-resizable-panels';

/* Pattern A – two panes (chat | editor) */
<PanelGroup direction="horizontal" autoSaveId="chat-editor">
  <Panel minSize={25}>{/* Chat */}</Panel>
  <PanelResizeHandle className="w-2 bg-gray-300 dark:bg-gray-700" />
  <Panel minSize={25}>{/* Editor / Canvas Tabs */}</Panel>
</PanelGroup>
```
### Power features you now own
* **`autoSaveId`** ⇒ layout persists via `localStorage`.
* `panelRef.collapse()/expand()` for hot-keys.
* `Panel.onResize(size%)` → telemetry.

---

## 5 · Monaco Editor configuration catalogue 🔖
```jsx
const editor = monaco.editor.create(ref.current, {
  language         : props.language,
  theme            : 'vs-dark',
  automaticLayout  : true,
  minimap          : { enabled: false },
  fontFamily       : 'Fira Code, monospace',
  fontLigatures    : true,
  inlineSuggest    : { enabled: true }  // ghost-text
});
```
| Feature         | Option / API                                    |
|-----------------|-------------------------------------------------|
| CodeLens        | `codeLens: true`                                |
| Format-on-save  | `editor.getAction('editor.action.formatDocument')` |
| Error squiggles | `monaco.editor.setModelMarkers(...)`            |
| Theme switch    | `monaco.editor.setTheme('vs-light')`            |
| Diff editor     | `monaco.editor.createDiffEditor(...)`           |

---

## 6 · Monacopilot registration recipes 🔖
```ts
import { registerCompletion } from 'monacopilot';

registerCompletion(monaco, editor, {
  endpoint       : '/api/code/copilot',
  language       : props.language,
  trigger        : 'onIdle',    // onTyping | onDemand
  maxContextLines: 60
});
```
| Need               | Option / Snippet                          |
|--------------------|-------------------------------------------|
| Low-latency Groq   | `trigger:'onTyping', debounce:80`         |
| Per-file prompt    | `filename:'App.tsx'`                      |
| Multi-file context | `relatedFiles:[{ path, content }, …]`     |
| Manual trigger     | `trigger:'onDemand'` + `.trigger()`       |
| Disable cache      | `enableCaching:false`                     |

---

## 7 · Extending `useCodeEditor` safely 🔖
```diff
+import { registerCompletion } from 'monacopilot';

const handleEditorMount = useCallback((editor) => {
  editorInstanceRef.current = editor;
+ const copilot = registerCompletion(monaco, editor, {
+   endpoint: '/api/code/copilot',
+   language,
+   trigger : 'onIdle'
+ });
  // …existing onDidChangeModelContent

  return () => {
    disposables.forEach(d => d.dispose());
+   copilot.deregister();
  };
}, [language]);
```
Add a toolbar toggle:
```jsx
<input
  type="checkbox"
  checked={copilotOn}
  onChange={e => copilot.setEnabled(e.target.checked)}
/>
```

---

## 8 · Wiring the Editor into **ProjectChatPage** 🔖
```jsx
<PanelGroup direction="horizontal" autoSaveId={`prj-${projectId}`}>
  <Panel minSize={25}><MessageList …/></Panel>
  <PanelResizeHandle className="w-2 bg-gray-300" />
  <Panel minSize={30}>
    <WorkTabs
      editorProps={{ editorRef, code, setCode, language, setLanguage }}
      diffProps  ={…}
      canvasProps={…}
    />
  </Panel>
</PanelGroup>
```

---

## 9 · Streaming execution & diff workflow 🔖
1. **Edit** code → Copilot suggests → user accepts.
2. Click **Run** → `useCodeExecutor` streams output.
3. Assistant returns diff → `DiffView` shows patch → **Apply** inserts.
4. No remaining changes ⇒ “Review” button hides.

---

## 10 · Accessibility & keyboard UX 🔖
| Action                    | Shortcut (Mac / Win) | Notes                  |
|---------------------------|----------------------|------------------------|
| Accept suggestion         | Tab                  | inline completions     |
| Dismiss suggestion        | Esc                  |                        |
| Trigger suggestions       | ⌃⌥Space / Ctrl⇧Space | via `editor.addCommand`|
| Collapse right panel      | Cmd/Ctrl + ⇧ + →     | `panelRef.collapse()`  |
| Focus Chat ↔ Editor       | F6                   | add ARIA roles         |

---

## 11 · Performance tuning checklist 🔖
* Lazy-load `MonacoRoot` (`React.lazy`).
* Limit workers/languages via Vite plugin.
* `trigger:'onIdle'` + debounce 120 ms.
* Add `skipInitialResize` for hidden panels.
* Wrap heavy widgets in `<Suspense>` + `<ErrorBoundary>`.

---

## 12 · Security & quota management 🔖
* Keys stay server-side (`/api/code/copilot`).
* Redis rate-limit: **30 req/min/user**.
* Run `secret_scanner` on `editorContent`.
* Log `{ language, cursorOffset, promptSize }` for cost tracking.

---

## 13 · Testing strategy 🔖
### Unit
```ts
jest.mock('monacopilot', () => ({ registerCompletion: jest.fn() }));
renderHook(useCodeEditor);
expect(registerCompletion).toHaveBeenCalled();
```
### E2E (Playwright)
1. Mock backend → type code → ghost-text.
2. Accept completion → **Run** → validate output.
3. Drag handle → assert persisted widths.

---

## 14 · Troubleshooting quick-ref 🔖
| Symptom             | Fix                                          |
|---------------------|----------------------------------------------|
| Worker 404s         | add vite-plugin-monaco-editor or fix worker  |
| `Buffer` undefined  | ensure `inject({ Buffer })` in rollup config |
| Copilot silent      | check `/api/code/copilot` 200 + shape OK     |
| Tab not accepting   | remove conflicting keybinding                |
| Layout resets       | provide `defaultSize` or use `autoSaveId`    |
| Drag lag            | throttle heavy `onLayout` to ≤ 16 ms         |

---

🏁 **You now have a single, portable reference** for Monaco + Monacopilot + react-resizable-panels inside **ai-productivity-app**.
Pin sections 4-9 for daily development; revisit performance & security lists before every production release.
```

---

The text is exactly the same; only Markdown structure, fences, and tables were polished for readability.
