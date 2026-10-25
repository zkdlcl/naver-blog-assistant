#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
PID_DIR="$PROJECT_ROOT/data/pids"
PYTHON_BIN="$PROJECT_ROOT/venv/bin/python"
START_WEB="${START_WEB:-1}"
START_DISCORD_BOT="${START_DISCORD_BOT:-0}"
START_WATCH_RANKER="${START_WATCH_RANKER:-1}"

mkdir -p "$LOG_DIR" "$PID_DIR"
cd "$PROJECT_ROOT"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Missing virtualenv Python: $PYTHON_BIN"
  echo "Run: bash scripts/bootstrap_local.sh"
  exit 1
fi

if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
  echo "Missing .env file."
  echo "Run: cp .env.example .env"
  exit 1
fi

set -a
source "$PROJECT_ROOT/.env"
set +a

start_service() {
  local name="$1"
  local pid_file="$2"
  local pattern="$3"
  shift 3

  if [[ -f "$pid_file" ]]; then
    local existing_pid
    existing_pid="$(cat "$pid_file")"
    if [[ -n "$existing_pid" ]] && kill -0 "$existing_pid" 2>/dev/null; then
      echo "$name already running: $existing_pid"
      return
    fi
  fi

  if [[ -n "$pattern" ]]; then
    local found_pid
    found_pid="$(pgrep -f "$pattern" | head -n 1 || true)"
    if [[ -n "$found_pid" ]] && kill -0 "$found_pid" 2>/dev/null; then
      echo "$name already running: $found_pid"
      echo "$found_pid" > "$pid_file"
      return
    fi
  fi

  echo "Starting $name..."
  nohup "$@" >> "$LOG_DIR/$name.log" 2>&1 &
  echo "$!" > "$pid_file"
  echo "$name started: $(cat "$pid_file")"
}

if [[ "$START_WEB" == "1" ]]; then
  start_service "bms-web" "$PID_DIR/bms-web.pid" "scripts/run_web.py" \
    "$PYTHON_BIN" "$PROJECT_ROOT/scripts/run_web.py"
fi

if [[ "$START_DISCORD_BOT" == "1" ]]; then
  if [[ -z "${DISCORD_TOKEN:-}" ]]; then
    echo "Skipping bms-discord-bot: DISCORD_TOKEN is empty."
  else
    start_service "bms-discord-bot" "$PID_DIR/bms-discord-bot.pid" "bot/main.py" \
      "$PYTHON_BIN" "$PROJECT_ROOT/bot/main.py"
  fi
fi

if [[ "$START_WATCH_RANKER" == "1" ]]; then
  if [[ -z "${TARGET_BLOG_ID:-}" && -z "${TARGET_BLOG_URL:-}" ]]; then
    echo "Skipping bms-watch-ranker: TARGET_BLOG_ID or TARGET_BLOG_URL is empty."
  else
    start_service "bms-watch-ranker" "$PID_DIR/bms-watch-ranker.pid" "scripts/run_watch_ranker.py --loop" \
      "$PYTHON_BIN" "$PROJECT_ROOT/scripts/run_watch_ranker.py" --loop
  fi
fi

echo "BMS local services are ready."
