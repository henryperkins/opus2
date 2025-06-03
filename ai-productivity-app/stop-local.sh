#!/bin/bash

# AI Productivity App - Local Development Stop Script
echo "🛑 Stopping AI Productivity App (Local Mode)..."

# Kill processes using saved PIDs
if [ -f "backend.pid" ]; then
    BACKEND_PID=$(cat backend.pid)
    if kill -0 $BACKEND_PID 2>/dev/null; then
        echo "🔧 Stopping backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID
    fi
    rm -f backend.pid
fi

if [ -f "frontend.pid" ]; then
    FRONTEND_PID=$(cat frontend.pid)
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        echo "🔧 Stopping frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID
    fi
    rm -f frontend.pid
fi

# Also try to kill by port (backup method)
echo "🔍 Checking for remaining processes..."

# Kill any process using port 8000 (backend)
if lsof -ti:8000 >/dev/null 2>&1; then
    echo "🔧 Killing process on port 8000..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
fi

# Kill any process using port 5173 (frontend)
if lsof -ti:5173 >/dev/null 2>&1; then
    echo "🔧 Killing process on port 5173..."
    lsof -ti:5173 | xargs kill -9 2>/dev/null || true
fi

echo "✅ Stopped successfully!"