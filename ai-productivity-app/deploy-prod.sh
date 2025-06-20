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
if docker compose -f docker-compose.prod.yml ps | grep -q "running"; then
    echo "✅ Production deployment successful!"
    echo "Frontend: http://localhost"
    echo "Backend API: http://localhost:8000"
else
    echo "❌ Deployment failed"
    docker compose -f docker-compose.prod.yml logs
    exit 1
fi
