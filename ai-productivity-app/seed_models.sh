#!/bin/bash

# Simple script to seed AI models in the database
# This script can be run from the project root

echo "🌱 Seeding AI models database..."

# Check if Docker is available and containers are running
if docker compose ps | grep -q backend; then
    echo "🐳 Using Docker backend container..."
    docker compose exec backend python3 -m app.cli.seed_models
elif command -v python3 &> /dev/null; then
    echo "🐍 Using local Python environment..."
    cd backend
    
    # Check if virtual environment exists
    if [ -d "venv" ]; then
        echo "📦 Activating virtual environment..."
        source venv/bin/activate
    fi
    
    # Try to run the seeding
    python3 -m app.cli.seed_models
else
    echo "❌ Neither Docker nor Python3 found!"
    echo "Please either:"
    echo "  1. Start Docker containers: make dev"
    echo "  2. Install Python dependencies: cd backend && pip install -r requirements.txt"
    exit 1
fi

echo "✅ Model seeding completed!"