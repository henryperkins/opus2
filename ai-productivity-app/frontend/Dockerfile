# Lightweight image that simply serves the *already built* static frontend.
#
# The original Dockerfile started a Vite dev server (`npm run dev`) which relies
# on *esbuild* spawning a native child process. In certain restricted
# environments (including the execution sandbox used for automated tests) that
# `spawn` call fails with `EPERM`, preventing the container from starting.  To
# avoid this limitation we now skip the tool-chain entirely and serve the
# checked-in `dist/` folder with a tiny Node HTTP server implemented in
# `server.js`.

FROM node:20-alpine

# -----------------------------------------------------------------------------
# Runtime setup – we do *not* install any npm dependencies because the static
# server only uses Node core modules.  We still copy package.json so that the
# `npm start` script is available.
# -----------------------------------------------------------------------------

WORKDIR /app

# Copy only the files needed to run the server first (for better layer caching)
COPY package*.json ./

# Copy the rest of the application, including the pre-built assets in `dist/`.
COPY . .

# The HTTP server listens on the same default port that Vite uses so that URLs
# referenced throughout the project documentation remain unchanged.
EXPOSE 5173

# Health check – consider the container healthy when the root document returns
# HTTP 200.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD node -e "import('node:http').then(http => http.get('http://localhost:5173', res => process.exit(res.statusCode === 200 ? 0 : 1)))"

# Start the static file server.
CMD ["npm", "start"]
