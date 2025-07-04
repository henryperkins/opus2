#!/bin/bash
# Clean up theme test files after confirming dark mode works

echo "Cleaning up theme test files..."

# Remove test CSS files
rm -f src/styles/test-dark.css
rm -f src/styles/dark-mode-override.css
rm -f src/styles/dark-mode-fix.css

# Remove test components
rm -f src/components/ThemeTest.jsx
rm -f src/components/ThemeDebug.jsx
rm -f src/components/MinimalThemeTest.jsx
rm -f src/components/DarkModeTest.jsx

# Remove test page
rm -f src/pages/ThemeTestPage.jsx

# Remove test scripts
rm -f verify-theme.js
rm -f debug-dark-mode.js
rm -f test-theme-working.js

# Remove documentation files (optional - you may want to keep these)
# rm -f THEME_*.md

echo "✅ Clean up complete!"
echo ""
echo "The following files are still in use:"
echo "- src/styles/dark-mode-emergency.css (KEEP THIS - it makes dark mode work)"
echo "- src/hooks/useTheme.jsx (your theme hook)"
echo "- src/components/common/ThemeToggle.jsx (the toggle button)"
echo ""
echo "Don't forget to remove the test route from router.jsx if you added it!"
