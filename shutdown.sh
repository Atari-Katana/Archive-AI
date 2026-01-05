#!/bin/bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "\n${BLUE}===================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Banner
print_header "Archive-AI Shutdown"

# Get root directory
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

# Stop UI server if running on port 8888
UI_PID=$(lsof -ti:8888 2>/dev/null || true)
if [ -n "$UI_PID" ]; then
    print_info "Stopping UI server (PID: $UI_PID)..."
    kill "$UI_PID" 2>/dev/null || true
    sleep 1
    print_success "UI server stopped"
fi

# Stop Docker services
print_info "Stopping Docker services..."

# Try to stop with AWQ overlay first (in case it was started with ./go.sh)
if [ -f "docker-compose.awq-7b.yml" ]; then
    docker-compose -f docker-compose.yml -f docker-compose.awq-7b.yml down 2>/dev/null || true
fi

# Stop regular services
docker-compose down

print_success "All services stopped"

# Show status
print_header "Shutdown Complete"

echo "Services have been stopped. Data is preserved in:"
echo "  • data/redis/      - Redis data and memories"
echo "  • data/archive/    - Archived memories"
echo "  • data/library/    - Ingested documents"
echo ""
echo "To start Archive-AI again, run:"
echo "  ./go.sh"
echo ""

print_success "Archive-AI shutdown successfully!"
