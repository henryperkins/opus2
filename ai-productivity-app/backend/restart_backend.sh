#!/bin/bash
# Script to restart the backend container to apply code changes

echo "Restarting backend to apply AI config fix..."

# Navigate to the app directory
cd "$(dirname "$0")/.."

# Restart just the backend service
docker compose restart ai-productivity-backend

echo "Backend restarted. Please wait a moment for it to fully start."
echo "You can check the logs with: docker-compose logs -f ai-productivity-backend"
