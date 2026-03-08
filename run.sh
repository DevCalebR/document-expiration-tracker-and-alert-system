#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

if [[ ! -f "$BACKEND_DIR/.env" ]]; then
  echo "Missing $BACKEND_DIR/.env"
  echo "Run: cp $BACKEND_DIR/.env.example $BACKEND_DIR/.env"
  exit 1
fi

if [[ ! -d "$BACKEND_DIR/.venv" ]]; then
  echo "Missing $BACKEND_DIR/.venv"
  echo "Run the backend setup first: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt -r requirements-dev.txt"
  exit 1
fi

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  echo "Missing $FRONTEND_DIR/node_modules"
  echo "Run the frontend setup first: cd $FRONTEND_DIR && npm install"
  exit 1
fi

osascript <<EOF_APP
 tell application "Terminal"
     do script "cd '$BACKEND_DIR' && source .venv/bin/activate && uvicorn main:app --reload"
 end tell
EOF_APP

sleep 2

osascript <<EOF_UI
 tell application "Terminal"
     do script "cd '$FRONTEND_DIR' && npm run dev"
 end tell
EOF_UI

sleep 2
open "http://localhost:5173"

echo "Started DocExpire local mode. Worker is not required unless RQ_ASYNC=True."
