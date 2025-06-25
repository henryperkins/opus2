/* eslint-env node */
// Vite configuration for React / Tailwind project
import { defineConfig, splitVendorChunkPlugin } from 'vite';
import react from '@vitejs/plugin-react';
import { visualizer } from 'rollup-plugin-visualizer';
import tailwindcss from '@tailwindcss/vite';
import tsconfigPaths from 'vite-tsconfig-paths';
import svgr from 'vite-plugin-svgr';
// Monaco Editor plugin removed - using direct integration
import inject from '@rollup/plugin-inject';

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
    // Monaco Editor configured via @monaco-editor/react directly
    inject({ Buffer: ['buffer', 'Buffer'] }),
    splitVendorChunkPlugin(), // automatic vendor splitter
    visualizer({
      filename: 'stats.html',
      template: 'treemap',
      gzipSize: true,
    }),
  ],

  // Ensure heavyweight libraries needed at runtime are eagerly pre-bundled so
  // Vite’s dev server doesn’t need to stream them on-demand (which caused
  // intermittent `ERR_CONNECTION_CLOSED` errors when the remote reverse proxy
  // reset long-running connections).
  optimizeDeps: {
    include: [
      'react-syntax-highlighter',
      'react-syntax-highlighter/dist/esm/languages/prism/javascript',
      'react-syntax-highlighter/dist/esm/languages/prism/typescript',
      'react-syntax-highlighter/dist/esm/languages/prism/python',
      'react-syntax-highlighter/dist/esm/languages/prism/markup',
      'react-syntax-highlighter/dist/esm/languages/prism/json',
      'react-syntax-highlighter/dist/esm/languages/prism/bash',
      'monaco-editor',
      'monacopilot',
      'buffer',
    ],
  },

  /**
   * Provide a stub for the optional `@sentry/react` dependency so that
   * production builds succeed even when the package is not installed.
   *
   * The real SDK is only required when a Sentry DSN is supplied; for all other
   * environments we alias it to a tiny no-op implementation (see
   * `src/sentryStub.js`).
   */
  resolve: {
    alias: {
      '@sentry/react': '/src/sentryStub.js',
      buffer: 'buffer',
    },
  },

  define: {
    global: 'globalThis',
  },

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
    // HMR configuration for reverse proxy
    hmr: {
      port: 5173,
      host: 'lakefrontdigital.io',
      clientPort: 443, // Use HTTPS port for client connections
      protocol: 'wss', // Use secure WebSocket
    },
    // Enable proxy for development with WebSocket support
    proxy: {
      '/api': {
        target: backendTarget,
        changeOrigin: true,
        ws: true, // Enable WebSocket support for all /api routes including /api/chat/ws
        // Don't rewrite path - backend expects /api prefix
      }
    }
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

          if (id.includes('@monaco-editor') || id.includes('monaco-editor')) return 'monaco';
          if (id.includes('monacopilot')) return 'monacopilot';
          if (/react-syntax-highlighter/.test(id)) return 'syntax';
          if (/[\\/](d3|d3-.*?)[\\/]/.test(id)) return 'd3';
          if (/react|react-dom|scheduler/.test(id)) return 'react';
          return 'vendor';
        },
      },
    },
  },
});
