// hooks/useResponsiveLayout.js
import { useState, useEffect, useCallback } from "react";
import useMediaQuery from "./useMediaQuery";

// Standardized breakpoints for the application
export const BREAKPOINTS = {
  xs: "(max-width: 475px)",
  sm: "(max-width: 640px)",
  md: "(max-width: 768px)",
  lg: "(max-width: 1024px)",
  xl: "(max-width: 1280px)",
  "2xl": "(max-width: 1536px)",

  // Semantic breakpoints
  mobile: "(max-width: 768px)",
  tablet: "(min-width: 769px) and (max-width: 1024px)",
  desktop: "(min-width: 1025px)",

  // Orientation
  landscape: "(orientation: landscape)",
  portrait: "(orientation: portrait)",

  // Specific features
  touch: "(pointer: coarse)",
  hover: "(hover: hover)",

  // Accessibility
  reducedMotion: "(prefers-reduced-motion: reduce)",
  highContrast: "(prefers-contrast: high)",
  darkMode: "(prefers-color-scheme: dark)",
};

// Layout types
export const LAYOUT_TYPES = {
  MOBILE: "mobile",
  TABLET: "tablet",
  DESKTOP: "desktop",
  MOBILE_LANDSCAPE: "mobile_landscape",
  TABLET_LANDSCAPE: "tablet_landscape",
};

// Responsive layout hook
export function useResponsiveLayout() {
  const isMobile = useMediaQuery(BREAKPOINTS.mobile);
  const isTablet = useMediaQuery(BREAKPOINTS.tablet);
  const isDesktop = useMediaQuery(BREAKPOINTS.desktop);
  const isLandscape = useMediaQuery(BREAKPOINTS.landscape);
  const isTouch = useMediaQuery(BREAKPOINTS.touch);
  const hasHover = useMediaQuery(BREAKPOINTS.hover);
  const prefersReducedMotion = useMediaQuery(BREAKPOINTS.reducedMotion);

  // Determine current layout type
  const layoutType = (() => {
    if (isMobile) {
      return isLandscape ? LAYOUT_TYPES.MOBILE_LANDSCAPE : LAYOUT_TYPES.MOBILE;
    }
    if (isTablet) {
      return isLandscape ? LAYOUT_TYPES.TABLET_LANDSCAPE : LAYOUT_TYPES.TABLET;
    }
    return LAYOUT_TYPES.DESKTOP;
  })();

  // Responsive component configuration
  const config = {
    // Layout properties
    layoutType,
    isMobile,
    isTablet,
    isDesktop,
    isLandscape,
    isPortrait: !isLandscape,

    // Interaction capabilities
    isTouch,
    hasHover,
    supportsGestures: isTouch && isMobile,

    // Accessibility preferences
    prefersReducedMotion,

    // Component sizing
    containerClass: (() => {
      if (isMobile) return "container-mobile";
      if (isTablet) return "container-tablet";
      return "container-desktop";
    })(),

    // Navigation preferences
    useBottomSheet: isMobile,
    useSidebar: isDesktop,
    useCollapsible: isTablet,

    // Content display
    showFullContent: isDesktop,
    showSummaryContent: isMobile,
    useCardLayout: isMobile || isTablet,
    useTableLayout: isDesktop,

    // Interaction patterns
    useContextMenu: hasHover && isDesktop,
    useLongPress: isTouch,
    useDoubleClick: hasHover,

    // Modal behavior
    useFullScreenModal: isMobile,
    useOverlayModal: isDesktop,
    useSlideModal: isTablet,

    // Input methods
    preferKeyboard: isDesktop && hasHover,
    preferTouch: isTouch,

    // Spacing and sizing
    spacing: {
      xs: isMobile ? "0.25rem" : "0.5rem",
      sm: isMobile ? "0.5rem" : "0.75rem",
      md: isMobile ? "0.75rem" : "1rem",
      lg: isMobile ? "1rem" : "1.5rem",
      xl: isMobile ? "1.5rem" : "2rem",
    },

    // Font sizing
    fontSize: {
      xs: isMobile ? "0.75rem" : "0.75rem",
      sm: isMobile ? "0.875rem" : "0.875rem",
      base: isMobile ? "1rem" : "1rem",
      lg: isMobile ? "1.125rem" : "1.125rem",
      xl: isMobile ? "1.25rem" : "1.5rem",
    },
  };

  return config;
}

