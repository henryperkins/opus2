#!/bin/bash

# Build and deploy production version of AI Productivity App
# Frontend: Built static files for server NGINX
# Backend: Docker container

set -e

# Configuration - adjust these paths for your server setup
WEB_ROOT="${WEB_ROOT:-/var/www/html}"
BACKUP_DIR="${BACKUP_DIR:-/tmp/ai-app-backup-$(date +%Y%m%d-%H%M%S)}"

echo "🚀 Building production version..."

# Build frontend static files
echo "📦 Building frontend static files..."
cd frontend
npm run build
cd ..
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
    NGINX_CONFIG="/etc/nginx/sites-enabled/lakefrontdigital.io.conf"
    
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
