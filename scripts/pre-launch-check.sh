#!/bin/bash
#
# Archive-AI Pre-Launch Check
# Comprehensive validation before inaugural launch
#
# Usage: bash scripts/pre-launch-check.sh [--prod]
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
PROD_MODE=false
if [[ "$1" == "--prod" ]]; then
    PROD_MODE=true
fi

TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

# Helper functions
print_header() {
    echo -e "\n${BLUE}===================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
}

print_error() {
    echo -e "${RED}✗${NC} $1"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
    WARNING_CHECKS=$((WARNING_CHECKS + 1))
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
}

print_info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

print_section() {
    echo -e "${MAGENTA}→${NC} $1"
}

# Banner
clear
echo -e "${CYAN}"
cat << "EOF"
    ___              __    _              ___    ____
   /   |  __________/ /_  (_)   _____   /   |  /  _/
  / /| | / ___/ ___/ __ \/ / | / / _ \ / /| |  / /
 / ___ |/ /  / /__/ / / / /| |/ /  __// ___ |_/ /
/_/  |_/_/   \___/_/ /_/_/ |___/\___/_/  |_/___/

         Pre-Launch Validation System
              Version 7.5
EOF
echo -e "${NC}"

if [ "$PROD_MODE" = true ]; then
    print_info "Mode: Production"
    COMPOSE_FILE="docker-compose.prod.yml"
else
    print_info "Mode: Development"
    COMPOSE_FILE="docker-compose.yml"
fi

echo ""

# TEST 1: System Prerequisites
print_header "Test 1: System Prerequisites"

print_section "Checking required software..."

# Docker
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | grep -oP '\d+\.\d+\.\d+' | head -1)
    DOCKER_MAJOR=$(echo $DOCKER_VERSION | cut -d'.' -f1)
    if [ "$DOCKER_MAJOR" -ge 24 ]; then
        print_success "Docker $DOCKER_VERSION (>= 24.0 required)"
    else
        print_warning "Docker $DOCKER_VERSION (upgrade recommended, 24.0+)"
    fi
else
    print_error "Docker not found (required)"
fi

# Docker Compose
if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version | grep -oP '\d+\.\d+\.\d+' | head -1)
    print_success "Docker Compose $COMPOSE_VERSION"
else
    print_error "Docker Compose not found (required)"
fi

# GPU Check
if command -v nvidia-smi &> /dev/null; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)
    GPU_VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader | head -1)
    print_success "GPU: $GPU_NAME ($GPU_VRAM)"

    # Check VRAM
    VRAM_MB=$(echo $GPU_VRAM | grep -oP '\d+')
    if [ "$VRAM_MB" -ge 16000 ]; then
        print_success "GPU VRAM: $GPU_VRAM (>= 16GB required)"
    else
        print_error "GPU VRAM: $GPU_VRAM (insufficient, 16GB+ required)"
    fi
else
    print_error "nvidia-smi not found (GPU required for Vorpal)"
fi

# NVIDIA Container Toolkit
if docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
    print_success "NVIDIA Container Toolkit working"
else
    print_error "NVIDIA Container Toolkit not working"
fi

# System RAM
TOTAL_RAM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
TOTAL_RAM_GB=$((TOTAL_RAM_KB / 1024 / 1024))
if [ "$TOTAL_RAM_GB" -ge 32 ]; then
    print_success "System RAM: ${TOTAL_RAM_GB}GB (>= 32GB required)"
else
    print_warning "System RAM: ${TOTAL_RAM_GB}GB (32GB+ recommended)"
fi

# Disk space
AVAILABLE_DISK=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')
if [ "$AVAILABLE_DISK" -ge 50 ]; then
    print_success "Available disk space: ${AVAILABLE_DISK}GB (>= 50GB required)"
else
    print_warning "Available disk space: ${AVAILABLE_DISK}GB (50GB+ recommended)"
fi

# TEST 2: Configuration Files
print_header "Test 2: Configuration Files"

print_section "Checking configuration files..."

