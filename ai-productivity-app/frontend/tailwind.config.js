/* Minimal Tailwind CSS v4 configuration
 *
 * In v4, theme configuration is done via CSS variables in @theme.
 * This file is mainly for plugins that require JavaScript configuration.
 */

import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);

// Attempt to load optional plugins for backward compatibility
function loadPlugin(pkg) {
  try {
    return require(pkg);
  } catch {
    return () => ({ name: `noop-${pkg}` });
  }
}

const formsPlugin = loadPlugin('@tailwindcss/forms');
const typographyPlugin = loadPlugin('@tailwindcss/typography');

export default {
  plugins: [
    formsPlugin,
    typographyPlugin,
  ],
};
