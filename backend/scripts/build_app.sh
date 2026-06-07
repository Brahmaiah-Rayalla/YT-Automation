#!/usr/bin/env bash
set -euo pipefail

BACKEND_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND_ROOT="$(cd "$BACKEND_ROOT/../frontend" && pwd)"
STATIC_DIR="$BACKEND_ROOT/static"

cd "$FRONTEND_ROOT"
if [ ! -d node_modules ]; then
  npm install
fi
npm run build

rm -rf "$STATIC_DIR"
cp -r "$FRONTEND_ROOT/dist" "$STATIC_DIR"
echo "Built frontend into $STATIC_DIR"
