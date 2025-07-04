@echo off
REM Clean up theme test files after confirming dark mode works

echo Cleaning up theme test files...

REM Remove test CSS files
del /f src\styles\test-dark.css 2>nul
del /f src\styles\dark-mode-override.css 2>nul
del /f src\styles\dark-mode-fix.css 2>nul

REM Remove test components
del /f src\components\ThemeTest.jsx 2>nul
del /f src\components\ThemeDebug.jsx 2>nul
del /f src\components\MinimalThemeTest.jsx 2>nul
del /f src\components\DarkModeTest.jsx 2>nul

REM Remove test page
del /f src\pages\ThemeTestPage.jsx 2>nul

REM Remove test scripts
del /f verify-theme.js 2>nul
del /f debug-dark-mode.js 2>nul
del /f test-theme-working.js 2>nul

REM Remove shell script
del /f cleanup-theme-tests.sh 2>nul

echo.
echo Clean up complete!
echo.
echo The following files are still in use:
echo - src\styles\dark-mode-emergency.css (KEEP THIS - it makes dark mode work)
echo - src\hooks\useTheme.jsx (your theme hook)
echo - src\components\common\ThemeToggle.jsx (the toggle button)
echo.
echo Don't forget to remove the test route from router.jsx if you added it!
pause
