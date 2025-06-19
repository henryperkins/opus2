#!/bin/bash

# AI Productivity App - Local Development Startup (No Docker)
set -e

echo "🚀 Starting AI Productivity App (Local Mode)..."

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check dependencies
echo "🔍 Checking dependencies..."

if ! command_exists python3; then
    echo "❌ Python3 is required but not installed"
    exit 1
fi

if ! command_exists node; then
    echo "❌ Node.js is required but not installed"
    exit 1
fi

if ! command_exists npm; then
    echo "❌ npm is required but not installed"
    exit 1
fi

echo "✅ Dependencies check passed"

# Backend setup
echo "🔧 Setting up backend..."
cd backend

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Ensure cookies are not marked Secure when running over plain HTTP so that the
# browser will include the auth cookie on subsequent requests.
export INSECURE_COOKIES=true

# Install/update Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Initialize database if needed
if [ ! -f "data/app.db" ]; then
    echo "🗄️ Initializing database..."
    mkdir -p data
    python scripts/init_db.py
fi

# Start backend server in foreground (prints logs and errors to terminal)
echo "🚀 Starting backend server..."
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
echo ""
echo "*************************************"
echo "* The backend server will now start. *"
echo "* Open a NEW TERMINAL and run:       *"
echo "*    cd frontend && npm run dev      *"
echo "* to start the frontend server.      *"
echo "*************************************"
echo ""
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# If you want to run the backend in background and log to file, use:
# nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
# BACKEND_PID=$!
# echo "Backend started with PID: $BACKEND_PID"

# Wait for services to start
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
        echo "⚠️  Backend readiness timeout - check backend.log"
        echo "Backend PID: $BACKEND_PID"
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
        echo "⚠️  Frontend startup timeout - check frontend.log"
        echo "Frontend PID: $FRONTEND_PID"
    fi
    sleep 2
done

# Save PIDs for cleanup
echo "$BACKEND_PID" > backend.pid
echo "$FRONTEND_PID" > frontend.pid

echo ""
echo "🎉 Application started successfully!"
echo "📱 Frontend: http://localhost:5173"
echo "🔧 Backend API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "📊 Logs:"
echo "  Backend: tail -f backend/backend.log"
echo "  Frontend: tail -f frontend/frontend.log"
echo ""
echo "🛑 To stop: ./stop-local.sh"
echo "   Or manually: kill $BACKEND_PID $FRONTEND_PID"
