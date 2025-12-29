#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
VENV_DIR="$SCRIPT_DIR/../.venv"

if [ ! -d "$VENV_DIR" ]; then
  echo "Virtual environment not found at $VENV_DIR" >&2
  exit 1
fi

source "$VENV_DIR/bin/activate"
exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
