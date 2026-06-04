#!/usr/bin/env bash
# Convenience launcher: starts the backend (uvicorn) and frontend (vite) in
# the same terminal and tears them down together on Ctrl-C.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cleanup() {
  echo
  echo "Stopping…"
  kill "${BACK_PID:-}" "${FRONT_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "→ starting backend (uvicorn) on :8000"
(
  cd "$ROOT/backend"
  if [ ! -d .venv ]; then
    python -m venv .venv
    .venv/bin/pip install -q -r requirements.txt
  fi
  [ -f .env ] || cp .env.example .env
  .venv/bin/uvicorn app.main:app --reload
) &
BACK_PID=$!

echo "→ starting frontend (vite) on :5173"
(
  cd "$ROOT/frontend"
  [ -d node_modules ] || npm install
  npm run dev
) &
FRONT_PID=$!

wait
