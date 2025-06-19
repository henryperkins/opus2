#!/bin/bash

# AI Productivity App - Simplified Startup Script
set -e

echo "🚀 Starting AI Productivity App..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if this is first run by looking for built images
BACKEND_IMAGE=$(docker images -q ai-productivity-app-backend 2>/dev/null)
FRONTEND_IMAGE=$(docker images -q ai-productivity-app-frontend 2>/dev/null)

if [[ -z "$BACKEND_IMAGE" || -z "$FRONTEND_IMAGE" ]]; then
    echo "🔧 First run detected - installing dependencies and building containers..."
    echo "⏳ This may take a few minutes..."
    docker compose build
    echo "✅ Build complete!"
else
    echo "🔧 Starting containers..."
fi

# Start the application
docker compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to start..."
sleep 5

# Check backend health
echo "🔍 Checking backend health..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health/ready > /dev/null 2>&1; then
        echo "✅ Backend is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "⚠️  Backend readiness timeout - check logs with: docker compose logs backend"
    fi
    sleep 2
done

# Check frontend
echo "🔍 Checking frontend..."
for i in {1..15}; do
    if curl -s http://localhost:5173 > /dev/null 2>&1; then
        echo "✅ Frontend is ready"
        break
    fi
    if [ $i -eq 15 ]; then
        echo "⚠️  Frontend startup timeout - check logs with: docker compose logs frontend"
    fi
    sleep 2
done

echo ""
echo "🎉 Application started successfully!"
echo "📱 Frontend: http://localhost:5173"
echo "🔧 Backend API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "🛑 To stop: docker compose down"
echo "📊 To view logs: docker compose logs -f"