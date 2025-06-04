// Vite configuration for React development
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// ---------------------------------------------------------------------------
// Helper: determine backend URL for the dev-server proxy.
// Priority (first match wins):
//   1. Explicit env var VITE_API_URL   → works for Docker where we set
//      "http://backend:8000".
//   2. BACKEND_URL                     → gives local developers flexibility
//   3. Fallback                        → http://localhost:8000 (no Docker)
// ---------------------------------------------------------------------------

const backendTarget =
  process.env.VITE_API_URL ||
  process.env.BACKEND_URL ||
  'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: backendTarget,
        changeOrigin: true,
        rewrite: (path) => path, // keep original path
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    minify: 'esbuild',
    target: 'esnext',
  },
});
