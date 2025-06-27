/* Tailwind CSS v4 - Minimal Configuration
 * 
 * Most theme configuration is now done in CSS via @theme.
 * This file is primarily for content paths and plugins.
 */

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}',
  ],

  // -------------------------------------------------------------------------
  // Dark mode configuration
  // -------------------------------------------------------------------------
  // Tailwind CSS v4 defaults to using the `prefers-color-scheme` media query
  // for the `dark:` variant.  However, the application provides an explicit
  // theme toggle (see `useTheme` + `ThemeToggle`), which relies on adding a
  // `dark` **class** to the <html> element.  To make those utilities work we
  // must opt-in to class-based dark mode.
  //
  // Ref: https://tailwindcss.com/docs/dark-mode#class-strategy
  // -------------------------------------------------------------------------
  darkMode: 'class',

  // -------------------------------------------------------------------------
  // Plugins – keep minimal, extend as required.
  // -------------------------------------------------------------------------
  plugins: [
    // Add Tailwind plugins here
  ],
};
