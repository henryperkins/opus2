// components/layout/ResponsiveContainer.jsx
import React from 'react';
import { useResponsiveLayout, getResponsiveStyles } from '../../hooks/useResponsiveLayout';

/**
 * ResponsiveContainer - A wrapper component that provides consistent responsive behavior
 * across the application. Eliminates duplicate mobile/desktop logic.
 */
export default function ResponsiveContainer({
  children,
  component = 'div',
  variant = 'default',
  className = '',
  style = {},
  padding = true,
  maxWidth = true,
  center = true,
  fullHeight = false,
  ...props
}) {
  const layout = useResponsiveLayout();
  const Component = component;

  // Generate responsive styles based on variant
  const getVariantStyles = () => {
    const baseStyles = getResponsiveStyles(layout);
    
    switch (variant) {
      case 'page':
        return {
          ...baseStyles.container,
          minHeight: fullHeight ? '100vh' : 'auto',
          padding: padding ? layout.spacing.lg : 0,
          maxWidth: maxWidth ? (layout.isMobile ? '100%' : '1200px') : '100%'
        };
        
      case 'section':
        return {
          width: '100%',
          padding: padding ? `${layout.spacing.md} 0` : 0,
          margin: center ? '0 auto' : '0',
          maxWidth: maxWidth ? (layout.isMobile ? '100%' : '800px') : '100%'
        };
        
      case 'card':
        return {
          backgroundColor: 'var(--bg-surface)',
          borderRadius: layout.isMobile ? '0.5rem' : '0.75rem',
          padding: padding ? layout.spacing.md : 0,
          border: '1px solid var(--border-color)',
          boxShadow: layout.isMobile ? 'none' : '0 1px 3px rgba(0, 0, 0, 0.1)',
          margin: layout.spacing.sm,
          width: '100%'
        };
        
      case 'grid':
        return {
          ...baseStyles.grid,
          padding: padding ? layout.spacing.md : 0
        };
        
      case 'flex':
        return {
          ...baseStyles.flex,
          padding: padding ? layout.spacing.sm : 0
        };
        
      case 'modal':
        return {
          position: layout.useFullScreenModal ? 'fixed' : 'relative',
          top: layout.useFullScreenModal ? 0 : 'auto',
          left: layout.useFullScreenModal ? 0 : 'auto',
          right: layout.useFullScreenModal ? 0 : 'auto',
          bottom: layout.useFullScreenModal ? 0 : 'auto',
          width: layout.useFullScreenModal ? '100%' : 'auto',
          height: layout.useFullScreenModal ? '100%' : 'auto',
          maxWidth: layout.useFullScreenModal ? 'none' : '90vw',
          maxHeight: layout.useFullScreenModal ? 'none' : '90vh',
          backgroundColor: 'var(--bg-surface)',
          borderRadius: layout.useFullScreenModal ? 0 : '0.75rem',
          padding: padding ? layout.spacing.lg : 0,
          zIndex: 1000
        };
        
      case 'sidebar':
        return {
          width: layout.isMobile ? '100%' : '300px',
          height: layout.isMobile ? 'auto' : '100%',
          backgroundColor: 'var(--bg-surface)',
          borderRight: layout.isMobile ? 'none' : '1px solid var(--border-color)',
          borderBottom: layout.isMobile ? '1px solid var(--border-color)' : 'none',
          padding: padding ? layout.spacing.md : 0,
          overflow: 'auto'
        };
        
      case 'content':
        return {
          flex: 1,
          padding: padding ? layout.spacing.md : 0,
          overflow: 'auto',
          width: '100%'
        };
        
      default:
        return {
          width: '100%',
          ...style
        };
    }
  };

  // Generate responsive class names
  const getResponsiveClasses = () => {
    const baseClasses = [
      'responsive-container',
      `responsive-container-${variant}`,
      `responsive-container-${layout.layoutType}`
    ];

    // Add layout-specific classes
    if (layout.isMobile) baseClasses.push('mobile-layout');
    if (layout.isTablet) baseClasses.push('tablet-layout');
    if (layout.isDesktop) baseClasses.push('desktop-layout');
    if (layout.isTouch) baseClasses.push('touch-device');
    if (layout.hasHover) baseClasses.push('hover-device');
    if (layout.prefersReducedMotion) baseClasses.push('reduced-motion');

    return baseClasses.join(' ');
  };

  const combinedClassName = `${getResponsiveClasses()} ${className}`.trim();
  const combinedStyle = { ...getVariantStyles(), ...style };

  return (
    <Component
      className={combinedClassName}
      style={combinedStyle}
      {...props}
    >
      {children}
    </Component>
  );
}

