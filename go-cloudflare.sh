#!/bin/bash
set -euo pipefail

# Archive-AI Cloudflare Startup Script
# Starts Archive-AI optimized for Cloudflare Tunnel deployment
#
# Key differences from go.sh:
# - Uses docker-compose.cloudflare.yml overlay
# - Does NOT start separate UI server (Brain serves UI at /ui/)
# - Configures PUBLIC_URL for Cloudflare domain
# - Single entry point on port 8080

# Root of repo
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

# Use standalone Cloudflare compose file (no merging, avoids port conflicts)
COMPOSE_FILES="-f docker-compose.cloudflare-fixed.yml"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}Archive-AI v7.5 - Cloudflare Mode${NC}"
echo -e "${BLUE}=================================================${NC}"
echo ""

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

# Check for .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found!${NC}"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo ""
    echo "IMPORTANT: Edit .env and set:"
    echo "  1. REDIS_PASSWORD (required)"
    echo "  2. PUBLIC_URL=https://your-domain.com (your Cloudflare domain)"
    echo ""
    echo "Run: nano .env"
    echo ""
    exit 1
fi

# Check if PUBLIC_URL is set
if ! grep -q "PUBLIC_URL=" .env 2>/dev/null; then
    echo -e "${YELLOW}⚠️  PUBLIC_URL not set in .env${NC}"
    echo ""
    echo "Add this line to your .env file:"
    echo "  PUBLIC_URL=https://your-domain.com"
    echo ""
    echo "This should be your Cloudflare Tunnel domain."
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

cleanup() {
    # Bring down services started by this script
    (cd "$ROOT_DIR" && docker-compose $COMPOSE_FILES down) || true
}

trap cleanup EXIT INT TERM

# Clean up any existing containers/networks first
echo "🧹 Cleaning up any existing Archive-AI containers..."
docker-compose -f docker-compose.yml -f docker-compose.awq-7b.yml down 2>/dev/null || true
docker-compose -f docker-compose.yml down 2>/dev/null || true
docker-compose $COMPOSE_FILES down 2>/dev/null || true

# Remove any leftover containers with archive names
docker ps -a --format "{{.Names}}" | grep -E "^archive-" | xargs -r docker rm -f 2>/dev/null || true

echo ""

# Start services (Cloudflare overlay)
echo "🚀 Starting Archive-AI with Cloudflare configuration..."
echo ""
(cd "$ROOT_DIR" && docker-compose $COMPOSE_FILES up -d)

# Wait for services to be ready
echo ""
echo "⏳ Waiting for services to start..."
sleep 5

# Check health
if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Brain service is healthy${NC}"
else
    echo -e "${YELLOW}⚠️  Brain service not responding yet (may still be loading models)${NC}"
fi

echo ""
echo -e "${GREEN}=================================================${NC}"
echo -e "${GREEN}✓ Archive-AI started successfully!${NC}"
echo -e "${GREEN}=================================================${NC}"
echo ""
echo "Local Access:"
echo "  • API:     http://localhost:8080/docs"
echo "  • Health:  http://localhost:8080/health"
echo "  • UI:      http://localhost:8080/ui/index.html"
echo "  • Metrics: http://localhost:8080/ui/metrics-panel.html"
echo "  • Config:  http://localhost:8080/ui/config-panel.html"
echo ""
echo "Cloudflare Tunnel Access (once configured):"
PUBLIC_URL=$(grep "PUBLIC_URL=" .env 2>/dev/null | cut -d '=' -f2 | tr -d '"' || echo "https://your-domain.com")
echo "  • API:     ${PUBLIC_URL}/docs"
echo "  • Health:  ${PUBLIC_URL}/health"
echo "  • UI:      ${PUBLIC_URL}/ui/index.html"
echo "  • Metrics: ${PUBLIC_URL}/ui/metrics-panel.html"
echo "  • Config:  ${PUBLIC_URL}/ui/config-panel.html"
echo ""
echo "Next Steps:"
echo "  1. Configure Cloudflare Tunnel (see docker-compose.cloudflare.yml comments)"
echo "  2. Set up DNS routing to your domain"
echo "  3. Access via your Cloudflare domain"
echo ""
echo "Management:"
echo "  • Health check:  bash scripts/health-check.sh"
echo "  • Stop services: ./shutdown.sh"
echo "  • View logs:     docker-compose logs -f brain"
echo ""
echo -e "${BLUE}Press Ctrl+C to stop all services${NC}"
echo ""

# Keep script running (cleanup will run on exit)
tail -f /dev/null
