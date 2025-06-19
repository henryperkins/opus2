# Development Dockerfile for frontend with Vite dev server and proxy support

FROM node:20-alpine

WORKDIR /app

# Install dependencies first for better layer caching
COPY package*.json ./
# Set NODE_ENV=development to install devDependencies
RUN NODE_ENV=development npm ci

# Install wget for healthcheck probe
RUN apk add --no-cache wget

# Copy source code
COPY . .

# Expose the default Vite dev server port
EXPOSE 5173

# Health check for the development server
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:5173/ || exit 1

# Run Vite dev server with proxy support
CMD ["npm", "run", "dev"]
