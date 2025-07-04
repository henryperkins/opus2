// Quick test to verify dark mode is working
// Run this in the browser console after restarting the dev server

(() => {
  console.log('=== Theme Toggle Test ===');
  
  // Remove dark class
  document.documentElement.classList.remove('dark');
  const lightBg = window.getComputedStyle(document.body).backgroundColor;
  console.log('Light mode background:', lightBg);
  
  // Add dark class
  document.documentElement.classList.add('dark');
  const darkBg = window.getComputedStyle(document.body).backgroundColor;
  console.log('Dark mode background:', darkBg);
  
  // Check if they're different
  if (lightBg !== darkBg) {
    console.log('✅ SUCCESS: Theme switching is working!');
    console.log('Light:', lightBg, '| Dark:', darkBg);
  } else {
    console.log('❌ FAILED: Theme is not switching');
    console.log('Both modes show:', lightBg);
  }
  
  // Test a few more elements
  const testElements = [
    { selector: '.bg-white', name: 'White backgrounds' },
    { selector: '.text-gray-900', name: 'Dark text' },
    { selector: '.border-gray-200', name: 'Light borders' }
  ];
  
  console.log('\n--- Element Tests ---');
  testElements.forEach(({ selector, name }) => {
    const el = document.querySelector(selector);
    if (el) {
      document.documentElement.classList.remove('dark');
      const light = window.getComputedStyle(el).backgroundColor || window.getComputedStyle(el).color || window.getComputedStyle(el).borderColor;
      
      document.documentElement.classList.add('dark');
      const dark = window.getComputedStyle(el).backgroundColor || window.getComputedStyle(el).color || window.getComputedStyle(el).borderColor;
      
      console.log(`${name}: ${light !== dark ? '✅' : '❌'} (Light: ${light} | Dark: ${dark})`);
    }
  });
  
  console.log('\n=== End Test ===');
})();
