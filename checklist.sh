#!/bin/bash

PROJECT_ROOT="/Users/avighna/Desktop/oi-checklist"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT"
FRONTEND_PORT=5501

BACKEND_SESSION="checklist-back"
FRONTEND_SESSION="checklist-front"

# --- Shutdown ---
if [[ "$1" == "--shutdown" ]]; then
  for session in "$BACKEND_SESSION" "$FRONTEND_SESSION"; do
    if tmux has-session -t "$session" 2>/dev/null; then
      echo "Killing session: $session"
      tmux kill-session -t "$session"
    fi
  done
  exit 0
fi

# --- Focus ---
if [[ "$1" == "--focus" ]]; then
  if [[ "$2" == "back" ]]; then
    if tmux has-session -t "$BACKEND_SESSION" 2>/dev/null; then
      tmux attach-session -t "$BACKEND_SESSION"
    else
      echo "Backend session not running."
    fi
  elif [[ "$2" == "front" ]]; then
    if tmux has-session -t "$FRONTEND_SESSION" 2>/dev/null; then
      tmux attach-session -t "$FRONTEND_SESSION"
    else
      echo "Frontend session not running."
    fi
  else
    echo "Usage: $0 --focus [back|front]"
    exit 1
  fi
  exit 0
fi

# --- Default: launch servers ---
if tmux has-session -t "$BACKEND_SESSION" 2>/dev/null || tmux has-session -t "$FRONTEND_SESSION" 2>/dev/null; then
  echo "One or both checklist servers already running. Use '--focus' or '--shutdown'."
  exit 1
fi

echo "Starting backend server in tmux session '$BACKEND_SESSION'..."
cp "$FRONTEND_DIR/index.html" "$FRONTEND_DIR/404.html"
tmux new-session -d -s "$BACKEND_SESSION" -c "$BACKEND_DIR" "FLASK_ENV=production python3 app.py"

echo "Starting frontend server in tmux session '$FRONTEND_SESSION'..."
tmux new-session -d -s "$FRONTEND_SESSION" -c "$FRONTEND_DIR" "python3 custom_server.py"

echo "Servers started."
echo "Use './checklist.sh --focus back' or '--focus front' to view logs."
echo "Use './checklist.sh --shutdown' to stop both."
