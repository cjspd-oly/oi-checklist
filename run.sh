#!/bin/bash
set -e
set -o pipefail

cd /home/pd/Documents/GitHub/oi-checklist/

# ------------------------------
# Activate virtual environment
# ------------------------------
if [ ! -d "venv" ]; then
    echo "[ERROR] Virtual environment not found. Run setup.sh first."
    exit 1
fi

echo "[INFO] Activating virtual environment..."
source venv/bin/activate

# ------------------------------
# Run backend
# ------------------------------
echo "[INFO] Starting Flask backend..."
python3 backend/app.py &
BACKEND_PID=$!

# Give backend a few seconds to start
sleep 2

# ------------------------------
# Run frontend
# ------------------------------
echo "[INFO] Starting frontend server..."
python3 custom_server.py &
FRONTEND_PID=$!

echo "[INFO] Backend PID: $BACKEND_PID"
echo "[INFO] Frontend PID: $FRONTEND_PID"

# ------------------------------
# Wait for both processes to finish
# ------------------------------
wait $BACKEND_PID $FRONTEND_PID
