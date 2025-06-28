import { useState } from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { Brain, X } from 'lucide-react';

/**
 * Simplified chat layout component using only react-resizable-panels and Tailwind CSS
 * Eliminates the over-engineered responsive system while maintaining functionality
 */
export default function ChatLayout({
  children,
  sidebar,
  editor,
  showSidebar = true,
  showEditor = false,
  onSidebarToggle,
  onEditorToggle,
  onSidebarClose,
  onEditorClose
}) {
  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-gray-900">
      {/* Main horizontal layout */}
      <PanelGroup
        direction="horizontal"
        className="flex-1"
        autoSaveId="chat-layout-main"
      >
        {/* Chat/Content Area */}
        <Panel id="content" order={1} defaultSize={showSidebar ? 70 : 100} minSize={50}>
          {showEditor ? (
            // Vertical split for chat + editor
            <PanelGroup
              direction="vertical"
              autoSaveId="chat-editor-vertical"
            >
              <Panel id="chat" order={1} defaultSize={65} minSize={30}>
                {children}
              </Panel>

              <PanelResizeHandle className="h-1 bg-gray-300 dark:bg-gray-600 hover:bg-blue-500 transition-colors group">
                <div className="h-full flex items-center justify-center group-hover:bg-blue-100 dark:group-hover:bg-blue-900/30 transition-colors">
                  <div className="w-8 h-0.5 bg-gray-400 rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
              </PanelResizeHandle>

              <Panel id="editor" order={2} defaultSize={35} minSize={20}>
                <div className="h-full relative">
                  {/* Close button for editor */}
                  {onEditorClose && (
                    <button
                      onClick={onEditorClose}
                      className="absolute top-2 right-2 z-10 p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                      aria-label="Close Code Editor"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                  {editor}
                </div>
              </Panel>
            </PanelGroup>
          ) : (
            children
          )}
        </Panel>

        {/* Sidebar - Hidden on mobile via CSS */}
        {showSidebar && sidebar && (
          <>
            <PanelResizeHandle className="w-1 bg-gray-300 dark:bg-gray-600 hover:bg-blue-500 transition-colors hidden md:block group">
              <div className="w-full h-full flex items-center justify-center group-hover:bg-blue-100 dark:group-hover:bg-blue-900/30 transition-colors">
                <div className="w-0.5 h-8 bg-gray-400 rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </PanelResizeHandle>

            <Panel
              id="sidebar"
              order={2}
              defaultSize={30}
              minSize={20}
              maxSize={40}
              className="hidden md:block"
            >
              <div className="h-full relative">
                {/* Close button for sidebar */}
                {onSidebarClose && (
                  <button
                    onClick={onSidebarClose}
                    className="absolute top-2 right-2 z-10 p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                    aria-label="Close Knowledge Assistant"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
                {sidebar}
              </div>
            </Panel>
          </>
        )}
      </PanelGroup>

      {/* Mobile Sidebar - Bottom drawer */}
      {showSidebar && sidebar && (
        <div className="md:hidden">
          <MobileDrawer>
            {sidebar}
          </MobileDrawer>
        </div>
      )}
    </div>
  );
}

/**
 * Simple mobile drawer that's collapsible
 * Replaces the over-engineered MobileBottomSheet
 */
function MobileDrawer({ children }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      {/* Toggle button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-20 right-4 z-50 p-3 bg-blue-600 text-white rounded-full shadow-lg md:hidden hover:bg-blue-700 transition-colors"
        aria-label="Toggle Knowledge Assistant"
      >
        <Brain className="w-5 h-5" />
      </button>

      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/30 backdrop-blur-sm z-40 md:hidden"
          onClick={() => setIsOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Drawer */}
      <div className={`
        fixed inset-x-0 bottom-0 z-50 bg-white dark:bg-gray-800
        transform transition-transform duration-300 ease-out
        rounded-t-xl shadow-xl md:hidden
        ${isOpen ? 'translate-y-0' : 'translate-y-full'}
      `}>
        {/* Handle */}
        <div className="flex items-center justify-center py-3">
          <div className="w-10 h-1 bg-gray-300 rounded-full" />
        </div>

        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Knowledge Assistant</h2>
          <button
            onClick={() => setIsOpen(false)}
            className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-lg"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 max-h-[60vh] overflow-y-auto">
          {children}
        </div>
      </div>
    </>
  );
}
