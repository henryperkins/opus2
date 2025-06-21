import { Allotment } from 'allotment';
import 'allotment/dist/style.css';

// Wrapper component to match existing usage patterns
export default function SplitPane({ 
  split = "vertical", 
  minSize = 200, 
  defaultSize = "50%", 
  resizerStyle = {}, 
  left, 
  right, 
  children, 
  ...props 
}) {
  // Handle legacy left/right prop pattern
  if (left && right) {
    return (
      <Allotment split={split} {...props}>
        <Allotment.Pane minSize={minSize}>
          {left}
        </Allotment.Pane>
        <Allotment.Pane>
          {right}
        </Allotment.Pane>
      </Allotment>
    );
  }

  // Handle children array pattern
  if (children && Array.isArray(children)) {
    return (
      <Allotment split={split} {...props}>
        <Allotment.Pane minSize={minSize}>
          {children[0]}
        </Allotment.Pane>
        <Allotment.Pane>
          {children[1]}
        </Allotment.Pane>
      </Allotment>
    );
  }

  // Default behavior
  return (
    <Allotment split={split} {...props}>
      {children}
    </Allotment>
  );
}
