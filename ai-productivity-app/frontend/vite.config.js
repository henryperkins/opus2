// Vite configuration for React development
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
    plugins: [react()],
    server: {
        host: '0.0.0.0',
        port: 5173,
        strictPort: true,
        proxy: {
            // Forward API calls to the backend container without rewriting the
            // path so that the "/api" prefix expected by FastAPI remains
            // intact (e.g. "/api/auth/login" → "http://backend:8000/api/auth/login").
            '/api': {
                target: 'http://backend:8000',
                changeOrigin: true,
                // Keep the original path – removing the prefix breaks auth
                // endpoints that are mounted under "/api" inside FastAPI.
                // eslint-disable-next-line no-unused-vars
                rewrite: (path) => path, // leave untouched
            },
        }
    },
    build: {
        outDir: 'dist',
        sourcemap: true,
        minify: 'esbuild',
        target: 'esnext'
    }
})
