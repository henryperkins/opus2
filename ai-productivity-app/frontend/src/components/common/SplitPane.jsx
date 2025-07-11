import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";

// Wrapper component to match existing usage patterns
export default function SplitPane({
  split = "vertical",
  minSize = 200,
  defaultSize = "50%",
  resizerStyle = {},
  left,
  right,
  children,
  autoSaveId,
  className = "",
  ...props
}) {
  const direction = split === "vertical" ? "horizontal" : "vertical";
  // Convert minSize to percentage (1-100)
  const minSizePercent =
    typeof minSize === "number"
      ? Math.max(10, Math.min(45, (minSize / window.innerWidth) * 100))
      : 25;
  
  // Convert defaultSize to percentage (1-100)
  const defaultSizePercent =
    typeof defaultSize === "string" && defaultSize.includes("%")
      ? Math.max(10, Math.min(90, parseInt(defaultSize)))
      : 50;
  
  // Ensure defaultSize is not less than minSize
  const adjustedDefaultSize = Math.max(minSizePercent, defaultSizePercent);

  // Handle legacy left/right prop pattern
  if (left && right) {
    return (
      <PanelGroup
        direction={direction}
        autoSaveId={autoSaveId}
        className={className}
        {...props}
      >
        <Panel minSize={minSizePercent} defaultSize={adjustedDefaultSize}>
          {left}
        </Panel>
        <PanelResizeHandle className="w-2 bg-gray-300 dark:bg-gray-700 hover:bg-gray-400 dark:hover:bg-gray-600 transition-colors" />
        <Panel minSize={minSizePercent}>{right}</Panel>
      </PanelGroup>
    );
  }

  // Handle children array pattern
  if (children && Array.isArray(children)) {
    return (
      <PanelGroup
        direction={direction}
        autoSaveId={autoSaveId}
        className={className}
        {...props}
      >
        <Panel minSize={minSizePercent} defaultSize={adjustedDefaultSize}>
          {children[0]}
        </Panel>
        <PanelResizeHandle className="w-2 bg-gray-300 dark:bg-gray-700 hover:bg-gray-400 dark:hover:bg-gray-600 transition-colors" />
        <Panel minSize={minSizePercent}>{children[1]}</Panel>
      </PanelGroup>
    );
  }

  // Default behavior - wrap single children in panels if needed
  return (
    <PanelGroup
      direction={direction}
      autoSaveId={autoSaveId}
      className={className}
      {...props}
    >
      {children}
    </PanelGroup>
  );
}
