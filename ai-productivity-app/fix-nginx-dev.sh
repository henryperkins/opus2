#!/bin/bash

# Quick Script to Apply NGINX Development Configuration
# This script will help you apply the necessary changes to your NGINX config

echo "=== NGINX Development Configuration Fix ==="
echo ""
echo "This script will help you fix the NGINX configuration for Vite development."
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script needs to be run as root (or with sudo) to modify NGINX configuration."
   echo "Please run: sudo $0"
   exit 1
fi

# Backup the current config
echo "1. Creating backup of current NGINX configuration..."
cp /etc/nginx/sites-available/lakefrontdigital.io /etc/nginx/sites-available/lakefrontdigital.io.backup.$(date +%Y%m%d_%H%M%S)
echo "   ✓ Backup created"

# Check if the static asset caching rule exists
echo ""
echo "2. Checking for static asset caching rule..."
if grep -q "location ~\* \\\\\.\\(js\\|css" /etc/nginx/sites-available/lakefrontdigital.io; then
    echo "   ⚠️  Found static asset caching rule - this needs to be commented out for development"
    echo "   Please edit /etc/nginx/sites-available/lakefrontdigital.io and comment out the block:"
    echo "   location ~* \\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {"
    echo ""
else
    echo "   ✓ No static asset caching rule found"
fi

# Check if Vite is running
echo ""
echo "3. Checking if Vite development server is running..."
if curl -s -I http://localhost:5173 > /dev/null; then
    echo "   ✓ Vite is running on localhost:5173"
else
    echo "   ⚠️  Vite is not running. Please start it with:"
    echo "   cd /home/azureuser/opus2/ai-productivity-app/frontend && npm run dev"
fi

# Check if backend is running
echo ""
echo "4. Checking if backend is running..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "   ✓ Backend is running on localhost:8000"
else
    echo "   ⚠️  Backend is not running. Please start it."
fi

echo ""
echo "=== Next Steps ==="
echo "1. Edit your NGINX configuration: nano /etc/nginx/sites-available/lakefrontdigital.io"
echo "2. Comment out the static asset caching rule (see NGINX_DEVELOPMENT_FIX.md for details)"
echo "3. Replace the AI-Productivity-App routes section with the configuration from nginx-ai-app-config.conf"
echo "4. Test the configuration: nginx -t"
echo "5. Restart NGINX: systemctl restart nginx"
echo ""
echo "For detailed instructions, see: NGINX_DEVELOPMENT_FIX.md"
