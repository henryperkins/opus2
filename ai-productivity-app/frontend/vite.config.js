/* eslint-env node */
// Vite configuration for React / Tailwind project
import { defineConfig, splitVendorChunkPlugin } from 'vite';
import react from '@vitejs/plugin-react';
import { visualizer } from 'rollup-plugin-visualizer';
import tailwindcss from '@tailwindcss/vite';
import tsconfigPaths from 'vite-tsconfig-paths';
import svgr from 'vite-plugin-svgr';

// ---------------------------------------------------------------------------
// Helper: decide proxy target (Docker-aware)
const backendTarget =
  // eslint-disable-next-line no-undef
  process.env.NODE_ENV === 'development' && process.env.DOCKER_ENV === 'true'
    ? 'http://backend:8000' // Docker service name
    : // eslint-disable-next-line no-undef
    process.env.VITE_API_URL ||
    // eslint-disable-next-line no-undef
    process.env.BACKEND_URL ||
    'http://localhost:8000';

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    tsconfigPaths(),
    svgr(),
    splitVendorChunkPlugin(),                // automatic vendor splitter
    visualizer({
      filename: 'stats.html',
      template: 'treemap',
      gzipSize: true,
    }),
  ],

  // Base URL for production
  base: '/',

  // Vitest
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
  },

  // Dev-server
  server: {
    host: '0.0.0.0',
    port: parseInt(process.env.PORT) || 5173, // eslint-disable-line no-undef
    strictPort: false,
    allowedHosts: ['localhost', '127.0.0.1', 'lakefrontdigital.io'],
    // Only proxy when using localhost backend
    ...(backendTarget.includes('localhost') && {
      proxy: {
        '/api': {
          target: backendTarget,
          changeOrigin: true,
          ws: true,
          rewrite: (p) => p,
        },
      },
    }),
  },

  // Production build
  build: {
    outDir: 'dist',
    sourcemap: true,
    minify: 'esbuild',
    target: 'esnext',
    /**
     * After deliberate chunking we allow 1.5 MB as the
     * *warning* threshold so CI stays green.
     */
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        /**
         * Put heavyweight third-party libs in their own
         * cache-friendly files.
         */
        manualChunks(id) {
          if (!id.includes('node_modules')) return;

          if (id.includes('@monaco-editor')) return 'monaco';
          if (/react-syntax-highlighter/.test(id)) return 'syntax';
          if (/[\\/](d3|d3-.*?)[\\/]/.test(id)) return 'd3';
          if (/react|react-dom|scheduler/.test(id)) return 'react';
          return 'vendor';
        },
      },
    },
  },
});
