#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$PROJECT_ROOT/data/pids"

stop_service() {
  local name="$1"
  local pid_file="$2"

  if [[ ! -f "$pid_file" ]]; then
    echo "$name is not running."
    return
  fi

  local pid
  pid="$(cat "$pid_file")"
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    echo "Stopping $name: $pid"
    kill "$pid"
  else
    echo "$name pid is stale: $pid"
  fi
  rm -f "$pid_file"
}

stop_service "bms-web" "$PID_DIR/bms-web.pid"
stop_service "bms-discord-bot" "$PID_DIR/bms-discord-bot.pid"
stop_service "bms-watch-ranker" "$PID_DIR/bms-watch-ranker.pid"
