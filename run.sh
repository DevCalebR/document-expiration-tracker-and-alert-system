#!/bin/bash

# --- Backend ---
osascript <<EOF
tell application "Terminal"
    do script "cd ~/Desktop/DocExpire/backend && source .venv/bin/activate && python -m uvicorn main:app --reload"
end tell
EOF

# Wait 2 seconds for backend to start (adjust if needed)
sleep 2

# --- Frontend ---
osascript <<EOF
tell application "Terminal"
    do script "cd ~/Desktop/DocExpire/frontend && npm run dev"
end tell
EOF

# Wait 3 seconds for frontend to start
sleep 3

# --- Open frontend in default browser ---
open "http://localhost:5173"

