// Quick verification script for theme switching
// Run this in the browser console on any page with theme switching

(() => {
  console.log('=== Theme System Verification ===');
  
  // Check DOM state
  const root = document.documentElement;
  const hasLightClass = root.classList.contains('light');
  const hasDarkClass = root.classList.contains('dark');
  
  console.log('DOM Classes:', {
    light: hasLightClass,
    dark: hasDarkClass,
    allClasses: root.classList.toString()
  });
  
  // Check localStorage
  const zustandData = localStorage.getItem('ai-productivity-auth');
  let zustandTheme = null;
  
  if (zustandData) {
    try {
      const parsed = JSON.parse(zustandData);
      zustandTheme = parsed?.state?.preferences?.theme;
    } catch (e) {
      console.error('Failed to parse Zustand data:', e);
    }
  }
  
  const legacyTheme = localStorage.getItem('theme');
  
  console.log('Storage:', {
    zustandTheme,
    legacyTheme
  });
  
  // Check meta theme-color
  const metaTheme = document.querySelector('meta[name="theme-color"]');
  console.log('Meta theme-color:', metaTheme?.content || 'not found');
  
  // Check computed styles
  const bodyBg = window.getComputedStyle(document.body).backgroundColor;
  const bodyColor = window.getComputedStyle(document.body).color;
  
  console.log('Computed Styles:', {
    backgroundColor: bodyBg,
    textColor: bodyColor
  });
  
  // Verify Tailwind dark mode
  const testEl = document.createElement('div');
  testEl.className = 'bg-white dark:bg-gray-900';
  document.body.appendChild(testEl);
  const testBg = window.getComputedStyle(testEl).backgroundColor;
  document.body.removeChild(testEl);
  
  console.log('Tailwind dark mode test:', {
    testBackground: testBg,
    isDarkModeWorking: testBg === 'rgb(17, 24, 39)' || testBg === 'rgb(255, 255, 255)'
  });
  
  // Summary
  console.log('\n=== Summary ===');
  if (hasLightClass && !hasDarkClass) {
    console.log('✅ Light mode is active');
  } else if (hasDarkClass && !hasLightClass) {
    console.log('✅ Dark mode is active');
  } else {
    console.log('❌ Theme state is invalid!');
  }
  
  console.log('\nTo test theme switching:');
  console.log('1. Click the theme toggle button');
  console.log('2. Run this script again to verify the change');
  console.log('3. Check that UI colors have updated');
})();
