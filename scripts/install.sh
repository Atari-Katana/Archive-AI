#!/bin/bash
#
# Archive-AI Installation Script
# Automates the setup process for Archive-AI v7.5
#
# Usage: bash scripts/install.sh [--prod]
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
if [[ "$1" == "--prod" ]]; then
    PROD_MODE=true
fi

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

check_command() {
    if command -v "$1" &> /dev/null; then
        print_success "$1 is installed"
        return 0
    else
        print_error "$1 is not installed"
        return 1
    fi
}

# Banner
print_header "Archive-AI v7.5 Installation"
if [ "$PROD_MODE" = true ]; then
    print_info "Production mode enabled"
else
    print_info "Development mode (use --prod for production)"
fi

# Step 1: Check prerequisites
print_header "Step 1: Checking Prerequisites"

MISSING_DEPS=false

# Check Docker
if check_command docker; then
    DOCKER_VERSION=$(docker --version | grep -oP '\d+\.\d+\.\d+' | head -1)
    print_info "Docker version: $DOCKER_VERSION"
else
    MISSING_DEPS=true
fi

# Check Docker Compose
if check_command docker-compose; then
    COMPOSE_VERSION=$(docker-compose --version | grep -oP '\d+\.\d+\.\d+' | head -1)
    print_info "Docker Compose version: $COMPOSE_VERSION"
else
    MISSING_DEPS=true
fi

# Check NVIDIA SMI (GPU)
if check_command nvidia-smi; then
    GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1)
    print_info "GPU: $GPU_INFO"
else
    print_warning "nvidia-smi not found - GPU support may not be available"
fi

# Check if NVIDIA Container Toolkit is available
if docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
    print_success "NVIDIA Container Toolkit is working"
else
    print_warning "NVIDIA Container Toolkit may not be configured properly"
fi

if [ "$MISSING_DEPS" = true ]; then
    print_error "Missing required dependencies. Please install them first."
    echo ""
    echo "Installation guides:"
    echo "  Docker: https://docs.docker.com/engine/install/"
    echo "  Docker Compose: https://docs.docker.com/compose/install/"
    echo "  NVIDIA Container Toolkit: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
    exit 1
fi

# Step 2: Create environment file
print_header "Step 2: Creating Environment Configuration"

if [ -f .env ]; then
    print_warning ".env file already exists"
    read -p "Overwrite? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Keeping existing .env file"
    else
        cp .env.example .env
        print_success "Created new .env from template"
    fi
else
    cp .env.example .env
    print_success "Created .env from template"
fi

# Generate Redis password if not set
if grep -q "REDIS_PASSWORD=changeme" .env || grep -q "REDIS_PASSWORD=$" .env; then
    print_info "Generating secure Redis password..."
    REDIS_PASS=$(openssl rand -base64 32)
    sed -i "s/REDIS_PASSWORD=.*/REDIS_PASSWORD=$REDIS_PASS/" .env
    print_success "Generated Redis password"
fi

print_warning "Please review and customize .env file before starting services"

# Step 3: Create required directories
print_header "Step 3: Creating Data Directories"

mkdir -p data/redis
print_success "Created data/redis"

mkdir -p data/archive
print_success "Created data/archive"

mkdir -p data/library
print_success "Created data/library"

mkdir -p models/vorpal
print_success "Created models/vorpal"

mkdir -p models/whisper
print_success "Created models/whisper"

mkdir -p models/f5-tts
print_success "Created models/f5-tts"

mkdir -p models/goblin
print_success "Created models/goblin"

# Create Library-Drop directory
LIBRARY_DROP=$(grep LIBRARY_DROP .env | cut -d'=' -f2)
LIBRARY_DROP=${LIBRARY_DROP:-~/ArchiveAI/Library-Drop}
LIBRARY_DROP_EXPANDED="${LIBRARY_DROP/#\~/$HOME}"

mkdir -p "$LIBRARY_DROP_EXPANDED"
print_success "Created Library-Drop: $LIBRARY_DROP_EXPANDED"

# Step 4: Check for Vorpal model
print_header "Step 4: Checking Models"

if [ -d "models/vorpal" ] && [ "$(ls -A models/vorpal)" ]; then
    print_success "Vorpal model directory is not empty"
else
    print_warning "Vorpal model directory is empty"
    echo ""
    echo "You need to download Llama-3-8B-Instruct (EXL2 4.0bpw) and place it in:"
    echo "  ./models/vorpal/"
    echo ""
    echo "Recommended source: https://huggingface.co/turboderp"
fi

print_info "Whisper models will auto-download on first use"
print_info "F5-TTS models will auto-download on first use"

# Check for Goblin model
echo ""
if [ -f "models/goblin/DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf" ]; then
    print_success "Goblin model found"
else
    print_warning "Goblin model not found"
    echo ""
    echo "The Goblin reasoning engine requires a 7B GGUF model (~8.4GB)."
    echo "This is needed for dual-engine mode (Vorpal + Goblin)."
    echo ""
    read -p "Download Goblin model now? (Y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
        print_info "Downloading Goblin model..."
        python3 scripts/download-models.py --model goblin-7b
        if [ $? -eq 0 ]; then
            print_success "Goblin model downloaded successfully"
        else
            print_error "Download failed. You can run this later:"
            echo "  python3 scripts/download-models.py --model goblin-7b"
        fi
    else
        print_info "Skipping Goblin download. You can download later with:"
        echo "  python3 scripts/download-models.py --model goblin-7b"
        echo ""
        print_warning "Without Goblin, only single-engine mode will be available"
    fi
fi

# Step 5: Build Docker images
print_header "Step 5: Building Docker Images"

if [ "$PROD_MODE" = true ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
else
    COMPOSE_FILE="docker-compose.yml"
fi

print_info "Building images using $COMPOSE_FILE..."
docker-compose -f "$COMPOSE_FILE" build

print_success "Docker images built successfully"

# Step 6: Set permissions
print_header "Step 6: Setting Permissions"

chmod 755 scripts/*.sh 2>/dev/null || true
print_success "Made scripts executable"

# Ensure data directories are writable
chmod -R 755 data/ 2>/dev/null || true
print_success "Set data directory permissions"

# Step 7: Installation summary
print_header "Installation Complete!"

echo ""
echo "Next steps:"
echo ""
echo "1. Review configuration:"
echo "   nano .env"
echo ""
echo "2. Download Vorpal model (if not done):"
echo "   Place Llama-3-8B-Instruct (EXL2 4.0bpw) in ./models/vorpal/"
echo ""
echo "3. Start services:"
if [ "$PROD_MODE" = true ]; then
    echo "   bash scripts/start.sh --prod"
else
    echo "   bash scripts/start.sh"
fi
echo ""
echo "4. Check health:"
echo "   bash scripts/health-check.sh"
echo ""
echo "5. Access Web UI:"
echo "   cd ui && python3 -m http.server 8888"
echo "   Open http://localhost:8888"
echo ""

print_info "Documentation:"
echo "  - Quick Start: README.md"
echo "  - Deployment: DEPLOYMENT.md"
echo "  - Performance: PERFORMANCE.md"
echo ""

print_success "Installation ready!"
