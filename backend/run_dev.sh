#!/usr/bin/env bash
# Start API with venv + deps. Uses .env from this folder (create with: cp ollama.env .env)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "No .env — copying ollama.env → .env"
  cp ollama.env .env
fi

if [[ ! -d .venv ]]; then
  echo "Creating .venv…"
  python3 -m venv .venv
fi

echo "Installing dependencies…"
.venv/bin/pip install -q -r requirements.txt

PORT="${PORT:-8000}"
echo "Starting http://127.0.0.1:${PORT} (Ollama must be running)"
if lsof -iTCP:"${PORT}" -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "Port ${PORT} is already in use. Stop the other process, e.g.:"
  echo "  lsof -iTCP:${PORT} -sTCP:LISTEN"
  echo "  kill \$(lsof -iTCP:${PORT} -sTCP:LISTEN -t)"
  echo "Or use another port: PORT=8001 $0"
  exit 1
fi
exec .venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port "${PORT}"
