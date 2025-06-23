#!/bin/bash

# Build and deploy production version of AI Productivity App
# Frontend: Built static files for server NGINX
# Backend: Docker container

set -euo pipefail

# ------------------------------------------------------------
# Determine repository root and change into it so relative
# paths (frontend/, docker-compose.prod.yml, etc.) work no
# matter where the script is invoked from.
# ------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# ------------------------------------------------------------
# Load environment variables from .env if present so that
# deployment-specific settings can live alongside application
# configuration.  We export everything to make sure the rest
# of the script (and docker compose) can reference them.
# ------------------------------------------------------------
if [[ -f .env ]]; then
  echo "🔑 Loading variables from .env"
  # shellcheck disable=SC1091
  set -o allexport
  source .env
  set +o allexport
fi

# ------------------------------------------------------------
# Configuration with sane defaults that can be overriden via
# environment variables or the .env file loaded above.
# ------------------------------------------------------------

# Destination directory for the built SPA (static files).  Must be
# writable by the current user when DEPLOY_TO_WEB_ROOT=true.
WEB_ROOT="${WEB_ROOT:-${DEPLOY_WEB_ROOT:-/var/www/html}}"

# Flag – when "true" the built artefacts are copied into $WEB_ROOT.
DEPLOY_TO_WEB_ROOT="${DEPLOY_TO_WEB_ROOT:-false}"

# Nginx server-block path that should be patched + reloaded.
# Try to auto-detect a vhost that contains our server_name when the user
# hasn't configured one via env vars.

detect_nginx_config() {
  local search_dir="$1"
  local host="$2"
  # The grep may return no matches which exits with status 1; that's fine –
  # we ignore the exit code and return an empty string so that the caller can
  # decide how to proceed.
  grep -Rsl "server_name[[:space:]].*${host}" "$search_dir" 2>/dev/null || true |\
    head -n 1 || true
}

# 1) honour explicit env var, 2) auto-detect, 3) fallback default path

if [[ -n "${NGINX_CONFIG:-}" ]]; then
  : # use value from env / .env
else
  CANDIDATE=$(detect_nginx_config /etc/nginx/sites-enabled "lakefrontdigital.io")
  [[ -z "$CANDIDATE" ]] && CANDIDATE=$(detect_nginx_config /etc/nginx/sites-available "lakefrontdigital.io")
  NGINX_CONFIG="${CANDIDATE:-/etc/nginx/sites-enabled/lakefrontdigital.io.conf}"
fi

# ------------------------------------------------------------
# Determine WEB_ROOT automatically when still set to default
# ------------------------------------------------------------

if [[ "$WEB_ROOT" == "/var/www/html" && -f "$NGINX_CONFIG" ]]; then
  # try to read the first 'root' directive inside the matching server block
  DETECTED_ROOT=$(awk '/server_name[[:space:]].*lakefrontdigital.io/{f=1} f && /root[[:space:]].*;/{print $2; exit}' "$NGINX_CONFIG" | tr -d ';')
  if [[ -n "$DETECTED_ROOT" ]]; then
    WEB_ROOT="$DETECTED_ROOT"
  fi
fi

# Backup directory for previous web-root contents (optional).
BACKUP_DIR="${BACKUP_DIR:-/tmp/ai-app-backup-$(date +%Y%m%d-%H%M%S)}"

echo "🚀 Building production version..."

# Build frontend static files
echo "📦 Building frontend static files..."
# Attempt to build locally first because it's quicker when the environment
# supports child_process spawn.  If that fails (e.g. EPERM in restricted
# sandboxes) we fall back to a disposable Docker container so the build still
# succeeds automatically.

build_frontend() {
  echo "🔧 Running local npm build (frontend/)"
  (cd frontend && npm ci --silent && npm run build)
}

if build_frontend; then
  echo "✅ Frontend built locally"
else
  echo "⚠️  Local build failed – falling back to Dockerised node builder"
  docker run --rm \
    -v "$(pwd)/frontend":/app \
    -w /app \
    node:20-alpine \
    sh -ec "npm ci --silent && npm run build" || {
      echo "❌ Frontend build failed inside Docker as well. Aborting deployment" >&2
      exit 1
    }
  echo "✅ Frontend built inside Docker"
fi
echo "✅ Frontend built successfully"

# Stop any running backend containers
echo "🛑 Stopping existing backend containers..."
docker compose -f docker-compose.prod.yml down 2>/dev/null || echo "No existing containers to stop"

# Build production backend image
echo "🏗️  Building production backend image..."
docker compose -f docker-compose.prod.yml build --no-cache

