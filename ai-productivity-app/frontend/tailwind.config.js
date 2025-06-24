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
  // Theme configuration is now in CSS via @theme
  // Dark mode uses prefers-color-scheme by default in v4
  plugins: [
    // Add plugins as needed
  ],
};
