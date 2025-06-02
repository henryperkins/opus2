#!/bin/bash

# AI Productivity App - Simplified Startup Script
set -e

echo "🚀 Starting AI Productivity App..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Start the application with Docker (no local dependency installation needed)
echo "🔧 Building and starting containers..."
docker compose up --build

echo "🎉 Application started!"
echo "📱 Frontend: http://localhost:5173"
echo "🔧 Backend API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the application"