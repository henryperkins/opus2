// Debug script to check dark mode configuration
// Run this in the browser console

(() => {
  console.log('=== Dark Mode Debug ===');
  
  // 1. Check HTML classes
  const htmlClasses = document.documentElement.classList;
  console.log('HTML classes:', Array.from(htmlClasses));
  
  // 2. Check if dark mode styles are loaded
  const testEl = document.createElement('div');
  testEl.className = 'dark:bg-gray-900';
  document.body.appendChild(testEl);
  
  // First check without dark class
  const lightStyle = window.getComputedStyle(testEl).backgroundColor;
  console.log('Without .dark class:', lightStyle);
  
  // Add dark class and check again
  document.documentElement.classList.add('dark');
  const darkStyle = window.getComputedStyle(testEl).backgroundColor;
  console.log('With .dark class:', darkStyle);
  
  // Clean up
  document.body.removeChild(testEl);
  
  // 3. Check specific elements
  const body = document.body;
  console.log('Body computed styles:', {
    backgroundColor: window.getComputedStyle(body).backgroundColor,
    color: window.getComputedStyle(body).color
  });
  
  // 4. Check if Tailwind CSS is loaded
  const styleSheets = Array.from(document.styleSheets);
  const hasTailwind = styleSheets.some(sheet => {
    try {
      return sheet.href?.includes('tailwind') || 
             Array.from(sheet.cssRules || []).some(rule => 
               rule.cssText?.includes('--tw-') || 
               rule.selectorText?.includes('.dark')
             );
    } catch (e) {
      return false;
    }
  });
  console.log('Tailwind CSS loaded:', hasTailwind);
  
  // 5. Test a simple dark mode toggle
  console.log('\n--- Testing toggle ---');
  const currentDark = document.documentElement.classList.contains('dark');
  document.documentElement.classList.toggle('dark');
  console.log(`Toggled from ${currentDark ? 'dark' : 'light'} to ${!currentDark ? 'dark' : 'light'}`);
  
  // Check body again
  console.log('Body after toggle:', {
    backgroundColor: window.getComputedStyle(body).backgroundColor,
    color: window.getComputedStyle(body).color
  });
  
  // 6. Look for dark mode CSS rules
  let darkRulesFound = 0;
  styleSheets.forEach(sheet => {
    try {
      const rules = Array.from(sheet.cssRules || []);
      rules.forEach(rule => {
        if (rule.selectorText?.includes('.dark')) {
          darkRulesFound++;
          if (darkRulesFound <= 5) {
            console.log('Dark rule found:', rule.selectorText);
          }
        }
      });
    } catch (e) {
      // Ignore cross-origin stylesheet errors
    }
  });
  console.log(`Total dark mode rules found: ${darkRulesFound}`);
  
  console.log('\n=== End Debug ===');
})();
