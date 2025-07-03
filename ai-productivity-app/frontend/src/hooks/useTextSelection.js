import { useState, useEffect } from 'react';

/**
 * Hook that tracks the current user text selection and returns both the text
 * and the (x, y) coordinates where a floating context-menu could be rendered.
 * Coordinates are computed from the selection's bounding client rect and are
 * relative to the viewport.
 */
export function useTextSelection() {
  const [selectionText, setSelectionText] = useState('');
  const [position, setPosition] = useState({ x: 0, y: 0 });

  useEffect(() => {
    function handleSelectionChange() {
      const sel = window.getSelection();
      if (!sel) return;

      const text = sel.toString();
      if (!text) {
        setSelectionText('');
        return;
      }

      // Try to compute a reasonable anchor position for the context menu – use
      // the first range's bounding rect if available.
      try {
        const range = sel.getRangeAt(0);
        const rect = range.getBoundingClientRect();
        const x = rect.left + rect.width / 2;
        const y = rect.top - 8; // a little above the selection
        setPosition({ x, y });
      } catch {
        // ignore – might happen if range is collapsed
      }

      setSelectionText(text);
    }

    document.addEventListener('selectionchange', handleSelectionChange);
    return () => document.removeEventListener('selectionchange', handleSelectionChange);
  }, []);

  return { selectionText, position };
}

export default useTextSelection;
