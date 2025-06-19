import React, { useState, useRef, useEffect, useCallback } from 'react';

export default function SplitPane({ left, right, initial = 50 }) {
  const [ratio, setRatio] = useState(initial);
  const dragging = useRef(false);
  const startX = useRef(0);
  const startRatio = useRef(ratio);
  const resizerRef = useRef(null);

  const onMouseMove = useCallback((e) => {
    if (!dragging.current) return;
    const delta = e.clientX - startX.current;
    const newRatio = Math.min(80, Math.max(20, startRatio.current + (delta / window.innerWidth) * 100));
    setRatio(newRatio);
  }, []);

  const onMouseUp = useCallback(() => {
    dragging.current = false;
    document.removeEventListener('mousemove', onMouseMove);
    document.removeEventListener('mouseup', onMouseUp);
  }, [onMouseMove]);

  const onMouseDown = useCallback((e) => {
    dragging.current = true;
    startX.current = e.clientX;
    startRatio.current = ratio;
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  }, [ratio, onMouseMove, onMouseUp]);

  const onKeyDown = useCallback((e) => {
    if (e.key === 'ArrowLeft') {
      e.preventDefault();
      setRatio(prev => Math.max(20, prev - 5));
    } else if (e.key === 'ArrowRight') {
      e.preventDefault();
      setRatio(prev => Math.min(80, prev + 5));
    } else if (e.key === 'Home') {
      e.preventDefault();
      setRatio(20);
    } else if (e.key === 'End') {
      e.preventDefault();
      setRatio(80);
    }
  }, []);

  // Cleanup event listeners on unmount
  useEffect(() => {
    return () => {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };
  }, [onMouseMove, onMouseUp]);

  return (
    <div className="flex h-full select-none">
      <div style={{ width: `${ratio}%` }} className="h-full overflow-hidden">
        {left}
      </div>
      <div
        ref={resizerRef}
        onMouseDown={onMouseDown}
        onKeyDown={onKeyDown}
        tabIndex={0}
        role="separator"
        aria-orientation="vertical"
        aria-valuenow={Math.round(ratio)}
        aria-valuemin={20}
        aria-valuemax={80}
        aria-label="Resize panels"
        className="w-1 bg-gray-300 cursor-col-resize hover:bg-gray-400 focus:bg-blue-500 focus:outline-none"
      ></div>
      <div style={{ width: `${100 - ratio}%` }} className="h-full overflow-hidden">
        {right}
      </div>
    </div>
  );
}
