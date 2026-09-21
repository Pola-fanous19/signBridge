#!/usr/bin/env bash
# SignBridge v4 - One-Click Launcher (macOS / Linux)
set -e
cd "$(dirname "$0")"

echo "=========================================================="
echo "  SignBridge v4 - One-Click Launcher"
echo "=========================================================="

# 1. Backend setup
cd backend
if [ ! -d ".venv" ]; then
    echo "[1/4] Creating Python virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate
echo "[2/4] Installing backend dependencies..."
pip install --quiet --upgrade pip
pip install -r requirements.txt
cd ..

# 2. Frontend setup
cd frontend
if [ ! -d "node_modules" ]; then
    echo "[3/4] Installing frontend dependencies (npm install)..."
    npm install
fi
cd ..

# 3. Launch backend & frontend
echo "[4/4] Starting backend & frontend..."
(cd backend && ./.venv/bin/python -m flask --app app.main run --host 0.0.0.0 --port 8000) &
BACKEND_PID=$!

sleep 3

(cd frontend && npm run dev) &
FRONTEND_PID=$!

echo ""
echo "=========================================================="
echo "  SignBridge v4 is running!"
echo "  - Backend:  http://localhost:8000"
echo "  - Frontend: http://localhost:5173"
echo "=========================================================="
echo "  Press Ctrl+C to stop."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
