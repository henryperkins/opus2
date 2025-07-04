# Theme Switching Debug Guide

## What We've Fixed

1. **Removed race conditions** in the theme synchronization logic
2. **Added comprehensive logging** to track theme state changes
3. **Created a debug component** that shows real-time theme state
4. **Simplified the theme resolution logic** to be more predictable

## How to Test

1. **Start the development server**
   ```bash
   npm run dev
   ```

2. **Open browser console** (F12) to see theme debug logs

3. **Look for the Theme Debug panel** in the bottom-right corner showing:
   - Hook theme state
   - Zustand preference
   - Current DOM state

4. **Click the theme toggle** in the header and watch:
   - Console logs showing the theme change flow
   - Debug panel updating in real-time
   - UI colors switching

## Expected Console Output

When clicking the theme toggle, you should see:
```
[useTheme] Toggle theme from light to dark
[useTheme] setTheme called with: dark
[useTheme] Resolved theme: dark
[useTheme] Applying theme to DOM: dark
[useTheme] DOM updated - classes: dark
[useTheme] Persisting preference: dark
[useTheme] Preferences changed: dark
```

## If Theme Still Doesn't Switch

1. **Check the browser console** for any errors
2. **Check localStorage**:
   ```javascript
   // In browser console:
   localStorage.getItem('ai-productivity-auth')
   localStorage.getItem('theme')
   ```

3. **Manually test theme application**:
   ```javascript
   // In browser console:
   document.documentElement.classList.remove('light', 'dark');
   document.documentElement.classList.add('dark');
   ```

4. **Check if Tailwind dark mode is working**:
   ```javascript
   // Create a test element
   const test = document.createElement('div');
   test.className = 'bg-white dark:bg-gray-900';
   document.body.appendChild(test);
   console.log(window.getComputedStyle(test).backgroundColor);
   document.body.removeChild(test);
   ```

## Debug Component Controls

The debug panel in the bottom-right has three buttons:
- **Toggle**: Same as header toggle
- **Light**: Force light theme
- **Dark**: Force dark theme

## Common Issues

1. **Zustand store not updating**: Check if the auth store is properly initialized
2. **DOM classes not applying**: Verify Tailwind CSS is configured for class-based dark mode
3. **Styles not changing**: Ensure CSS is properly loaded and dark: variants are compiled

## Next Steps if Still Broken

1. **Clear all storage**:
   ```javascript
   localStorage.clear();
   location.reload();
   ```

2. **Check theme in different pages**: Navigate to `/theme-test` for isolated testing

3. **Verify the build**: 
   ```bash
   npm run build
   npm run preview
   ```
   Test in production mode to rule out dev server issues
