#!/usr/bin/env bash
# Starts backend (FastAPI :8000) + frontend (Vite :5173) together.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Requires Python 3.10+ (uses PEP 604 `X | None` type hints).
PYTHON_BIN=""
for candidate in python3.12 python3.11 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
      PYTHON_BIN="$candidate"
      break
    fi
  fi
done
if [ -z "$PYTHON_BIN" ]; then
  echo "Error: Python 3.10+ is required but was not found (checked python3.12/3.11/3.10/3)." >&2
  exit 1
fi

cd "$ROOT_DIR/backend"
if [ ! -d ".venv" ]; then
  "$PYTHON_BIN" -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
deactivate

cd "$ROOT_DIR/frontend"
npm install --silent
npm run dev &
FRONTEND_PID=$!

trap 'kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null' INT TERM
echo "Backend:  http://localhost:8000/docs"
echo "Frontend: http://localhost:5173"
wait
