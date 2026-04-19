#!/bin/bash

# Get the absolute path to the app directory
APP_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo "🔮 Initializing RollMind..."

# 1. Start the Backend API in the background
echo "🚀 Launching Backend API (FastAPI)..."
cd "$APP_DIR/api"
../../venv/bin/python main.py &
API_PID=$!

# 2. Start the Frontend Web
echo "✨ Launching Frontend Web (Next.js)..."
cd "$APP_DIR/web2"
npm run dev &
WEB_PID=$!

# Function to handle script termination (Ctrl+C)
cleanup() {
    echo ""
    echo "🛑 Stopping RollMind..."
    kill $API_PID
    kill $WEB_PID
    wait $API_PID 2>/dev/null
    wait $WEB_PID 2>/dev/null
    echo "Done."
    exit
}

# Trap SIGINT (Ctrl+C) and call cleanup
trap cleanup SIGINT

# Keep the script running and wait for children
wait
