import React, { useState } from "react";
import SkeletonLoader from "../components/common/SkeletonLoader";
import ErrorBoundary from "../components/common/ErrorBoundary";
import EmptyState from "../components/common/EmptyState";
import ResponsiveSplitPane from "../components/common/ResponsiveSplitPane";
import MobileBottomSheet from "../components/common/MobileBottomSheet";
import useMediaQuery from "../hooks/useMediaQuery";

/**
 * Demo page showcasing all the enhanced Phase 1 components
 * This demonstrates the polished mobile-responsive features
 */
export default function Phase1Demo() {
  const { isMobile, isTablet, breakpoint } = useMediaQuery();
  const [activeDemo, setActiveDemo] = useState("skeleton");
  const [bottomSheetOpen, setBottomSheetOpen] = useState(false);
  const [errorBoundaryKey, setErrorBoundaryKey] = useState(0);

  const triggerError = () => {
    setErrorBoundaryKey((prev) => prev + 1);
    throw new Error("WebSocket connection failed - demo error");
  };

  const ErrorComponent = () => {
    const [shouldError, setShouldError] = useState(false);

    if (shouldError) {
      throw new Error("Demo WebSocket error");
    }

    return (
      <div className="p-6 space-y-4">
        <h3 className="text-lg font-semibold">Error Boundary Demo</h3>
        <p className="text-gray-600">
          Click the button below to trigger a demo error:
        </p>
        <button
          onClick={() => setShouldError(true)}
          className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
        >
          Trigger WebSocket Error
        </button>
      </div>
    );
  };

  const demos = {
    skeleton: {
      title: "Loading States",
      component: (
        <div className="p-6 space-y-6">
          <div>
            <h3 className="text-lg font-semibold mb-4">Chat Message Loading</h3>
            <SkeletonLoader type="message" count={2} />
          </div>

          <div>
            <h3 className="text-lg font-semibold mb-4">Streaming Response</h3>
            <SkeletonLoader type="streaming-message" />
          </div>

          <div>
            <h3 className="text-lg font-semibold mb-4">WebSocket Connecting</h3>
            <SkeletonLoader type="websocket-connecting" />
          </div>

          <div>
            <h3 className="text-lg font-semibold mb-4">Model Switching</h3>
            <SkeletonLoader type="model-switching" />
          </div>

          <div>
            <h3 className="text-lg font-semibold mb-4">Search Results</h3>
            <SkeletonLoader type="search-result" count={2} />
          </div>

          <div>
            <h3 className="text-lg font-semibold mb-4">Knowledge Panel</h3>
            <SkeletonLoader type="knowledge-panel" />
          </div>
        </div>
      ),
    },
    errors: {
      title: "Error Handling",
      component: (
        <ErrorBoundary key={errorBoundaryKey}>
          <ErrorComponent />
        </ErrorBoundary>
      ),
    },
    empty: {
      title: "Empty States",
      component: (
        <div className="p-6 space-y-8">
          <div>
            <h3 className="text-lg font-semibold mb-4">Chat Empty State</h3>
            <EmptyState type="chat" />
          </div>

          <div>
            <h3 className="text-lg font-semibold mb-4">
              WebSocket Disconnected
            </h3>
            <EmptyState
              type="websocket-disconnected"
              action={{
                text: "Reconnect",
                onClick: () => alert("Reconnecting..."),
                variant: "primary",
              }}
            />
          </div>

          <div>
            <h3 className="text-lg font-semibold mb-4">No Search Results</h3>
            <EmptyState type="search" />
          </div>

          <div>
            <h3 className="text-lg font-semibold mb-4">Model Unavailable</h3>
            <EmptyState
              type="model-unavailable"
              action={{
                text: "Switch Model",
                onClick: () => alert("Opening model selector..."),
                variant: "primary",
              }}
            />
          </div>
        </div>
      ),
    },
    responsive: {
      title: "Responsive Layout",
      component: (
        <div className="h-96">
          <ResponsiveSplitPane
            left={
              <div className="p-4 bg-blue-50 h-full">
                <h3 className="font-semibold mb-2">Chat Panel</h3>
                <p className="text-sm text-gray-600">
                  This panel adapts based on screen size:
                </p>
                <ul className="text-sm text-gray-600 mt-2 space-y-1">
                  <li>• Mobile: Tab-based navigation</li>
                  <li>• Tablet: Slide-out overlay</li>
                  <li>• Desktop: Traditional split pane</li>
                </ul>
                <div className="mt-4 p-2 bg-white rounded text-xs">
                  Current: {breakpoint}
                </div>
              </div>
            }
            right={
              <div className="p-4 bg-green-50 h-full">
                <h3 className="font-semibold mb-2">Editor Panel</h3>
                <p className="text-sm text-gray-600">
                  The right panel maintains focus while the left panel becomes
                  contextual on smaller screens.
                </p>
                <div className="mt-4 space-y-2 text-xs">
                  <div>Mobile: {isMobile ? "✅" : "❌"}</div>
                  <div>Tablet: {isTablet ? "✅" : "❌"}</div>
                  <div>Screen: {window.innerWidth}px</div>
                </div>
              </div>
            }
            leftTitle="Chat"
            rightTitle="Editor"
          />
        </div>
      ),
    },
    mobile: {
      title: "Mobile Features",
      component: (
        <div className="p-6 space-y-6">
          <div>
            <h3 className="text-lg font-semibold mb-4">Bottom Sheet Demo</h3>
            <p className="text-gray-600 mb-4">
              On mobile, panels become bottom sheets for better UX.
            </p>
            <button
              onClick={() => setBottomSheetOpen(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 touch-target"
            >
              Open Knowledge Panel
            </button>
          </div>

          <div>
            <h3 className="text-lg font-semibold mb-4">Touch Targets</h3>
            <div className="flex flex-wrap gap-2">
              <button className="touch-target bg-gray-200 rounded-lg text-sm">
                44px Min
              </button>
              <button className="touch-target bg-blue-100 rounded-lg text-sm">
                Touch Friendly
              </button>
              <button className="touch-target bg-green-100 rounded-lg text-sm">
                Accessible
              </button>
            </div>
          </div>

          <div>
            <h3 className="text-lg font-semibold mb-4">Device Info</h3>
            <div className="bg-gray-100 p-4 rounded-lg text-sm space-y-1">
              <div>
                Breakpoint: <strong>{breakpoint}</strong>
              </div>
              <div>
                Mobile: <strong>{isMobile ? "Yes" : "No"}</strong>
              </div>
              <div>
                Tablet: <strong>{isTablet ? "Yes" : "No"}</strong>
              </div>
              <div>
                Screen:{" "}
                <strong>
                  {window.innerWidth}×{window.innerHeight}
                </strong>
              </div>
            </div>
          </div>
        </div>
      ),
    },
  };

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <h1 className="text-xl font-semibold text-gray-900">
              Phase 1: Polish & Stabilization Demo
            </h1>
            <div className="text-sm text-gray-500">
              {breakpoint} • {window.innerWidth}px
            </div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex space-x-8 overflow-x-auto">
            {Object.entries(demos).map(([key, demo]) => (
              <button
                key={key}
                onClick={() => setActiveDemo(key)}
                className={`py-2 px-1 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                  activeDemo === key
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                {demo.title}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto py-6">
        <div className="bg-white rounded-lg shadow">
          {demos[activeDemo]?.component}
        </div>
      </div>

      {/* Mobile Bottom Sheet */}
      <MobileBottomSheet
        isOpen={bottomSheetOpen}
        onClose={() => setBottomSheetOpen(false)}
        title="Knowledge Context"
        snapPoints={[0.3, 0.6, 0.8]}
        initialSnap={0.6}
      >
        <div className="p-4 space-y-4">
          <h3 className="font-semibold">Knowledge Panel Content</h3>
          <p className="text-gray-600">
            This is how knowledge panels appear on mobile devices. You can drag
            the handle to resize or swipe down to dismiss.
          </p>
          <div className="space-y-2">
            <div className="p-3 bg-blue-50 rounded-lg">
              <div className="font-medium text-sm">Code Context</div>
              <div className="text-xs text-gray-600">
                Active functions and variables
              </div>
            </div>
            <div className="p-3 bg-green-50 rounded-lg">
              <div className="font-medium text-sm">Documentation</div>
              <div className="text-xs text-gray-600">
                Relevant docs and examples
              </div>
            </div>
            <div className="p-3 bg-purple-50 rounded-lg">
              <div className="font-medium text-sm">Related Files</div>
              <div className="text-xs text-gray-600">Connected components</div>
            </div>
          </div>
        </div>
      </MobileBottomSheet>
    </div>
  );
}
