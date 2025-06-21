import { useState, useEffect } from 'react';

/**
 * Custom hook for responsive design and media query handling
 * Returns current breakpoint and helper functions for responsive behavior
 */
export const useMediaQuery = () => {
    const [windowSize, setWindowSize] = useState({
        width: typeof window !== 'undefined' ? window.innerWidth : 0,
        height: typeof window !== 'undefined' ? window.innerHeight : 0,
    });

    const [breakpoint, setBreakpoint] = useState('desktop');

    useEffect(() => {
        const handleResize = () => {
            const width = window.innerWidth;
            const height = window.innerHeight;

            setWindowSize({ width, height });

            // Tailwind CSS breakpoints
            if (width < 640) {
                setBreakpoint('mobile');
            } else if (width < 768) {
                setBreakpoint('sm');
            } else if (width < 1024) {
                setBreakpoint('tablet');
            } else if (width < 1280) {
                setBreakpoint('desktop');
            } else {
                setBreakpoint('xl');
            }
        };

        // Set initial values
        handleResize();

        // Add event listener
        window.addEventListener('resize', handleResize);

        // Cleanup
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    const isMobile = breakpoint === 'mobile';
    const isTablet = breakpoint === 'tablet' || breakpoint === 'sm';
    const isDesktop = breakpoint === 'desktop' || breakpoint === 'xl';
    const isTouchDevice = isMobile || isTablet;

    return {
        windowSize,
        breakpoint,
        isMobile,
        isTablet,
        isDesktop,
        isTouchDevice,
        // Helper functions
        matchesQuery: (query) => {
            if (typeof window === 'undefined') return false;
            return window.matchMedia(query).matches;
        }
    };
};

/**
 * Hook for specific breakpoint detection
 */
export const useBreakpoint = (breakpoint) => {
    const { matchesQuery } = useMediaQuery();

    const queries = {
        sm: '(min-width: 640px)',
        md: '(min-width: 768px)',
        lg: '(min-width: 1024px)',
        xl: '(min-width: 1280px)',
        '2xl': '(min-width: 1536px)',
    };

    return matchesQuery(queries[breakpoint] || breakpoint);
};

export default useMediaQuery;
