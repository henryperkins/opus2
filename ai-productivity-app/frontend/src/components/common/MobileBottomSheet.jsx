import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { ChevronUp, ChevronDown, X, GripHorizontal } from 'lucide-react';
import useMediaQuery from '../../hooks/useMediaQuery';

/**
 * Mobile-optimized bottom sheet component for knowledge panels and secondary content
 * Features:
 * - Smooth slide-up animation
 * - Drag to resize/dismiss
 * - Snap points for different heights
 * - Touch-friendly interactions
 */
export default function MobileBottomSheet({
  isOpen,
  onClose,
  title,
  children,
  snapPoints = [0.3, 0.6, 0.9], // Percentage of screen height
  initialSnap = 0.6,
  className = "",
  backdrop = true,
  showHandle = true,
  ...props
}) {
  const { isMobile, windowSize } = useMediaQuery();
  const [currentSnap, setCurrentSnap] = useState(initialSnap);
  const [isDragging, setIsDragging] = useState(false);
  const [startY, setStartY] = useState(0);
  const [startHeight, setStartHeight] = useState(0);
  const sheetRef = useRef(null);
  const contentRef = useRef(null);

  // Calculate sheet height based on snap point
  // Calculate height in pixels and round for Safari rendering quirks
  const sheetHeight = Math.round(windowSize.height * currentSnap);

  // Handle drag start
  const handleDragStart = (e) => {
    if (!isMobile) return;

    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    setIsDragging(true);
    setStartY(clientY);
    setStartHeight(sheetHeight);

    // Prevent body scroll during drag
    document.body.style.overflow = 'hidden';
  };

  // Handle drag move
  const handleDragMove = (e) => {
    if (!isDragging || !isMobile) return;

    e.preventDefault();
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    const deltaY = startY - clientY;
    const newHeight = Math.max(0, Math.min(windowSize.height * 0.9, startHeight + deltaY));
    const newSnap = newHeight / windowSize.height;

    setCurrentSnap(newSnap);
  };

  // Handle drag end
  const handleDragEnd = () => {
    if (!isDragging || !isMobile) return;

    setIsDragging(false);
    document.body.style.overflow = '';

    // Find closest snap point
    const closest = snapPoints.reduce((prev, curr) => {
      return Math.abs(curr - currentSnap) < Math.abs(prev - currentSnap) ? curr : prev;
    });

    // If dragged below minimum threshold, close the sheet
    if (currentSnap < 0.1) {
      onClose();
    } else {
      setCurrentSnap(closest);
    }
  };

  // Add event listeners for drag
  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e) => handleDragMove(e);
    const handleMouseUp = () => handleDragEnd();
    const handleTouchMove = (e) => handleDragMove(e);
    const handleTouchEnd = () => handleDragEnd();

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.addEventListener('touchmove', handleTouchMove, { passive: false });
    document.addEventListener('touchend', handleTouchEnd);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.removeEventListener('touchmove', handleTouchMove);
      document.removeEventListener('touchend', handleTouchEnd);
    };
  }, [isDragging, startY, startHeight, currentSnap, snapPoints, windowSize.height]);

  // Handle keyboard events
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, onClose]);

  // Don't render on desktop or when closed
  if (!isMobile || !isOpen) {
    return null;
  }

  const sheetContent = (
    <>
      {/* Backdrop */}
      {backdrop && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40"
          onClick={onClose}
        />
      )}

      {/* Bottom Sheet */}
      <div
        ref={sheetRef}
        className={`fixed bottom-0 left-0 right-0 bg-white rounded-t-2xl shadow-2xl z-50 flex flex-col dynamic-height dynamic-transform ${className}`}
        style={{
          '--dynamic-height': `${sheetHeight}px`,
          '--dynamic-transform': isOpen ? 'translateY(0)' : 'translateY(100%)',
        }}
        {...props}
      >
        {/* Handle */}
        {showHandle && (
          <div
            className="flex items-center justify-center py-3 cursor-grab active:cursor-grabbing"
            onMouseDown={handleDragStart}
            onTouchStart={handleDragStart}
          >
            <div className="w-10 h-1 bg-gray-300 rounded-full" />
          </div>
        )}

        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
          <div className="flex items-center space-x-2">
            {/* Snap point controls */}
            <div className="flex space-x-1">
              {snapPoints.map((snap, index) => (
                <button
                  key={snap}
                  onClick={() => setCurrentSnap(snap)}
                  className={`w-2 h-2 rounded-full transition-colors ${
                    Math.abs(currentSnap - snap) < 0.05
                      ? 'bg-brand-primary-600'
                      : 'bg-gray-300'
                  }`}
                  title={`${Math.round(snap * 100)}% height`}
                />
              ))}
            </div>

            <button
              onClick={onClose}
              className="p-2 text-gray-500 hover:text-gray-700 rounded-lg touch-safe"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div
          ref={contentRef}
          className="scrollable-content touch-safe"
          style={{
            '--user-select': isDragging ? 'none' : 'auto',
          }}
        >
          {children}
        </div>
      </div>
    </>
  );

  // Render in portal for proper z-index layering
  return createPortal(sheetContent, document.body);
}
