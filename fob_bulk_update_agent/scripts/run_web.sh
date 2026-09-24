#!/usr/bin/env bash
# Start the FOB CSV Cleaner upload/download web UI.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
exec python -m uvicorn web.app:app --host "$HOST" --port "$PORT"
