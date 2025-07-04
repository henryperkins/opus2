# Theme Switching - Emergency Fix

Since the standard Tailwind v4 dark mode isn't working, here's a quick fix to get your theme switching working immediately:

## Quick Fix (Do This Now)

### 1. Create Override CSS

Create a new file `src/styles/dark-mode-emergency.css`:

```css
/* Emergency dark mode styles */
html.dark {
  color-scheme: dark;
}

html.dark body {
  background-color: #111827 !important;
  color: #f9fafb !important;
}

/* Override all light backgrounds in dark mode */
html.dark .bg-white { background-color: #1f2937 !important; }
html.dark .bg-gray-50 { background-color: #111827 !important; }
html.dark .bg-gray-100 { background-color: #1f2937 !important; }
html.dark .bg-gray-200 { background-color: #374151 !important; }

/* Override text colors */
html.dark .text-gray-900 { color: #f9fafb !important; }
html.dark .text-gray-800 { color: #e5e7eb !important; }
html.dark .text-gray-700 { color: #d1d5db !important; }
html.dark .text-gray-600 { color: #9ca3af !important; }

/* Override borders */
html.dark .border-gray-200 { border-color: #4b5563 !important; }
html.dark .border-gray-300 { border-color: #374151 !important; }

/* Fix specific components */
html.dark .chat-layout { background-color: #111827 !important; }
html.dark .btn-primary { background: #2563eb !important; }
html.dark .btn-secondary { 
  background-color: #374151 !important;
  color: #e5e7eb !important;
  border-color: #4b5563 !important;
}
```

### 2. Import in main.jsx

Add this import:
```javascript
import './styles/dark-mode-emergency.css';
```

### 3. Test It

The theme should now switch immediately when you toggle.

## Why This Works

This bypasses Tailwind's dark mode system entirely and uses direct CSS selectors with `!important` to force the styles to apply when the `dark` class is present.

## Proper Fix (Do Later)

The real issue is likely one of:

1. **Tailwind v4 configuration**: The `@variant dark` syntax might not be working as expected
2. **Build process**: Vite might not be processing the Tailwind v4 dark utilities correctly
3. **CSS ordering**: Dark mode styles might be getting overridden

To properly debug:

1. Check the generated CSS in DevTools to see if `.dark` selectors exist
2. Look for any CSS that might be overriding the dark styles
3. Consider downgrading to Tailwind v3 which has more stable dark mode support

But for now, the emergency CSS will get your theme switching working!
