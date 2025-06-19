import React, { useState, useRef } from 'react';

export default function SplitPane({ left, right, initial = 50 }) {
  const [ratio, setRatio] = useState(initial);
  const dragging = useRef(false);
  const startX = useRef(0);
  const startRatio = useRef(ratio);

  const onMouseDown = (e) => {
    dragging.current = true;
    startX.current = e.clientX;
    startRatio.current = ratio;
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  };

  const onMouseMove = (e) => {
    if (!dragging.current) return;
    const delta = e.clientX - startX.current;
    const newRatio = Math.min(80, Math.max(20, startRatio.current + (delta / window.innerWidth) * 100));
    setRatio(newRatio);
  };

  const onMouseUp = () => {
    dragging.current = false;
    document.removeEventListener('mousemove', onMouseMove);
    document.removeEventListener('mouseup', onMouseUp);
  };

  return (
    <div className="flex h-full select-none">
      <div style={{ width: `${ratio}%` }} className="h-full overflow-hidden">
        {left}
      </div>
      <div
        onMouseDown={onMouseDown}
        className="w-1 bg-gray-300 cursor-col-resize"
      ></div>
      <div style={{ width: `${100 - ratio}%` }} className="h-full overflow-hidden">
        {right}
      </div>
    </div>
  );
}
