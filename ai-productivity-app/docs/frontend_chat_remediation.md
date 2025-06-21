# Front-End Chat Interface – Remediation Plan

_Date: 2025-06-21_

This document consolidates the problems discovered during the June-2025 front-end
audit and maps each one to **concrete, engineer-friendly tasks**.  The goal is
to track progress systematically and allow parallel work where safe.

Legend
-------
🟠  = pure front-end change (no back-end / DB impact)  
🔴  = requires back-end work or API contract change

------------------------------------------------------------------------
1. useChat hook 🟠
------------------------------------------------------------------------

| ID | Issue | Actionable fix |
|----|-------|----------------|
| 1.1 | `sendMessage()` returns `void`; callers expect a message-id and break when `undefined`. | • Refactor `sendMessage` to return a **Promise<string>**.<br>• Generate a temporary UUID (e.g. `tmp-${nanoid()}`) and push an optimistic message into `messages`.<br>• Resolve the promise once the server echoes the canonical id.<br>• Replace provisional ids in state. |
| 1.2 | No optimistic insert → sluggish UI. | Covered by 1.1. |
| 1.3 | Duplicate `streamingMessages` maps (hook vs page). | • Move the single map into `useChat` and expose as `streamingMessages`.<br>• Delete local duplicates in `ChatPage` & `ProjectChatPage`. |
| 1.4 | Reconnect scaffolding is unused. | • Track `reconnectAttempts` and compute back-off (`min(1000*2**n,30s)`).<br>• After `maxReconnectAttempts` emit toast & stop. |
| 1.5 | Timeout reference never cleared. | Clear `reconnectTimeoutRef.current` in `useEffect` cleanup. |

Deliverable PR: **frontend/#1234-chat-hook-hardening**

------------------------------------------------------------------------
2. ChatPage component 🟠
------------------------------------------------------------------------

| ID | Issue | Actionable fix |
|----|-------|----------------|
| 2.1 | Depends on old `sendMessage` contract. | Adjust after task 1: use returned id, no `undefined` guard. |
| 2.2 | `handleStreamingUpdate` defined but never used. | Remove dead code. |
| 2.3 | Local streaming map dupes hook. | Delete. |
| 2.4 | Direct mutation of `modelSelection.currentModel`. | Convert to stateful setter, e.g. `const [currentModel,setCurrentModel] = useState()`. Update downstream imports. |
| 2.5 | React key warnings when `message.id` is undefined. | Fixed once 1.1 returns valid ids. |

------------------------------------------------------------------------
3. ProjectChatPage component 🟠 / 🔴
------------------------------------------------------------------------

| ID | Issue | Actionable fix |
|----|-------|----------------|
| 3.1 | Streaming integration TODO – assistant responses arrive only after full render. | Re-use `streamingMessages` from hook and render partial chunks like `ChatPage`. |
| 3.2 | `fetch('/api/...')` hard-coded paths bypass axios baseURL. | Replace with `client.post('/code/execute', …)` etc. (Back-end paths unchanged ⇒ 🟠). |

------------------------------------------------------------------------
4. EnhancedCommandInput 🟠
------------------------------------------------------------------------

| ID | Issue | Actionable fix |
|----|-------|----------------|
| 4.1 | `onTyping` fires per keystroke. | Debounce (300 ms) using `lodash.debounce`. |
| 4.2 | “Clear citations” button leaves numbers in draft. | Also strip `\[\d+]` regex from `message` state. |
| 4.3 | Enter-to-send unavailable inside Monaco. | Add key-binding: `editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, handleSubmit)`. |

------------------------------------------------------------------------
5. Misc Page Issues 🟠
------------------------------------------------------------------------

| ID | Page | Issue | Action |
|----|------|-------|--------|
| 5.1 | ProjectFilesPage | Uses undefined `f.id` for React key. | Replace with `f.path` or a combined string. |
| 5.2 | Router | Obsolete `/dashboard` alias. | Deprecate in one release; add 307 redirect then delete. |
| 5.3 | useMediaQuery | `isTablet` comparison typo. | `const isTablet = breakpoint === 'tablet' || breakpoint === 'sm';` → should be `['tablet','sm'].includes(breakpoint)`. |

------------------------------------------------------------------------
6. Accessibility / UX 🟠
------------------------------------------------------------------------

1. Add `aria-label` to icon-only buttons in Chat header.
2. `MobileBottomSheet` snapPoints: Provide pixel values on iOS Safari (e.g. `[0.3,0.6,0.8]` → `[0.3*vh,…]` or switch to library’s percentage mode).

------------------------------------------------------------------------
7. Back-end coordination tasks 🔴
------------------------------------------------------------------------

Although primarily a front-end effort, two items need API cooperation:

1. **Streaming chunks format** – ensure server still sends `stream_chunk` / `stream_end` messages compatible with the consolidated streaming map.  No contract change expected but verify.
2. **Axios wrapper endpoints** – validate that `/api/code/execute` and others exist; if not, expose minimal handlers or align FE path.

------------------------------------------------------------------------
Execution order
------------------------------------------------------------------------

1. Hook hardening (section 1) – unblocks everything else.
2. ChatPage & ProjectChatPage clean-up.
3. Typing debounce & command-input UX.
4. Misc page & a11y polish.

Merged PRs automatically close the corresponding table rows above.