/**
 * Specialized responsive container components
 */

// Page-level container
export function ResponsivePage({ children, ...props }) {
  return (
    <ResponsiveContainer variant="page" {...props}>
      {children}
    </ResponsiveContainer>
  );
}

// Section container
export function ResponsiveSection({ children, ...props }) {
  return (
    <ResponsiveContainer variant="section" {...props}>
      {children}
    </ResponsiveContainer>
  );
}

// Card container
export function ResponsiveCard({ children, ...props }) {
  return (
    <ResponsiveContainer variant="card" {...props}>
      {children}
    </ResponsiveContainer>
  );
}

// Grid container
export function ResponsiveGrid({ children, ...props }) {
  return (
    <ResponsiveContainer variant="grid" {...props}>
      {children}
    </ResponsiveContainer>
  );
}

// Flex container
export function ResponsiveFlex({ children, ...props }) {
  return (
    <ResponsiveContainer variant="flex" {...props}>
      {children}
    </ResponsiveContainer>
  );
}

// Modal container
export function ResponsiveModal({ children, ...props }) {
  return (
    <ResponsiveContainer variant="modal" {...props}>
      {children}
    </ResponsiveContainer>
  );
}

// Sidebar container
export function ResponsiveSidebar({ children, ...props }) {
  return (
    <ResponsiveContainer variant="sidebar" {...props}>
      {children}
    </ResponsiveContainer>
  );
}

// Content container
export function ResponsiveContent({ children, ...props }) {
  return (
    <ResponsiveContainer variant="content" {...props}>
      {children}
    </ResponsiveContainer>
  );
}

/**
 * Responsive utility components
 */

// Show/hide based on breakpoints
export function ShowOnMobile({ children }) {
  const { isMobile } = useResponsiveLayout();
  return isMobile ? children : null;
}

export function ShowOnTablet({ children }) {
  const { isTablet } = useResponsiveLayout();
  return isTablet ? children : null;
}

export function ShowOnDesktop({ children }) {
  const { isDesktop } = useResponsiveLayout();
  return isDesktop ? children : null;
}

export function HideOnMobile({ children }) {
  const { isMobile } = useResponsiveLayout();
  return !isMobile ? children : null;
}

export function HideOnTablet({ children }) {
  const { isTablet } = useResponsiveLayout();
  return !isTablet ? children : null;
}

export function HideOnDesktop({ children }) {
  const { isDesktop } = useResponsiveLayout();
  return !isDesktop ? children : null;
}

// Touch/hover conditional rendering
export function ShowOnTouch({ children }) {
  const { isTouch } = useResponsiveLayout();
  return isTouch ? children : null;
}

export function ShowOnHover({ children }) {
  const { hasHover } = useResponsiveLayout();
  return hasHover ? children : null;
}

/**
 * Responsive wrapper hook for existing components
 */
export function useResponsiveWrapper(componentName, options = {}) {
  const layout = useResponsiveLayout();
  
  return {
    // Wrapper props
    wrapperProps: {
      className: `responsive-wrapper responsive-wrapper-${componentName} ${layout.containerClass}`,
      'data-layout': layout.layoutType,
      'data-touch': layout.isTouch,
      'data-hover': layout.hasHover
    },
    
    // Layout information
    layout,
    
    // Component configuration
    shouldWrap: options.alwaysWrap || layout.isMobile,
    wrapperComponent: layout.isMobile ? 'div' : React.Fragment,
    
    // Responsive behavior
    behaviors: {
      stackOnMobile: layout.isMobile,
      showLabelsOnDesktop: layout.isDesktop,
      useBottomSheetOnMobile: layout.isMobile,
      preferContextMenuOnDesktop: layout.hasHover && layout.isDesktop
    }
  };
}