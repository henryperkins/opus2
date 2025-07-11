// Utility helper to copy arbitrary text to the user clipboard.
//
// We prefer using the asynchronous Clipboard API when it is available and the
// document is served from a secure context (required by most browsers).
// For older browsers or non-secure contexts we gracefully fall back to
// creating a temporary <textarea> element and executing the legacy
// `document.execCommand('copy')` command.
//
// The function returns a Promise that resolves to a boolean indicating whether
// the copy operation appeared to succeed.

/**
 * Copy a string to the user's clipboard.
 *
 * @param {string} text - The text that should be placed on the clipboard.
 * @returns {Promise<boolean>} A promise that resolves to `true` when the text
 *                             is (most likely) copied successfully, otherwise
 *                             `false`.
 */
export async function copyToClipboard(text) {
  if (typeof text !== "string") {
    // Normalise any non-string input to string to avoid runtime errors.
    text = String(text);
  }

  // Prefer navigator.clipboard when available (secure contexts only).
  if (
    typeof navigator !== "undefined" &&
    navigator.clipboard &&
    window.isSecureContext
  ) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (err) {
      // Swallow the error and fall back to the older approach.
    }
  }

  // Fallback approach: create a hidden <textarea>, select its content and
  // execute the legacy copy command.
  try {
    const textArea = document.createElement("textarea");
    textArea.value = text;

    // Move the element out of the viewport so it isn't visible.
    textArea.style.position = "fixed";
    textArea.style.top = "-1000px";
    textArea.style.left = "-1000px";

    document.body.appendChild(textArea);

    textArea.focus();
    textArea.select();

    const successful = document.execCommand("copy");

    document.body.removeChild(textArea);

    return successful;
  } catch (err) {
    return false;
  }
}
