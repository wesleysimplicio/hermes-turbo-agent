#!/usr/bin/env bash
# apply-to-hermes2.sh — Copies the current repo into ~/.hermes2/hermes-agent
# and restarts the gateway via launchctl so changes take effect immediately.
#
# Skips: .git, venv, __pycache__, .claude, *.pyc, node_modules
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="$HOME/.hermes2/hermes-agent"

if [[ ! -d "$TARGET" ]]; then
  echo "ERROR: $TARGET does not exist. Install hermes2 first."
  exit 1
fi

echo "Syncing $REPO_DIR -> $TARGET"
rsync -av \
  --exclude='.git' \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='.claude' \
  --exclude='*.pyc' \
  --exclude='node_modules' \
  --exclude='.pytest_cache' \
  "$REPO_DIR/" "$TARGET/"

echo "Restarting gateway..."
launchctl kickstart -k "gui/$(id -u)/ai.hermes2.gateway" || true
sleep 3

if command -v hermes2 >/dev/null 2>&1; then
  hermes2 status || echo "(hermes2 status check failed — gateway may still be booting)"
fi

echo "Done."
