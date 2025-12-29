#!/bin/bash
#
# Archive-AI Startup Script
# Starts Archive-AI services with health verification
#
# Usage:
#   bash scripts/start.sh           # Development mode
#   bash scripts/start.sh --prod    # Production mode
#   bash scripts/start.sh --rebuild # Rebuild images before starting
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROD_MODE=false
REBUILD=false
DETACH=true

# Parse arguments
for arg in "$@"; do
    case $arg in
        --prod)
            PROD_MODE=true
            shift
            ;;
        --rebuild)
            REBUILD=true
            shift
            ;;
        --attach)
            DETACH=false
            shift
            ;;
        *)
            ;;
    esac
done

# Helper functions
print_header() {
    echo -e "\n${BLUE}===================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

wait_for_service() {
    local service=$1
    local max_wait=${2:-60}
    local counter=0

    echo -n "Waiting for $service to be ready"
    while [ $counter -lt $max_wait ]; do
        if docker ps --filter "name=$service" --filter "status=running" | grep -q "$service"; then
            echo ""
            print_success "$service is running"
            return 0
        fi
        echo -n "."
        sleep 1
        counter=$((counter + 1))
    done

    echo ""
    print_error "$service failed to start within ${max_wait}s"
    return 1
}

# Banner
print_header "Archive-AI v7.5 Startup"

if [ "$PROD_MODE" = true ]; then
    print_info "Production mode enabled"
    COMPOSE_FILE="docker-compose.prod.yml"
else
    print_info "Development mode"
    COMPOSE_FILE="docker-compose.yml"
fi

COMPOSE_FILES="-f $COMPOSE_FILE"
if [ -n "$EXTRA_COMPOSE_FILE" ]; then
    print_info "Using extra compose file: $EXTRA_COMPOSE_FILE"
    COMPOSE_FILES="$COMPOSE_FILES -f $EXTRA_COMPOSE_FILE"
fi

# Step 1: Pre-flight checks
print_header "Step 1: Pre-flight Checks"

# Check if .env exists
if [ ! -f .env ]; then
    print_error ".env file not found"
    echo "Run: cp .env.example .env"
    echo "Then edit .env with your configuration"
    exit 1
fi
print_success ".env file exists"

# Check if docker-compose file exists
if [ ! -f "$COMPOSE_FILE" ]; then
    print_error "$COMPOSE_FILE not found"
    exit 1
fi
print_success "$COMPOSE_FILE found"

# Check if Vorpal model exists
if [ -d "models/vorpal" ] && [ "$(ls -A models/vorpal)" ]; then
    print_success "Vorpal model directory contains files"
else
    print_warning "Vorpal model directory is empty or missing"
    echo "Vorpal service may fail to start without a model"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check GPU availability
if command -v nvidia-smi &> /dev/null; then
    GPU_INFO=$(nvidia-smi --query-gpu=name,memory.free --format=csv,noheader | head -1)
    print_success "GPU available: $GPU_INFO"
else
    print_warning "nvidia-smi not found - GPU may not be available"
fi

# Step 2: Rebuild images (if requested)
if [ "$REBUILD" = true ]; then
    print_header "Step 2: Rebuilding Docker Images"
    docker-compose $COMPOSE_FILES build
    print_success "Images rebuilt"
fi

# Step 3: Stop existing services
print_header "Step 3: Stopping Existing Services"

if docker-compose $COMPOSE_FILES ps | grep -q "Up"; then
    print_info "Stopping running services..."
    docker-compose $COMPOSE_FILES down
    print_success "Services stopped"
else
    print_info "No running services to stop"
fi

# Step 4: Start services
print_header "Step 4: Starting Services"

print_info "Starting services..."
echo ""

if [ "$DETACH" = true ]; then
    docker-compose $COMPOSE_FILES up -d

    # Wait for services to start
    sleep 2

    # Check each service
    print_info "Verifying service startup..."
    echo ""

    # Redis
    wait_for_service "redis" 30

    # Vorpal
    wait_for_service "vorpal" 60

    # Brain
    wait_for_service "brain" 30

    # Sandbox
    wait_for_service "sandbox" 20

    # Voice
    wait_for_service "voice" 60

    # Librarian
    wait_for_service "librarian" 20

else
    print_warning "Starting in attached mode (logs will stream)"
    print_info "Press Ctrl+C to stop all services"
    docker-compose $COMPOSE_FILES up
    exit 0
fi

# Step 5: Service status
print_header "Step 5: Service Status"

docker-compose $COMPOSE_FILES ps

# Step 6: Health check
print_header "Step 6: Quick Health Check"

sleep 3  # Give services a moment to initialize

# Check Brain health endpoint
if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
    print_success "Brain health endpoint responding"
else
    print_warning "Brain health endpoint not responding yet"
fi

# Check Vorpal
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    print_success "Vorpal health endpoint responding"
else
    print_warning "Vorpal health endpoint not responding yet (may still be loading model)"
fi

# Step 7: Final summary
print_header "Startup Complete!"

echo ""
echo "Services running:"
echo "  • Brain (API):     http://localhost:8080"
echo "  • Vorpal (LLM):    http://localhost:8000 (internal)"
echo "  • Redis:           localhost:6379 (internal)"
echo "  • Voice:           http://localhost:8001 (internal)"
echo "  • Sandbox:         http://localhost:8003 (internal)"
echo "  • RedisInsight UI: http://localhost:8002"
echo ""
echo "Next steps:"
echo "  1. Run comprehensive health check:"
echo "     bash scripts/health-check.sh"
echo ""
echo "  2. Start Web UI:"
echo "     cd ui && python3 -m http.server 8888"
echo "     Open http://localhost:8888"
echo ""
echo "  3. View API docs:"
echo "     http://localhost:8080/docs"
echo ""
echo "  4. View logs:"
echo "     docker-compose -f $COMPOSE_FILE logs -f"
echo ""
echo "  5. Stop services:"
echo "     docker-compose -f $COMPOSE_FILE down"
echo ""

print_success "Archive-AI is running!"