# Start production backend container
echo "🚀 Starting production backend container..."
docker compose -f docker-compose.prod.yml up -d

# Wait for backend to be healthy
echo "⏳ Waiting for backend to be ready..."
sleep 10

# Check if backend is running
if docker compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    echo "✅ Production backend deployment successful!"

    # Show container status
    echo "🐳 Container Status:"
    docker compose -f docker-compose.prod.yml ps

    # Test backend endpoint
    echo ""
    echo "🔍 Testing backend endpoint..."
    if curl -s http://localhost:8000/health/ready > /dev/null; then
        echo "✅ Backend health check passed"
    else
        echo "⚠️  Backend health check failed"
    fi

    echo ""
    echo "📚 Deployment Summary:"
    echo "   🔧 Backend API: http://localhost:8000"
    echo "   📁 Frontend build: $(pwd)/frontend/dist"
    echo "   📊 Build size: $(du -sh frontend/dist 2>/dev/null || echo "N/A")"
    echo ""

    # Optional: Deploy to web directory if WEB_ROOT is accessible
    if [[ -w "$WEB_ROOT" && "$DEPLOY_TO_WEB_ROOT" == "true" ]]; then
        echo "📂 Deploying frontend to web root..."

        # Create backup of existing files
        if [[ -d "$WEB_ROOT" && "$(ls -A $WEB_ROOT 2>/dev/null)" ]]; then
            echo "💾 Creating backup at $BACKUP_DIR"
            mkdir -p "$BACKUP_DIR"
            cp -r "$WEB_ROOT"/* "$BACKUP_DIR/" 2>/dev/null || true
        fi

        # Deploy new files
        echo "📦 Copying files to $WEB_ROOT"
        cp -r frontend/dist/* "$WEB_ROOT/"
        echo "✅ Frontend deployed to web root"
        echo "💾 Backup available at: $BACKUP_DIR"
    else
        echo "📋 Manual deployment steps:"
        echo "   1. Copy frontend/dist/* to your web server directory"
        echo "   2. Update NGINX configuration to handle API routes"
        echo ""
        echo "💡 To auto-deploy to web root, set:"
        echo "   export WEB_ROOT=/path/to/your/web/root"
        echo "   export DEPLOY_TO_WEB_ROOT=true"
        echo "   Then run this script again"
    fi

    # Switch nginx to production mode
    echo "🔧 Configuring NGINX for production..."
    if [[ -f "$NGINX_CONFIG" ]]; then
        # Create backup of current nginx config
        sudo cp "$NGINX_CONFIG" "${NGINX_CONFIG}.backup.$(date +%Y%m%d-%H%M%S)"
        
        # Switch from Vite dev server to static files
        sudo sed -i 's|proxy_pass http://localhost:5173;|try_files $uri $uri/ /index.html;|g' "$NGINX_CONFIG"
        
        # Enable static asset caching
        sudo sed -i 's|# location ~\* \\.\(png\|jpg\|jpeg\|gif\|ico\|svg\|woff\|woff2\|ttf\|eot\)\$ {|location ~* \\.(png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {|g' "$NGINX_CONFIG"
        sudo sed -i 's|#     expires 1y;|    expires 1y;|g' "$NGINX_CONFIG"
        sudo sed -i 's|#     add_header Cache-Control "public, immutable";|    add_header Cache-Control "public, immutable";|g' "$NGINX_CONFIG"
        sudo sed -i 's|#     try_files \$uri =404;|    try_files $uri =404;|g' "$NGINX_CONFIG"
        sudo sed -i 's|# }|}|g' "$NGINX_CONFIG"
        
        # Reload nginx
        if sudo nginx -t; then
            sudo systemctl reload nginx
            echo "✅ NGINX configured for production mode"
        else
            echo "❌ NGINX configuration error - restoring backup"
            sudo cp "${NGINX_CONFIG}.backup.$(date +%Y%m%d-%H%M%S)" "$NGINX_CONFIG"
            exit 1
        fi
    else
        echo "⚠️  NGINX config not found at $NGINX_CONFIG"
    fi

    echo ""
    echo "🔧 NGINX Configuration Notes:"
    echo "   • Backend API runs on: http://localhost:8000"
    echo "   • API routes proxy to: http://localhost:8000"
    echo "   • Static files served from web root"
    echo "   • Production mode enabled with asset caching"

else
    echo "❌ Backend deployment failed"
    docker compose -f docker-compose.prod.yml logs
    exit 1
fi
