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
  const minSizePercent =
    typeof minSize === "number"
      ? Math.max(10, (minSize / window.innerWidth) * 100)
      : 25;
  const defaultSizePercent =
    typeof defaultSize === "string" && defaultSize.includes("%")
      ? parseInt(defaultSize)
      : 50;

  // Handle legacy left/right prop pattern
  if (left && right) {
    return (
      <PanelGroup
        direction={direction}
        autoSaveId={autoSaveId}
        className={className}
        {...props}
      >
        <Panel minSize={minSizePercent} defaultSize={defaultSizePercent}>
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
        <Panel minSize={minSizePercent} defaultSize={defaultSizePercent}>
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
