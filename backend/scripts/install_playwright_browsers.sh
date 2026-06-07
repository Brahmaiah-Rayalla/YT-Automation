#!/usr/bin/env bash
# Installs Playwright Chromium with extended timeout and stale-lock cleanup.
set -euo pipefail

BACKEND_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${BACKEND_ROOT}/.venv/bin/python"
LOCK_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/.cache/ms-playwright}/__dirlock"

if [[ ! -x "$PYTHON" ]]; then
  echo "Virtual env not found. Run: python -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

export PLAYWRIGHT_DOWNLOAD_CONNECTION_TIMEOUT="${PLAYWRIGHT_DOWNLOAD_CONNECTION_TIMEOUT:-1800000}"

if [[ -e "$LOCK_PATH" ]]; then
  echo "Removing stale Playwright lock: $LOCK_PATH"
  rm -rf "$LOCK_PATH"
fi

for attempt in 1 2 3; do
  echo "Installing Chromium (attempt $attempt of 3)..."
  if "$PYTHON" -m playwright install chromium; then
    echo "Chromium installed successfully."
    exit 0
  fi
  rm -rf "$LOCK_PATH" 2>/dev/null || true
  sleep 10
done

echo "Failed to install Chromium after 3 attempts."
exit 1
