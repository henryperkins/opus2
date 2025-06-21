# AI Productivity App - NGINX Integration Guide

## Overview
This guide helps you integrate the AI Productivity App with your existing NGINX server configuration.

## Prerequisites
- NGINX installed and running on your server
- Backend container running on port 8000 (via docker-compose.prod.yml)
- Frontend static files deployed to your web root

## Configuration Steps

### 1. Add the Configuration
Include the provided NGINX configuration in your existing server block. You can either:

**Option A: Include the config file**
```nginx
server {
    # Your existing configuration...

    include /path/to/ai-productivity-app/nginx-ai-app-config.conf;

    # Your other location blocks...
}
```

**Option B: Copy the configuration directly**
Copy the contents of `nginx-ai-app-config.conf` into your server block.

### 2. Adjust Paths
Update the configuration based on your setup:

- **Web Root**: Ensure your `root` directive points to where the frontend files are deployed
- **Backend Port**: If your backend runs on a different port, update the `proxy_pass` URLs
- **SSL**: Add SSL configuration if you're using HTTPS

### 3. Example Complete Server Block
```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Set the web root to where frontend files are deployed
    root /var/www/ai-productivity-app;
    index index.html;

    # Include AI app configuration
    include /path/to/ai-productivity-app/nginx-ai-app-config.conf;

    # Your other existing configurations...
}
```

### 4. Test and Reload
```bash
# Test the configuration
sudo nginx -t

# Reload NGINX
sudo systemctl reload nginx
```

## Configuration Explanation

### API Proxying
- All `/api/*` requests are proxied to the backend container on port 8000
- WebSocket support is included for real-time features
- Proper headers are set for the backend to identify the original request

### Static File Handling
- Static assets (JS, CSS, images) are served with long-term caching
- Gzip compression is recommended (add to your main config if not present)

### SPA Support
- The `try_files` directive handles React Router client-side routing
- All non-API, non-asset requests fall back to `index.html`

### Security Headers
- Basic security headers are added to protect against common attacks
- Adjust these based on your security requirements

## Deployment Workflow

1. **Deploy Backend**: Run `./deploy-prod.sh` to build and start the backend container
2. **Deploy Frontend**: The script can optionally deploy frontend files, or do it manually
3. **Reload NGINX**: `sudo systemctl reload nginx` after any configuration changes

## Health Checks

- Backend health: `http://your-domain.com/health`
- Frontend: `http://your-domain.com` should serve the app
- API test: `http://your-domain.com/api/health` should return backend status

## Troubleshooting

### Common Issues

1. **502 Bad Gateway**: Backend container not running or port mismatch
   - Check: `docker ps` to verify backend is running
   - Check: Backend is accessible on `localhost:8000`

2. **404 on API routes**: Proxy configuration not working
   - Verify the `proxy_pass` URL is correct
   - Check NGINX error logs: `sudo tail -f /var/log/nginx/error.log`

3. **Static files not loading**: Path or permissions issue
   - Verify frontend files are in the correct web root
   - Check file permissions: `ls -la /var/www/ai-productivity-app/`

4. **SPA routing issues**: `try_files` not configured correctly
   - Ensure the SPA location block comes after specific location blocks
   - Test direct URL access to verify client-side routing works

### Logs
- NGINX error log: `/var/log/nginx/error.log`
- NGINX access log: `/var/log/nginx/access.log`
- Backend logs: `docker logs ai-productivity-app-backend-1`

## Performance Optimization

Consider adding these to your main NGINX configuration:

```nginx
# Gzip compression
gzip on;
gzip_vary on;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

# Connection optimization
keepalive_timeout 65;
keepalive_requests 100;

# Buffer sizes (adjust based on your needs)
client_max_body_size 50M;
client_body_buffer_size 1M;
```

## SSL/HTTPS

If using SSL, add these modifications:

```nginx
server {
    listen 443 ssl http2;
    ssl_certificate /path/to/your/cert.pem;
    ssl_certificate_key /path/to/your/key.pem;

    # Update proxy headers for HTTPS
    location ^~ /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header X-Forwarded-Proto https;
        # ... other proxy settings
    }
}
```
