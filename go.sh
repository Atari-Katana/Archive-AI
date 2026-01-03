#!/bin/bash
set -euo pipefail

# Root of repo
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Compose overlay for AWQ + 7B profile
COMPOSE_FILES="-f docker-compose.yml -f docker-compose.awq-7b.yml"

# Check for required models
echo "🔍 Checking required models..."
if [ ! -f "$ROOT_DIR/models/goblin/DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf" ]; then
    echo "⚠️  Goblin model not found. Downloading..."
    echo ""
    python3 "$ROOT_DIR/scripts/download-models.py" --model goblin-7b
    download_status=$?

    if [ $download_status -ne 0 ]; then
        echo ""
        echo "✗ Model download failed. Please check:"
        echo "  1. Internet connection"
        echo "  2. Disk space (need ~8.4GB free)"
        echo "  3. Manual download: https://huggingface.co/unsloth/DeepSeek-R1-Distill-Qwen-7B-GGUF"
        echo ""
        exit 1
    fi
    echo ""
else
    echo "✓ Goblin model found"
fi
echo ""

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

echo ""
echo "✓ Archive-AI started successfully!"
echo "  Web UI: http://localhost:8888"
echo "  API: http://localhost:8080/docs"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for UI server (cleanup will run on exit)
wait "$UI_PID"
