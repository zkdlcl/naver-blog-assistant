#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST_DIR="${1:-}"
INIT_GIT="${INIT_GIT:-1}"

if [[ -z "$DEST_DIR" ]]; then
  echo "Usage: bash scripts/export_public_snapshot.sh /path/to/output-dir"
  exit 1
fi

if [[ ! -d "$PROJECT_ROOT/.git" ]]; then
  echo "This script must run from a git working tree."
  exit 1
fi

mkdir -p "$DEST_DIR"
DEST_DIR="$(cd "$DEST_DIR" && pwd)"

if [[ -n "$(find "$DEST_DIR" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]; then
  echo "Destination directory is not empty: $DEST_DIR"
  exit 1
fi

cd "$PROJECT_ROOT"

git ls-files --cached --others --exclude-standard -z \
  | tar --null -T - -cf - \
  | tar -xf - -C "$DEST_DIR"

rm -rf \
  "$DEST_DIR/.git" \
  "$DEST_DIR/.codex" \
  "$DEST_DIR/venv" \
  "$DEST_DIR/.venv" \
  "$DEST_DIR/env" \
  "$DEST_DIR/logs" \
  "$DEST_DIR/data" \
  "$DEST_DIR/.env"

mkdir -p "$DEST_DIR/data" "$DEST_DIR/logs"
touch "$DEST_DIR/data/.gitkeep" "$DEST_DIR/logs/.gitkeep"

if [[ "$INIT_GIT" == "1" ]]; then
  git -C "$DEST_DIR" init -b main >/dev/null
fi

cat <<EOF
Public snapshot exported to:
  $DEST_DIR

Next steps:
  1. cd "$DEST_DIR"
  2. cp .env.example .env
  3. Fill in your local secrets in .env
  4. git remote add origin <new-public-repo-url>
  5. git add .
  6. git commit -m "Initial public snapshot"
  7. git push -u origin main
EOF
