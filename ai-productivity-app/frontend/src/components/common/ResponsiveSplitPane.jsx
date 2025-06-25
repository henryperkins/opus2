import React, { useState, useEffect } from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import useMediaQuery from '../../hooks/useMediaQuery';
import { ChevronLeft, ChevronRight, Menu, X } from 'lucide-react';

/**
 * Mobile-responsive split pane that adapts behavior based on screen size
 * - Desktop: Traditional split pane with resizer
 * - Tablet: Collapsible side panels with touch-friendly controls
 * - Mobile: Full-screen panels with slide-out navigation
 */
export default function ResponsiveSplitPane({
  left,
  right,
  defaultSize = "50%",
  minSize = 200,
  orientation = "horizontal",
  leftTitle = "Panel",
  rightTitle = "Content",
  className = "",
  ...props
}) {
  const { isMobile, isTablet, isTouchDevice } = useMediaQuery();
  const [leftPanelOpen, setLeftPanelOpen] = useState(!isMobile);
  const [rightPanelOpen, setRightPanelOpen] = useState(true);
  const [activePanel, setActivePanel] = useState('right'); // 'left', 'right', 'both'

  // Close panels on mobile when screen size changes
  useEffect(() => {
    if (isMobile) {
      setLeftPanelOpen(false);
      setActivePanel('right');
    } else if (isTablet) {
      setLeftPanelOpen(false);
      setActivePanel('right');
    } else {
      setLeftPanelOpen(true);
      setRightPanelOpen(true);
      setActivePanel('both');
    }
  }, [isMobile, isTablet]);

  // Mobile view - single panel with navigation
  if (isMobile) {
    return (
      <div className={`relative h-full ${className}`}>
        {/* Mobile Navigation Header */}
        <div className="flex items-center justify-between p-3 bg-white border-b border-gray-200 min-h-[60px]">
          <div className="flex items-center space-x-3">
            {left && (
              <button
                onClick={() => setActivePanel(activePanel === 'left' ? 'right' : 'left')}
                className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg touch-target"
                style={{ minWidth: '44px', minHeight: '44px' }}
              >
                <Menu className="w-5 h-5" />
              </button>
            )}
            <h1 className="font-semibold text-gray-900">
              {activePanel === 'left' ? leftTitle : rightTitle}
            </h1>
          </div>

          {/* Panel Toggle Buttons */}
          <div className="flex space-x-1">
            {left && (
              <button
                onClick={() => setActivePanel('left')}
                className={`px-3 py-1 text-sm rounded touch-target ${
                  activePanel === 'left'
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
                style={{ minHeight: '44px' }}
              >
                {leftTitle}
              </button>
            )}
            <button
              onClick={() => setActivePanel('right')}
              className={`px-3 py-1 text-sm rounded touch-target ${
                activePanel === 'right'
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
              style={{ minHeight: '44px' }}
            >
              {rightTitle}
            </button>
          </div>
        </div>

        {/* Panel Content */}
        <div className="h-[calc(100%-60px)] relative">
          {activePanel === 'left' && left && (
            <div className="h-full overflow-auto">
              {left}
            </div>
          )}
          {activePanel === 'right' && (
            <div className="h-full overflow-auto">
              {right}
            </div>
          )}
        </div>
      </div>
    );
  }

  // Tablet view - collapsible panels with overlay
  if (isTablet) {
    return (
      <div className={`relative h-full ${className}`}>
        {/* Left Panel Overlay */}
        {leftPanelOpen && left && (
          <>
            <div
              className="fixed inset-0 bg-black bg-opacity-50 z-30"
              onClick={() => setLeftPanelOpen(false)}
            />
            <div className="fixed top-0 left-0 w-80 h-full bg-white shadow-lg z-40 flex flex-col">
              <div className="flex items-center justify-between p-4 border-b border-gray-200">
                <h2 className="font-semibold text-gray-900">{leftTitle}</h2>
                <button
                  onClick={() => setLeftPanelOpen(false)}
                  className="p-2 text-gray-500 hover:text-gray-700 rounded-lg touch-target"
                  style={{ minWidth: '44px', minHeight: '44px' }}
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="flex-1 overflow-auto">
                {left}
              </div>
            </div>
          </>
        )}

        {/* Main Content */}
        <div className="h-full flex flex-col">
          {/* Header with panel controls */}
          <div className="flex items-center justify-between p-3 bg-white border-b border-gray-200">
            <div className="flex items-center space-x-3">
              {left && (
                <button
                  onClick={() => setLeftPanelOpen(true)}
                  className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg touch-target"
                  style={{ minWidth: '44px', minHeight: '44px' }}
                >
                  <Menu className="w-5 h-5" />
                </button>
              )}
              <h1 className="font-semibold text-gray-900">{rightTitle}</h1>
            </div>
          </div>

          {/* Right Panel Content */}
          <div className="flex-1 overflow-auto">
            {right}
          </div>
        </div>
      </div>
    );
  }

  // Desktop view - traditional split pane
  const direction = orientation === "vertical" ? "vertical" : "horizontal";
  const minSizePercent = typeof minSize === 'number' ? Math.max(10, (minSize / window.innerWidth) * 100) : 25;
  const defaultSizePercent = typeof defaultSize === 'string' && defaultSize.includes('%') 
    ? parseInt(defaultSize) 
    : 50;

  return (
    <div className={`h-full ${className}`}>
      <PanelGroup
        direction={direction}
        autoSaveId={`responsive-${orientation}-${leftTitle}-${rightTitle}`}
        {...props}
      >
        {left && (
          <Panel minSize={minSizePercent} defaultSize={defaultSizePercent}>
            <div className="h-full overflow-auto">
              {left}
            </div>
          </Panel>
        )}
        <PanelResizeHandle className="w-2 bg-gray-300 dark:bg-gray-700 hover:bg-gray-400 dark:hover:bg-gray-600 transition-colors" />
        <Panel minSize={minSizePercent}>
          <div className="h-full overflow-auto">
            {right}
          </div>
        </Panel>
      </PanelGroup>
    </div>
  );
}
