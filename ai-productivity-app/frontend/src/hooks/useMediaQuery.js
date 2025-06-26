import { useState, useEffect } from 'react';

/**
 * Simplified media query hook - CSS-first responsive design
 * Eliminates complex JavaScript layout calculations
 */
export const useMediaQuery = () => {
    const [isMobile, setIsMobile] = useState(false);
    const [isTablet, setIsTablet] = useState(false);
    const [isDesktop, setIsDesktop] = useState(true);

    useEffect(() => {
        const updateBreakpoints = () => {
            const mobile = window.matchMedia('(max-width: 768px)').matches;
            const tablet = window.matchMedia('(min-width: 769px) and (max-width: 1024px)').matches;
            const desktop = window.matchMedia('(min-width: 1025px)').matches;

            setIsMobile(mobile);
            setIsTablet(tablet);
            setIsDesktop(desktop);
        };

        // Set initial values
        updateBreakpoints();

        // Add event listener
        window.addEventListener('resize', updateBreakpoints);

        // Cleanup
        return () => window.removeEventListener('resize', updateBreakpoints);
    }, []);

    return {
        isMobile,
        isTablet,
        isDesktop,
        // Helper function for custom queries
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
