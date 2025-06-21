# NGINX Development Configuration Fix

## Problem
The Vite development server is not working properly behind the NGINX reverse proxy, causing:
- 404 errors for React assets (react.js, react-dom, etc.)
- WebSocket connection failures for Hot Module Replacement (HMR)
- Directory index forbidden errors
- WebSocket trying to connect to `wss://localhost/?token=...` instead of proper HMR endpoints

## Solution
You need to modify your main NGINX configuration to properly proxy all requests to the Vite development server and handle WebSocket connections correctly.

## Root Cause
The issue is that your NGINX config has a static asset caching rule:
```nginx
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
    try_files $uri =404;
}
```
This rule intercepts JavaScript and CSS requests and tries to serve them as static files, but they don't exist in your document root - they need to be served by the Vite dev server.

## Changes Required

### 1. Comment Out Static Asset Caching (CRITICAL)

In your main NGINX config (`/etc/nginx/sites-available/lakefrontdigital.io` or similar), **comment out** this block during development:

```nginx
# COMMENT OUT THIS BLOCK FOR DEVELOPMENT:
# location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
#     expires 1y;
#     add_header Cache-Control "public, immutable";
#     try_files $uri =404;
# }
```

### 2. Replace the AI-Productivity-App Routes Section

Replace the entire AI-Productivity-App routes section in your main NGINX config with:

```nginx
################################################################
# ----------  AI-Productivity-App routes  ----------
################################################################

# Vite HMR WebSocket connections (critical for development)
location /__vite_ping {
    proxy_pass http://localhost:5173;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
}

# Vite WebSocket for HMR
location /__vite_hmr {
    proxy_pass http://localhost:5173;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Vite assets and development files
location ~ ^/(src/|node_modules/|@|__vite) {
    proxy_pass http://localhost:5173;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

## FastAPI backend
location ^~ /api/ {
    proxy_pass              http://localhost:8000;
    proxy_http_version      1.1;

    proxy_set_header Host               $host;
    proxy_set_header X-Real-IP          $remote_addr;
    proxy_set_header X-Forwarded-For    $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto  $scheme;
    proxy_set_header X-Forwarded-Host   $host;
    proxy_set_header X-Forwarded-Server $host;

    proxy_set_header Upgrade            $http_upgrade;
    proxy_set_header Connection         "upgrade";

    proxy_connect_timeout 60s;
    proxy_send_timeout    60s;
    proxy_read_timeout    60s;

    proxy_cache_bypass 1;
    proxy_no_cache     1;
}

## Health-check
location = /health {
    proxy_pass         http://localhost:8000/health;
    proxy_http_version 1.1;
    proxy_set_header   Host               $host;
    proxy_set_header   X-Real-IP          $remote_addr;
    proxy_set_header   X-Forwarded-For    $proxy_add_x_forwarded_for;
    proxy_set_header   X-Forwarded-Proto  $scheme;
    access_log off;
}
```

### 3. Replace the Root Location Block

Replace this block:
```nginx
location / {
    try_files $uri $uri/ /index.html @reverse_proxy;
    # Security headers...
}
```

With this:
```nginx
location / {
    # For development, proxy all requests to Vite dev server
    # This ensures HMR works and all assets are served correctly
    proxy_pass http://localhost:5173;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Security headers for the app
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin-when-cross-origin";
}
```

## Steps to Apply

1. **Backup your current NGINX config:**
   ```bash
   sudo cp /etc/nginx/sites-available/lakefrontdigital.io /etc/nginx/sites-available/lakefrontdigital.io.backup
   ```

2. **Edit your NGINX config:**
   ```bash
   sudo nano /etc/nginx/sites-available/lakefrontdigital.io
   ```

3. **Make the changes above**

4. **Test the configuration:**
   ```bash
   sudo nginx -t
   ```

5. **Restart NGINX:**
   ```bash
   sudo systemctl restart nginx
   ```

6. **Restart your Vite dev server:**
   ```bash
   cd /home/azureuser/opus2/ai-productivity-app/frontend
   npm run dev
   ```

## Verification

After making these changes, you should:
1. No longer see 404 errors for React assets
2. See successful WebSocket connections in the browser console
3. Have Hot Module Replacement working properly
4. See `[vite] connected.` in the browser console instead of connection errors

## For Production

When you're ready to deploy to production, you'll need to:
1. Uncomment the static asset caching block
2. Replace the proxy-based location blocks with proper static file serving
3. Build your app with `npm run build` and serve the built files

The current configuration is specifically for development with the Vite dev server.
