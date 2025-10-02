#!/bin/bash
set -e  # Exit immediately if a command fails
set -o pipefail

# ------------------------------
# Setup virtual environment
# ------------------------------
if [ ! -d "venv" ]; then
    echo "[INFO] Creating virtual environment..."
    virtualenv venv
else
    echo "[INFO] Virtual environment already exists."
fi

echo "[INFO] Activating virtual environment..."
source venv/bin/activate

# ------------------------------
# Install dependencies
# ------------------------------
if [ -f "backend/requirements.txt" ]; then
    echo "[INFO] Installing Python dependencies..."
    pip install --upgrade pip
    pip install -r backend/requirements.txt
else
    echo "[ERROR] backend/requirements.txt not found."
    exit 1
fi

# ------------------------------
# Environment variables
# ------------------------------
if [ ! -f "backend/.env" ]; then
    echo "[INFO] Creating backend/.env file with default values..."
    cat <<EOL > backend/.env
# The port your backend will run on
PORT=5001

# Set to local for local development
FLASK_ENV=local

# Path to your SQLite database (e.g., database.db)
DATABASE_PATH=database.db

# Absolute path to the backend/ folder
BACKEND_DIR=backend

# URL where the frontend runs (e.g., http://localhost:5501)
FRONTEND_URL=http://localhost:5501

# URL where the Flask backend runs (e.g., http://localhost:5001)
BACKEND_URL=http://localhost:5001

# GitHub OAuth client ID
GITHUB_CLIENT_ID

# GitHub OAuth client secret
GITHUB_CLIENT_SECRET

# Discord OAuth client ID
DISCORD_CLIENT_ID

# Discord OAuth client secret
DISCORD_CLIENT_SECRET

# Google OAuth client ID
GOOGLE_CLIENT_ID

# Google OAuth client secret
GOOGLE_CLIENT_SECRET

# Username for an account that will be used to scrape qoj.ac (VCs)
QOJ_USER=

# Corresponding password for that account (to refresh sessions)
QOJ_PASS=
EOL
else
    echo "[INFO] backend/.env already exists. Skipping..."
fi


# ------------------------------
# Initialize database
# ------------------------------
echo "[INFO] Initializing database..."
python3 backend/database/init/init_db.py

echo "[INFO] Populating problems..."
python3 backend/database/init/populate_problems.py

echo "[INFO] Populating contests..."
python3 backend/database/init/populate_contests.py

# ------------------------------
# Run backend and frontend
# ------------------------------
echo "[INFO] Starting Flask backend..."
# Run backend in the background
python3 backend/app.py &

# Save backend PID if you want to stop it later
BACKEND_PID=$!

# Give backend a moment to start (optional)
sleep 2

echo "[INFO] Starting frontend server..."
# Activate venv and run frontend in another process
source venv/bin/activate
python3 custom_server.py &

# Save frontend PID if you want to stop it later
FRONTEND_PID=$!

echo "[INFO] Backend PID: $BACKEND_PID"
echo "[INFO] Frontend PID: $FRONTEND_PID"

# Wait for both processes to finish (keeps the script running)
wait $BACKEND_PID $FRONTEND_PID