// Hook for responsive component behavior
export function useResponsiveComponent(componentName, options = {}) {
  const layout = useResponsiveLayout();
  const [componentState, setComponentState] = useState({
    isCollapsed: false,
    isMinimized: false,
    variant: "default",
  });

  // Component-specific responsive behavior
  const getComponentConfig = useCallback(() => {
    const baseConfig = {
      // Common responsive patterns
      className: `${componentName} ${layout.containerClass}`,
      showLabels: layout.isDesktop || options.alwaysShowLabels,
      showIcons: true,
      showTooltips: layout.hasHover && !layout.isTouch,

      // Animation preferences
      animate: !layout.prefersReducedMotion,
      transition: layout.prefersReducedMotion ? "none" : "all 0.2s ease",

      // Interaction behavior
      onClick: layout.preferTouch ? "touch" : "click",
      onHover: layout.hasHover ? true : false,
      onLongPress: layout.isTouch ? true : false,

      // Layout behavior
      stackOnMobile: layout.isMobile,
      useGrid: layout.isDesktop,
      useFlex: layout.isMobile || layout.isTablet,
    };

    // Component-specific overrides
    switch (componentName) {
      case "knowledge-panel":
        return {
          ...baseConfig,
          useBottomSheet: layout.isMobile,
          useSidebar: layout.isDesktop,
          defaultPosition: layout.isMobile ? "bottom" : "right",
          allowMinimize: true,
          snapPoints: layout.isMobile ? [0.3, 0.6, 0.9] : undefined,
        };

      case "model-switcher":
        return {
          ...baseConfig,
          useDropdown: layout.isDesktop,
          useModal: layout.isMobile,
          showModelIcons: layout.isDesktop,
          showModelNames: true,
          compact: layout.isMobile,
        };

      case "chat-input":
        return {
          ...baseConfig,
          multiline: layout.isDesktop,
          expandable: layout.isMobile,
          showAttachments: layout.isDesktop || layout.isTablet,
          useFloatingActions: layout.isMobile,
        };

      case "message-list":
        return {
          ...baseConfig,
          virtualScroll: layout.isMobile,
          showAvatars: layout.isDesktop,
          showTimestamps: layout.isDesktop,
          compact: layout.isMobile,
          groupMessages: layout.isMobile,
        };

      case "code-editor":
        return {
          ...baseConfig,
          showLineNumbers: layout.isDesktop,
          showMinimap: layout.isDesktop && !options.compact,
          wordWrap: layout.isMobile,
          fontSize: layout.isMobile ? 14 : 16,
          tabSize: layout.isMobile ? 2 : 4,
        };

      default:
        return baseConfig;
    }
  }, [componentName, layout, options]);

  // Update component state based on layout changes
  useEffect(() => {
    const config = getComponentConfig();
    setComponentState((prev) => ({
      ...prev,
      variant: layout.isMobile
        ? "mobile"
        : layout.isTablet
          ? "tablet"
          : "desktop",
    }));
  }, [layout, getComponentConfig]);

  // Component state management
  const toggleCollapsed = useCallback(() => {
    setComponentState((prev) => ({ ...prev, isCollapsed: !prev.isCollapsed }));
  }, []);

  const toggleMinimized = useCallback(() => {
    setComponentState((prev) => ({ ...prev, isMinimized: !prev.isMinimized }));
  }, []);

  const setVariant = useCallback((variant) => {
    setComponentState((prev) => ({ ...prev, variant }));
  }, []);

  return {
    // Layout information
    layout,

    // Component configuration
    config: getComponentConfig(),

    // Component state
    ...componentState,

    // State management
    toggleCollapsed,
    toggleMinimized,
    setVariant,

    // Utility functions
    getBreakpointClass: (breakpoint) =>
      layout[breakpoint] ? `${componentName}-${breakpoint}` : "",
    getResponsiveClass: () => `${componentName}-${layout.layoutType}`,

    // Conditional rendering helpers
    showOnMobile: layout.isMobile,
    showOnTablet: layout.isTablet,
    showOnDesktop: layout.isDesktop,
    hideOnMobile: !layout.isMobile,
    hideOnTablet: !layout.isTablet,
    hideOnDesktop: !layout.isDesktop,
  };
}

// CSS-in-JS responsive styles helper
export function getResponsiveStyles(layout, baseStyles = {}) {
  return {
    ...baseStyles,

    // Responsive container
    container: {
      width: "100%",
      maxWidth: layout.isMobile ? "100%" : layout.isTablet ? "768px" : "1200px",
      margin: "0 auto",
      padding: layout.spacing.md,
      ...baseStyles.container,
    },

    // Responsive grid
    grid: {
      display: "grid",
      gridTemplateColumns: layout.isMobile
        ? "1fr"
        : layout.isTablet
          ? "repeat(2, 1fr)"
          : "repeat(auto-fit, minmax(300px, 1fr))",
      gap: layout.spacing.md,
      ...baseStyles.grid,
    },

    // Responsive flex
    flex: {
      display: "flex",
      flexDirection: layout.isMobile ? "column" : "row",
      gap: layout.spacing.sm,
      alignItems: layout.isMobile ? "stretch" : "center",
      ...baseStyles.flex,
    },

    // Responsive text
    text: {
      fontSize: layout.fontSize.base,
      lineHeight: layout.isMobile ? "1.5" : "1.6",
      ...baseStyles.text,
    },
  };
}

export default useResponsiveLayout;
