// src/utils/clipboard.js
// Utility for copying text to the clipboard across browsers.
//
// Exported API
//   copyToClipboard(text: string): Promise<boolean>
//
// Returns `true` when the text was successfully copied, otherwise `false`.
// Uses the modern Clipboard API when available and falls back to a
// textarea + document.execCommand approach for older browsers or in cases
// where the user’s permission settings block the API.
//
// All consumers import as:
//
//   import { copyToClipboard } from '../../utils/clipboard';
//
// ──────────────────────────────────────────────────────────────────────────────
export async function copyToClipboard(text) {
  // Guard against SSR / non-browser environments
  if (typeof window === 'undefined' || typeof document === 'undefined') {
    return false;
  }

  if (!text) {
    return false;
  }

  // Prefer the asynchronous Clipboard API when available
  if (navigator?.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // Fall through to legacy approach on failure
    }
  }

  // Legacy fallback: create an off-screen textarea and copy its contents
  try {
    const textarea = document.createElement('textarea');
    textarea.value = text;

    // Position off-screen to avoid scroll jumps / visual artifacts
    textarea.style.position = 'fixed';
    textarea.style.top = '-9999px';
    textarea.style.left = '-9999px';
    textarea.setAttribute('readonly', '');

    document.body.appendChild(textarea);

    textarea.select();
    textarea.setSelectionRange(0, textarea.value.length); // Mobile support

    const successful = document.execCommand('copy');
    document.body.removeChild(textarea);

    return successful;
  } catch {
    return false;
  }
}
