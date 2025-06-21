# Production Deployment Guide

This guide explains how to deploy the AI Productivity App to production using server-installed NGINX.

## Overview

The production setup consists of:
- **Frontend**: Static files built with Vite, served by NGINX
- **Backend**: Docker container running on port 8000
- **NGINX**: Server-installed, proxies API requests and serves static files

## Quick Deployment

1. **Run the deployment script:**
   ```bash
   ./deploy-prod.sh
   ```

   This script will:
   - Build the frontend static files (`frontend/dist/`)
   - Build and start the backend Docker container
   - Provide next steps for NGINX configuration

## Manual Deployment Steps

### 1. Build Frontend
```bash
cd frontend
npm run build
cd ..
```

### 2. Deploy Backend
```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### 3. Configure NGINX

1. **Copy static files to web server:**
   ```bash
   sudo cp -r frontend/dist/* /var/www/ai-productivity-app/
   ```

2. **Configure NGINX:**
   - Copy `nginx.conf.template` to your NGINX sites directory
   - Modify the configuration for your domain and paths
   - Enable the site and reload NGINX

   ```bash
   sudo cp nginx.conf.template /etc/nginx/sites-available/ai-productivity-app
   sudo ln -s /etc/nginx/sites-available/ai-productivity-app /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   ```

## Configuration Details

### NGINX Configuration
- **Static files**: Served from `/var/www/ai-productivity-app/`
- **API proxy**: `/api/*` → `http://localhost:8000/`
- **Health checks**: `/health` → `http://localhost:8000/health`
- **Documentation**: `/docs` → `http://localhost:8000/docs`

### Backend Container
- **Port**: 8000
- **Health check**: `http://localhost:8000/health/ready`
- **API documentation**: `http://localhost:8000/docs`

## Verification

1. **Check backend health:**
   ```bash
   curl http://localhost:8000/health/ready
   ```

2. **Check frontend (via NGINX):**
   ```bash
   curl http://your-domain.com
   ```

3. **Check API proxy (via NGINX):**
   ```bash
   curl http://your-domain.com/api/health/ready
   ```

## Monitoring

- **Backend logs**: `docker compose -f docker-compose.prod.yml logs -f`
- **NGINX logs**: `sudo tail -f /var/log/nginx/access.log /var/log/nginx/error.log`

## Updates

To update the application:

1. **Update code**: Pull latest changes
2. **Redeploy**: Run `./deploy-prod.sh`
3. **Update static files**: Copy new `frontend/dist/*` to web server
4. **Restart if needed**: Backend container will be recreated automatically

## Security Considerations

1. **Use HTTPS** in production (see nginx.conf.template for SSL configuration)
2. **Set proper environment variables** (SECRET_KEY, etc.)
3. **Configure firewall** to only allow necessary ports
4. **Regular updates** of Docker images and system packages

## Troubleshooting

### Backend Issues
- Check container status: `docker compose -f docker-compose.prod.yml ps`
- Check logs: `docker compose -f docker-compose.prod.yml logs backend`
- Verify health endpoint: `curl http://localhost:8000/health/ready`

### Frontend Issues
- Check NGINX configuration: `sudo nginx -t`
- Check NGINX logs: `sudo tail -f /var/log/nginx/error.log`
- Verify static files exist: `ls -la /var/www/ai-productivity-app/`

### Connectivity Issues
- Verify NGINX is proxying correctly
- Check firewall settings
- Verify domain DNS configuration
