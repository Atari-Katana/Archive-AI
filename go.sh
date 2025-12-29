#!/bin/bash
set -euo pipefail

# Root of repo
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Compose overlay for AWQ + 7B profile
COMPOSE_FILES="-f docker-compose.yml -f docker-compose.awq-7b.yml"

cleanup() {
    # Stop UI server if running
    if [[ -n "${UI_PID:-}" ]] && ps -p "$UI_PID" > /dev/null 2>&1; then
        kill "$UI_PID" || true
    fi
    # Bring down services started by this script
    (cd "$ROOT_DIR" && docker-compose $COMPOSE_FILES down) || true
}

trap cleanup EXIT INT TERM

# Start services (AWQ + 7B overlay)
(cd "$ROOT_DIR" && EXTRA_COMPOSE_FILE="docker-compose.awq-7b.yml" ./scripts/start.sh)

# Start UI server in background
(cd "$ROOT_DIR/ui" && python3 -m http.server 8888) &
UI_PID=$!

# Wait for UI server (cleanup will run on exit)
wait "$UI_PID"