# .env file
if [ -f .env ]; then
    print_success ".env file exists"

    # Check critical variables
    if grep -q "REDIS_PASSWORD=changeme" .env; then
        print_error "REDIS_PASSWORD still set to default 'changeme'"
    elif grep -q "REDIS_PASSWORD=" .env && [ -n "$(grep REDIS_PASSWORD .env | cut -d'=' -f2)" ]; then
        print_success "REDIS_PASSWORD is configured"
    else
        print_error "REDIS_PASSWORD not set in .env"
    fi

    # Check LIBRARY_DROP
    if grep -q "LIBRARY_DROP=" .env; then
        LIBRARY_DROP=$(grep LIBRARY_DROP .env | cut -d'=' -f2)
        print_success "LIBRARY_DROP configured: $LIBRARY_DROP"
    else
        print_warning "LIBRARY_DROP not set (will use default)"
    fi
else
    print_error ".env file not found (copy from .env.example)"
fi

# Docker compose file
if [ -f "$COMPOSE_FILE" ]; then
    print_success "$COMPOSE_FILE exists"

    # Validate YAML syntax
    if docker-compose -f "$COMPOSE_FILE" config > /dev/null 2>&1; then
        print_success "$COMPOSE_FILE syntax valid"
    else
        print_error "$COMPOSE_FILE has syntax errors"
    fi
else
    print_error "$COMPOSE_FILE not found"
fi

# TEST 3: Directory Structure
print_header "Test 3: Directory Structure"

print_section "Checking required directories..."

# Data directories
for dir in data/redis data/archive data/library; do
    if [ -d "$dir" ]; then
        print_success "$dir exists"
    else
        print_warning "$dir missing (will be created)"
    fi
done

# Model directories
for dir in models/vorpal models/whisper models/f5-tts; do
    if [ -d "$dir" ]; then
        print_success "$dir exists"
    else
        print_warning "$dir missing (will be created)"
    fi
done

# Library-Drop
if [ -f .env ]; then
    LIBRARY_DROP=$(grep LIBRARY_DROP .env | cut -d'=' -f2)
    LIBRARY_DROP=${LIBRARY_DROP:-~/ArchiveAI/Library-Drop}
    LIBRARY_DROP_EXPANDED="${LIBRARY_DROP/#\~/$HOME}"

    if [ -d "$LIBRARY_DROP_EXPANDED" ]; then
        print_success "Library-Drop exists: $LIBRARY_DROP_EXPANDED"
    else
        print_warning "Library-Drop missing: $LIBRARY_DROP_EXPANDED (will be created)"
    fi
fi

# TEST 4: Model Files
print_header "Test 4: Model Files"

print_section "Checking for required models..."

# Vorpal model (required)
if [ -d "models/vorpal" ] && [ "$(ls -A models/vorpal 2>/dev/null)" ]; then
    MODEL_SIZE=$(du -sh models/vorpal 2>/dev/null | cut -f1)
    print_success "Vorpal model found (${MODEL_SIZE})"

    # Check for config.json
    if [ -f "models/vorpal/config.json" ]; then
        print_success "Vorpal config.json found"
    else
        print_warning "Vorpal config.json not found (may cause issues)"
    fi
else
    print_error "Vorpal model NOT FOUND (required for launch)"
    echo "       Download: Llama-3-8B-Instruct (EXL2 4.0bpw)"
    echo "       Place in: ./models/vorpal/"
    echo "       See: models/README.md"
fi

# Whisper (auto-download)
if [ -d "models/whisper" ] && [ "$(ls -A models/whisper 2>/dev/null)" ]; then
    print_info "Whisper models present (will use cached)"
else
    print_info "Whisper models will auto-download on first use"
fi

# F5-TTS (auto-download)
if [ -d "models/f5-tts" ] && [ "$(ls -A models/f5-tts 2>/dev/null)" ]; then
    print_info "F5-TTS models present (will use cached)"
else
    print_info "F5-TTS models will auto-download on first use"
fi

# TEST 5: Port Availability
print_header "Test 5: Port Availability"

print_section "Checking for port conflicts..."

PORTS=(6379 8000 8001 8002 8003 8080)
PORT_NAMES=("Redis" "Vorpal" "Voice" "RedisInsight" "Sandbox" "Brain")

for i in "${!PORTS[@]}"; do
    PORT=${PORTS[$i]}
    NAME=${PORT_NAMES[$i]}

    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        PROCESS=$(lsof -Pi :$PORT -sTCP:LISTEN | tail -1 | awk '{print $1}')
        print_warning "Port $PORT ($NAME) in use by $PROCESS"
    else
        print_success "Port $PORT ($NAME) available"
    fi
done

# TEST 6: Docker Images
print_header "Test 6: Docker Images"

print_section "Checking Docker images..."

