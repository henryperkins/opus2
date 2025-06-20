#!/bin/bash

# Build and deploy production version of AI Productivity App

set -e

echo "🚀 Building production version..."

# Stop any running containers
echo "Stopping existing containers..."
docker compose -f docker-compose.prod.yml down

# Build production images
echo "Building production images..."
docker compose -f docker-compose.prod.yml build --no-cache

# Start production containers
echo "Starting production containers..."
docker compose -f docker-compose.prod.yml up -d

# Wait for services to be healthy
echo "Waiting for services to be ready..."
sleep 10

# Check if services are running
if docker compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    echo "✅ Production deployment successful!"
    echo "Frontend: http://localhost:8080"
    echo "Backend API: http://localhost:8000"

    # Show container status
    echo ""
    echo "Container Status:"
    docker compose -f docker-compose.prod.yml ps

    # Test endpoints
    echo ""
    echo "Testing endpoints..."
    if curl -s http://localhost:8000/health/ready > /dev/null; then
        echo "✅ Backend health check passed"
    else
        echo "⚠️  Backend health check failed"
    fi

    if curl -s http://localhost:8080 > /dev/null; then
        echo "✅ Frontend health check passed"
    else
        echo "⚠️  Frontend health check failed"
    fi
else
    echo "❌ Deployment failed"
    docker compose -f docker-compose.prod.yml logs
    exit 1
fi
