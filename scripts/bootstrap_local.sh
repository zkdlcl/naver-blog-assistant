#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$PROJECT_ROOT"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python not found: $PYTHON_BIN"
  exit 1
fi

if [[ ! -d "$PROJECT_ROOT/venv" ]]; then
  echo "Creating virtualenv..."
  "$PYTHON_BIN" -m venv "$PROJECT_ROOT/venv"
fi

echo "Installing Python packages..."
"$PROJECT_ROOT/venv/bin/pip" install --upgrade pip
"$PROJECT_ROOT/venv/bin/pip" install -r "$PROJECT_ROOT/requirements.txt"

echo "Installing Playwright Chromium..."
"$PROJECT_ROOT/venv/bin/python" -m playwright install chromium

if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
  cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
  echo "Created .env from .env.example. Fill in DISCORD_TOKEN and TARGET_BLOG_ID."
fi

echo "Bootstrap complete."
echo "Next:"
echo "  1. Edit .env"
echo "  2. bash scripts/start_local_services.sh"