SERVICES=(redis vorpal brain sandbox voice librarian)

for service in "${SERVICES[@]}"; do
    if docker images | grep -q "archive.*$service"; then
        print_info "$service image exists (will use existing)"
    else
        print_info "$service image not found (will build on start)"
    fi
done

# TEST 7: Network Connectivity
print_header "Test 7: Network Connectivity"

print_section "Checking network connectivity..."

# Check internet (for model downloads)
if ping -c 1 -W 2 8.8.8.8 > /dev/null 2>&1; then
    print_success "Internet connectivity available"
else
    print_warning "No internet connectivity (may prevent model downloads)"
fi

# Check HuggingFace (for Whisper/F5-TTS)
if curl -s --max-time 5 https://huggingface.co > /dev/null 2>&1; then
    print_success "HuggingFace accessible (for model downloads)"
else
    print_warning "HuggingFace not accessible (may prevent model downloads)"
fi

# TEST 8: Existing Services
print_header "Test 8: Existing Services"

print_section "Checking for running Archive-AI services..."

if docker ps --format '{{.Names}}' | grep -q "archive"; then
    print_warning "Archive-AI containers already running:"
    docker ps --format "       - {{.Names}} ({{.Status}})" | grep archive
    echo ""
    print_info "Run 'docker-compose down' to stop before launch"
else
    print_success "No Archive-AI containers running"
fi

# TEST 9: File Permissions
print_header "Test 9: File Permissions"

print_section "Checking file permissions..."

# Scripts
SCRIPT_COUNT=0
for script in scripts/*.sh; do
    if [ -x "$script" ]; then
        SCRIPT_COUNT=$((SCRIPT_COUNT + 1))
    fi
done

if [ "$SCRIPT_COUNT" -gt 0 ]; then
    print_success "$SCRIPT_COUNT executable scripts found"
else
    print_warning "No executable scripts found (run: chmod +x scripts/*.sh)"
fi

# Data directories writable
if [ -w data/ ]; then
    print_success "data/ directory is writable"
else
    print_error "data/ directory not writable"
fi

# TEST 10: Build Test (Optional)
print_header "Test 10: Build Test (Quick)"

print_section "Testing Docker build capability..."

# Try to build brain service (quickest)
if docker-compose -f "$COMPOSE_FILE" build brain > /dev/null 2>&1; then
    print_success "Docker build test passed (brain service)"
else
    print_warning "Docker build test failed (check Dockerfiles)"
fi

# FINAL SUMMARY
print_header "Pre-Launch Summary"

echo -e "${CYAN}Test Results:${NC}"
echo "  Total Checks:   $TOTAL_CHECKS"
echo -e "  ${GREEN}Passed:${NC}         $PASSED_CHECKS"
echo -e "  ${RED}Failed:${NC}         $FAILED_CHECKS"
echo -e "  ${YELLOW}Warnings:${NC}       $WARNING_CHECKS"
echo ""

# Determine readiness
if [ $FAILED_CHECKS -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                            ║${NC}"
    echo -e "${GREEN}║    ✓ READY FOR LAUNCH                     ║${NC}"
    echo -e "${GREEN}║                                            ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
    echo ""

    if [ $WARNING_CHECKS -gt 0 ]; then
        print_info "Launch is possible, but $WARNING_CHECKS warnings detected"
        echo "Review warnings above before proceeding"
    else
        print_success "All systems nominal - ready for inaugural launch!"
    fi

    echo ""
    echo "To launch Archive-AI:"
    if [ "$PROD_MODE" = true ]; then
        echo "  bash scripts/start.sh --prod"
    else
        echo "  bash scripts/start.sh"
    fi
    echo ""

    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                                            ║${NC}"
    echo -e "${RED}║    ✗ NOT READY FOR LAUNCH                 ║${NC}"
    echo -e "${RED}║                                            ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════╝${NC}"
    echo ""

    echo -e "${RED}Critical issues detected:${NC}"
    echo "  $FAILED_CHECKS failed check(s) must be resolved"
    echo ""
    echo "Common fixes:"
    echo "  • Install Docker & Docker Compose"
    echo "  • Install NVIDIA drivers & Container Toolkit"
    echo "  • Create .env file: cp .env.example .env"
    echo "  • Download Vorpal model to models/vorpal/"
    echo "  • Stop conflicting services on required ports"
    echo ""

    exit 1
fi
