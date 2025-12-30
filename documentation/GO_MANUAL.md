# Archive-AI Installation and Operations Manual

**Version:** 7.5
**Last Updated:** 2025-12-30
**For:** System Administrators and Users

---

## Table of Contents

1. [Introduction](#introduction)
2. [System Requirements](#system-requirements)
3. [Installation](#installation)
4. [First-Time Setup](#first-time-setup)
5. [Starting Services](#starting-services)
6. [Stopping Services](#stopping-services)
7. [Health Checks](#health-checks)
8. [Configuration Options](#configuration-options)
9. [Model Management](#model-management)
10. [Troubleshooting Startup Issues](#troubleshooting-startup-issues)
11. [Backup Procedures](#backup-procedures)
12. [Update and Upgrade](#update-and-upgrade)
13. [Advanced Operations](#advanced-operations)

---

## Introduction

This manual provides comprehensive guidance for installing, configuring, and operating Archive-AI. Whether you're setting up for the first time or managing an existing installation, this guide will help you succeed.

### What You'll Learn

- How to install Archive-AI from scratch
- Starting and stopping services correctly
- Verifying system health
- Managing configurations
- Troubleshooting common issues
- Maintaining and upgrading your system

### Quick Start

For experienced users, here's the express version:

```bash
# Clone repository
git clone https://github.com/your-repo/Archive-AI.git
cd Archive-AI

# Run installation script
bash scripts/install.sh

# Download models (manual step - see Model Management)
# Place models in models/vorpal/ and models/goblin/

# Start services
bash scripts/start.sh

# Check health
bash scripts/health-check.sh

# Access web UI
cd ui && python3 -m http.server 8888
# Open http://localhost:8888
```

---

## System Requirements

### Hardware Requirements

**Minimum Configuration:**
- CPU: 8 cores (Intel/AMD x86_64)
- RAM: 32GB system memory
- GPU: NVIDIA GPU with 16GB VRAM (RTX 4060 Ti 16GB or better)
- Storage: 100GB free disk space (SSD recommended)

**Recommended Configuration:**
- CPU: 12+ cores
- RAM: 64GB system memory
- GPU: NVIDIA RTX 5060 Ti 16GB or RTX 4090
- Storage: 256GB+ SSD

**VRAM Allocation:**
```
Vorpal (vLLM):     ~7.7GB  (with Goblin disabled)
                   ~3.5GB  (with Goblin enabled)
Goblin (llama.cpp): ~8-10GB (when enabled)
OS/CUDA overhead:   ~2.5GB
Total VRAM used:    ~13.5-15GB
```

### Software Requirements

**Operating System:**
- Ubuntu 22.04 LTS (recommended)
- Ubuntu 20.04 LTS
- Debian 11+
- Other Linux distributions (may require adjustments)

**Required Software:**
- Docker 24.0+
- Docker Compose 2.20+
- NVIDIA Driver 535+
- NVIDIA Container Toolkit
- Git
- Python 3.11+ (for UI server)

**Optional Software:**
- nvidia-smi (GPU monitoring)
- htop (system monitoring)
- redis-cli (Redis debugging)

### Network Requirements

**Ports Used:**
- 6379: Redis database
- 8000: Vorpal (vLLM inference)
- 8001: Voice service (STT/TTS)
- 8002: RedisInsight web UI
- 8003: Sandbox (code execution)
- 8080: Brain (main API)
- 8081: Goblin (llama.cpp inference)
- 8888: Web UI (static file server)

**Firewall Rules:**
- If running locally: No firewall changes needed
- If exposing externally: Secure appropriately (beyond scope of this manual)

---

## Installation

### Step 1: Verify Prerequisites

Check that all required software is installed:

```bash
# Check Docker
docker --version
# Expected: Docker version 24.0.0 or higher

# Check Docker Compose
docker-compose --version
# Expected: Docker Compose version 2.20.0 or higher

# Check NVIDIA Driver
nvidia-smi
# Should show your GPU and driver version (535+)

# Check NVIDIA Container Toolkit
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
# Should show nvidia-smi output from inside container

# Check Git
git --version
# Expected: git version 2.x.x

# Check Python
python3 --version
# Expected: Python 3.11.0 or higher
```

### Step 2: Install Missing Dependencies

**Ubuntu 22.04:**

```bash
# Update package index
sudo apt update

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin

# Install NVIDIA Driver (if not installed)
sudo ubuntu-drivers autoinstall

# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/libnvidia-container/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# Install Python 3.11
sudo apt install python3.11 python3.11-venv

# Log out and back in for Docker group changes to take effect
```

### Step 3: Clone Repository

```bash
# Clone Archive-AI repository
git clone https://github.com/your-repo/Archive-AI.git
cd Archive-AI

# Verify repository structure
ls -la
# Should see: brain/, vorpal/, goblin/, scripts/, docker-compose.yml, etc.
```

### Step 4: Run Installation Script

The installation script automates setup:

```bash
# Run installer (development mode)
bash scripts/install.sh

# Or for production mode
bash scripts/install.sh --prod
```

**What the installer does:**

1. Checks prerequisites
2. Creates `.env` file from template
3. Generates secure Redis password
4. Creates required directories:
   - `data/redis` - Redis persistence
   - `data/archive` - Archived memories
   - `data/library` - Library chunks
   - `models/vorpal` - Vorpal model storage
   - `models/goblin` - Goblin model storage
   - `models/whisper` - Whisper model cache
   - `models/f5-tts` - F5-TTS model cache
   - `~/ArchiveAI/Library-Drop` - Document ingestion
5. Sets directory permissions
6. Builds Docker images

**Expected Output:**

```
==================================================
Archive-AI v7.5 Installation
==================================================

Step 1: Checking Prerequisites
✓ docker is installed
ℹ Docker version: 24.0.5
✓ docker-compose is installed
ℹ Docker Compose version: 2.21.0
✓ nvidia-smi is installed
ℹ GPU: NVIDIA GeForce RTX 5060 Ti, 16384 MiB

Step 2: Creating Environment Configuration
✓ Created .env from template
✓ Generated Redis password

Step 3: Creating Data Directories
✓ Created data/redis
✓ Created data/archive
✓ Created data/library
✓ Created models/vorpal
✓ Created models/whisper
✓ Created models/f5-tts
✓ Created Library-Drop: /home/user/ArchiveAI/Library-Drop

Step 4: Checking Models
⚠ Vorpal model directory is empty
  You need to download Llama-3-8B-Instruct (EXL2 4.0bpw)

Step 5: Building Docker Images
[Building images...]
✓ Docker images built successfully

Step 6: Setting Permissions
✓ Made scripts executable
✓ Set data directory permissions

==================================================
Installation Complete!
==================================================
```

---

## First-Time Setup

### Configure Environment Variables

Edit the `.env` file to customize your installation:

```bash
# Open .env in your editor
nano .env
```

**Key Configuration Options:**

```bash
# Redis Configuration
REDIS_PASSWORD=<auto-generated-secure-password>  # Don't change
REDIS_URL=redis://redis:6379

# Vorpal Engine (Speed)
VORPAL_MODEL=Qwen/Qwen2.5-3B-Instruct
VORPAL_GPU_MEMORY_UTILIZATION=0.50  # Use 50% of VRAM
VORPAL_MAX_MODEL_LEN=8192

# Goblin Engine (Capacity) - Optional
GOBLIN_MODEL_PATH=/models/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf
GOBLIN_N_GPU_LAYERS=28
GOBLIN_CTX_SIZE=8192

# Brain (Orchestrator)
BRAIN_URL=http://brain:8080
ASYNC_MEMORY=true

# Voice Service
WHISPER_MODEL=base  # Options: tiny, base, small, medium, large
WHISPER_DEVICE=cpu  # Options: cpu, cuda
TTS_DEVICE=cpu      # Options: cpu, cuda

# Library Ingestion
LIBRARY_DROP=~/ArchiveAI/Library-Drop

# Logging
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR
```

**Save and exit** (Ctrl+O, Enter, Ctrl+X in nano)

### Download Models

Models must be downloaded manually due to their size.

**Vorpal Model (Required):**

Option 1: AWQ 7B (Recommended - used by go.sh)
```bash
# Download Qwen2.5-7B-Instruct-AWQ
# This is handled automatically by docker pull in go.sh
# No manual download needed!
```

Option 2: Local EXL2 model (Advanced)
```bash
# Download from HuggingFace (example)
git lfs install
cd models/vorpal
git clone https://huggingface.co/turboderp/Llama-3-8B-Instruct-exl2-4.0bpw .

# Or use huggingface-cli
huggingface-cli download turboderp/Llama-3-8B-Instruct-exl2-4.0bpw --local-dir models/vorpal
```

**Goblin Model (Optional - for reasoning tasks):**

```bash
# Download DeepSeek-R1-Distill-Qwen-14B
cd models/goblin
wget https://huggingface.co/TheBloke/DeepSeek-R1-Distill-Qwen-14B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf

# Or use huggingface-cli
huggingface-cli download TheBloke/DeepSeek-R1-Distill-Qwen-14B-GGUF \
  DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf --local-dir models/goblin
```

**Whisper & F5-TTS Models:**
These auto-download on first use. No manual download needed.

**Verify Model Files:**

```bash
# Check Vorpal model
ls -lh models/vorpal/
# Should show model files (varies by model)

# Check Goblin model (if using)
ls -lh models/goblin/
# Should show .gguf file (~8-10GB)
```

---

## Starting Services

Archive-AI provides two startup scripts:

### Option 1: Quick Start with go.sh (Recommended)

The `go.sh` script is the easiest way to get started:

```bash
# Start everything with one command
bash go.sh
```

**What go.sh does:**

1. Starts Docker services with AWQ overlay
2. Starts UI server in background
3. Waits for interrupt (Ctrl+C)
4. Cleans up on exit

**Benefits:**
- Single command startup
- Automatic cleanup on exit
- Optimized for AWQ 7B model
- UI server included

**Expected Output:**

```
==================================================
Archive-AI v7.5 Startup
==================================================

Starting services...
[+] Running 7/7
 ✔ Container redis       Started
 ✔ Container vorpal      Started
 ✔ Container goblin      Started
 ✔ Container brain       Started
 ✔ Container sandbox     Started
 ✔ Container voice       Started
 ✔ Container librarian   Started

UI server started at http://localhost:8888
Press Ctrl+C to stop all services
```

### Option 2: Manual Start with start.sh (Advanced)

For more control, use `start.sh`:

```bash
# Development mode (default)
bash scripts/start.sh

# Production mode
bash scripts/start.sh --prod

# Rebuild images before starting
bash scripts/start.sh --rebuild

# Attach to logs (foreground mode)
bash scripts/start.sh --attach
```

**What start.sh does:**

1. Pre-flight checks (verifies .env, models, GPU)
2. Stops existing services
3. Starts Docker Compose services
4. Waits for services to be ready
5. Runs quick health check
6. Displays next steps

**Expected Output:**

```
==================================================
Archive-AI v7.5 Startup
==================================================

ℹ Development mode

==================================================
Step 1: Pre-flight Checks
==================================================

✓ .env file exists
✓ docker-compose.yml found
✓ Vorpal model directory contains files
✓ GPU available: NVIDIA GeForce RTX 5060 Ti, 15823MiB

==================================================
Step 3: Stopping Existing Services
==================================================

ℹ No running services to stop

==================================================
Step 4: Starting Services
==================================================

[+] Running 7/7
 ✔ Container redis       Started
 ✔ Container vorpal      Started
 ✔ Container brain       Started
 ✔ Container sandbox     Started
 ✔ Container voice       Started
 ✔ Container librarian   Started

Waiting for redis to be ready.......
✓ redis is running

Waiting for vorpal to be ready........
✓ vorpal is running

Waiting for brain to be ready...
✓ brain is running

==================================================
Step 5: Service Status
==================================================

NAME        IMAGE                    STATUS
redis       redis/redis-stack        Up 30 seconds
vorpal      archive-ai/vorpal        Up 25 seconds
brain       archive-ai/brain         Up 20 seconds
sandbox     archive-ai/sandbox       Up 20 seconds
voice       archive-ai/voice         Up 20 seconds
librarian   archive-ai/librarian     Up 20 seconds

==================================================
Step 6: Quick Health Check
==================================================

✓ Brain health endpoint responding
⚠ Vorpal health endpoint not responding yet (may still be loading model)

==================================================
Startup Complete!
==================================================

Services running:
  • Brain (API):     http://localhost:8080
  • Vorpal (LLM):    http://localhost:8000 (internal)
  • Redis:           localhost:6379 (internal)
  • Voice:           http://localhost:8001 (internal)
  • Sandbox:         http://localhost:8003 (internal)
  • RedisInsight UI: http://localhost:8002

Next steps:
  1. Run comprehensive health check:
     bash scripts/health-check.sh

  2. Start Web UI:
     cd ui && python3 -m http.server 8888
     Open http://localhost:8888

  3. View API docs:
     http://localhost:8080/docs

  4. View logs:
     docker-compose -f docker-compose.yml logs -f

  5. Stop services:
     docker-compose -f docker-compose.yml down

✓ Archive-AI is running!
```

### Starting Individual Services

To start specific services only:

```bash
# Start just Redis and Brain
docker-compose up -d redis brain

# Start all except Goblin
docker-compose up -d redis vorpal brain sandbox voice librarian

# Start with specific compose file
docker-compose -f docker-compose.prod.yml up -d
```

### Starting the Web UI

After services are running:

```bash
# In a new terminal
cd ui
python3 -m http.server 8888

# Or use Python 2
python -m SimpleHTTPServer 8888

# Access UI
# Open browser to http://localhost:8888
```

---

## Stopping Services

### Using go.sh

If started with `go.sh`, simply press **Ctrl+C**:

```bash
# Press Ctrl+C
^C
# Cleanup happens automatically
```

### Using Docker Compose

For manual control:

```bash
# Graceful shutdown (preserves data)
docker-compose down

# Or with specific compose file
docker-compose -f docker-compose.yml down

# Stop but don't remove containers (faster restart)
docker-compose stop

# Stop specific service
docker-compose stop brain

# Force stop (not recommended)
docker-compose kill
```

### Complete Cleanup

To remove all containers, networks, and volumes:

```bash
# WARNING: This removes data volumes!
docker-compose down -v

# To also remove images
docker-compose down -v --rmi all
```

### Stopping Web UI

If started separately:

```bash
# Find Python HTTP server process
ps aux | grep "http.server 8888"

# Kill it
kill <PID>

# Or if started with go.sh, it stops automatically
```

---

## Health Checks

### Quick Health Check

Built into `start.sh`, or run manually:

```bash
# Check if services are responding
curl http://localhost:8080/health
curl http://localhost:8000/health
```

### Comprehensive Health Check

Run the full health check script:

```bash
# Full health check
bash scripts/health-check.sh

# Quick mode (basic checks only)
bash scripts/health-check.sh --quick

# Watch mode (continuous monitoring)
bash scripts/health-check.sh --watch
```

**Full Health Check Output:**

```
==================================================
Archive-AI v7.5 Health Check
==================================================

Mon Dec 30 10:30:45 UTC 2025

==================================================
1. Docker Container Status
==================================================

✓ redis container running (0.15% CPU, 245MiB / 24GiB)
✓ vorpal container running (45.23% CPU, 8.2GiB / 16GiB)
✓ brain container running (2.34% CPU, 512MiB / 16GiB)
✓ sandbox container running (0.01% CPU, 128MiB / 16GiB)
✓ voice container running (0.05% CPU, 1.1GiB / 16GiB)
✓ librarian container running (1.23% CPU, 256MiB / 16GiB)

==================================================
2. Service Health Endpoints
==================================================

✓ Brain is healthy
✓ Vorpal is healthy
✓ Sandbox is healthy
✓ Voice is healthy
✓ Redis is responding to PING

==================================================
3. Brain API Endpoints
==================================================

✓ Brain Metrics is healthy
    {
      "uptime_seconds": 1847,
      "memory_stats": {
        "total_memories": 42
      }
    }

==================================================
4. Resource Usage
==================================================

Container Resources:
NAME        CPU %     MEM USAGE / LIMIT      MEM %
redis       0.15%     245MiB / 24GiB         1.02%
vorpal      45.23%    8.2GiB / 16GiB        51.25%
brain       2.34%     512MiB / 16GiB         3.20%
sandbox     0.01%     128MiB / 16GiB         0.80%
voice       0.05%     1.1GiB / 16GiB         6.88%
librarian   1.23%     256MiB / 16GiB         1.60%

GPU Usage:
  NVIDIA GeForce RTX 5060 Ti: 8456MiB / 16384MiB (75% utilization)

Redis Memory:
  used_memory_human:185.23M
  maxmemory_human:20.00G

==================================================
5. Disk Usage
==================================================

Data Directories:
  1.2G    data/redis
  45M     data/library
  12M     data/archive

==================================================
6. Recent Errors in Logs
==================================================

✓ No errors found in recent logs

==================================================
7. Memory System Status
==================================================

✓ Total memories stored: 42

==================================================
8. Network Connectivity
==================================================

✓ Brain can reach Vorpal
✓ Brain can reach Sandbox

==================================================
9. Service Uptime
==================================================

✓ Brain uptime: 0h 30m

==================================================
Health Check Summary
==================================================

✓ All checks passed! System is healthy.

Summary:
  ✓ All services running
  ✓ All health endpoints responding
  ✓ API accessible
  ✓ Inter-service communication working
  ✓ No critical errors in logs

✓ Archive-AI is operating normally
```

### Individual Service Checks

**Check Brain:**
```bash
curl http://localhost:8080/health
# Expected: {"status": "healthy", "vorpal_model": "..."}
```

**Check Vorpal:**
```bash
curl http://localhost:8000/health
# Expected: {"status": "ok"}
```

**Check Redis:**
```bash
docker exec $(docker ps -qf "name=redis") redis-cli ping
# Expected: PONG
```

**Check GPU:**
```bash
nvidia-smi
# Should show Archive-AI using GPU
```

### Monitoring Logs

**View all logs:**
```bash
docker-compose logs -f
```

**View specific service:**
```bash
docker-compose logs -f brain
docker-compose logs -f vorpal
docker-compose logs -f redis
```

**View recent errors:**
```bash
docker-compose logs --tail=100 | grep -i error
```

---

## Configuration Options

### Environment Variables

All configuration is in `.env` file. Key sections:

**Redis:**
```bash
REDIS_PASSWORD=<secure-password>
REDIS_URL=redis://redis:6379
```

**Vorpal (Speed Engine):**
```bash
VORPAL_MODEL=Qwen/Qwen2.5-3B-Instruct
VORPAL_GPU_MEMORY_UTILIZATION=0.50
VORPAL_MAX_MODEL_LEN=8192
VORPAL_URL=http://vorpal:8000
```

**Goblin (Capacity Engine - Optional):**
```bash
GOBLIN_MODEL_PATH=/models/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf
GOBLIN_N_GPU_LAYERS=28
GOBLIN_CTX_SIZE=8192
GOBLIN_URL=http://goblin:8080
```

**Brain:**
```bash
BRAIN_URL=http://brain:8080
ASYNC_MEMORY=true
SANDBOX_URL=http://sandbox:8000
VOICE_URL=http://voice:8001
```

**Voice:**
```bash
WHISPER_MODEL=base
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
TTS_DEVICE=cpu
```

**Library:**
```bash
LIBRARY_DROP=~/ArchiveAI/Library-Drop
```

### User Config Overrides

Create `config/user-config.env` for local overrides:

```bash
# Create user config
mkdir -p config
nano config/user-config.env
```

**Example overrides:**
```bash
# Use GPU for Whisper
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16

# Increase Vorpal VRAM
VORPAL_GPU_MEMORY_UTILIZATION=0.70

# Change log level
LOG_LEVEL=DEBUG

# Custom library location
LIBRARY_DROP=/mnt/documents/AI-Library
```

**User config takes precedence** over `.env` when using `start.sh`.

### Docker Compose Profiles

Switch between different configurations:

**Development (default):**
```bash
docker-compose -f docker-compose.yml up -d
```

**Production:**
```bash
docker-compose -f docker-compose.prod.yml up -d
```

**AWQ 7B Model:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.awq-7b.yml up -d
# Or simply use: bash go.sh
```

### Customizing Resource Limits

Edit `docker-compose.yml`:

```yaml
services:
  redis:
    deploy:
      resources:
        limits:
          memory: 24G  # Increase Redis memory limit

  vorpal:
    environment:
      - GPU_MEMORY_UTILIZATION=0.60  # Use 60% of GPU instead of 50%
```

---

## Model Management

### Vorpal Models

**Supported Formats:**
- EXL2 (recommended for local models)
- AWQ (recommended - used by go.sh)
- GPTQ
- GGUF (via vLLM)

**Changing Vorpal Model:**

1. Download new model to `models/vorpal/`
2. Update `.env`:
   ```bash
   VORPAL_MODEL=new-model-name
   ```
3. Restart services:
   ```bash
   docker-compose restart vorpal
   ```

**Using Hugging Face Models:**

Many models work directly from HuggingFace:

```bash
# In .env
VORPAL_MODEL=Qwen/Qwen2.5-3B-Instruct  # Downloads automatically

# Or
VORPAL_MODEL=mistralai/Mistral-7B-Instruct-v0.2
```

### Goblin Models

**Supported Format:**
- GGUF only

**Changing Goblin Model:**

1. Download `.gguf` file to `models/goblin/`
2. Update `.env`:
   ```bash
   GOBLIN_MODEL_PATH=/models/new-model-Q4_K_M.gguf
   ```
3. Adjust GPU layers if needed:
   ```bash
   GOBLIN_N_GPU_LAYERS=35  # More layers = more VRAM used
   ```
4. Restart:
   ```bash
   docker-compose restart goblin
   ```

### Voice Models

**Whisper:**

Models auto-download. Change in `.env`:

```bash
WHISPER_MODEL=base  # Options: tiny, base, small, medium, large
```

**Model Sizes:**
- tiny: ~75MB (fastest, least accurate)
- base: ~150MB (good balance - recommended)
- small: ~500MB (better accuracy)
- medium: ~1.5GB (very good)
- large: ~3GB (best accuracy, slowest)

**F5-TTS:**

Uses default pretrained models. Auto-downloads on first use.

### Model Storage Locations

```
models/
├── vorpal/              # Vorpal model files
├── goblin/              # Goblin .gguf files
├── whisper/             # Whisper model cache
│   └── huggingface/
└── f5-tts/              # F5-TTS model cache
    └── ...
```

---

## Troubleshooting Startup Issues

### Service Won't Start

**Check Docker:**
```bash
# Is Docker running?
sudo systemctl status docker

# Start Docker if stopped
sudo systemctl start docker
```

**Check Logs:**
```bash
# View service logs
docker-compose logs <service-name>

# Example
docker-compose logs brain
docker-compose logs vorpal
```

### GPU Not Detected

**Verify GPU access:**
```bash
# Check nvidia-smi
nvidia-smi

# Check Docker GPU access
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

**If not working:**
```bash
# Reinstall NVIDIA Container Toolkit
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### Vorpal Fails to Load Model

**Common causes:**

1. **Model not found:**
   ```bash
   # Check model directory
   ls -la models/vorpal/
   # Should not be empty
   ```

2. **VRAM insufficient:**
   ```bash
   # Reduce VRAM allocation in .env
   VORPAL_GPU_MEMORY_UTILIZATION=0.40
   ```

3. **Wrong model path:**
   ```bash
   # Check VORPAL_MODEL in .env matches actual model
   ```

**View Vorpal logs:**
```bash
docker-compose logs vorpal | tail -50
```

### Brain Can't Connect to Vorpal

**Check network:**
```bash
# Exec into brain container
docker exec -it $(docker ps -qf "name=brain") bash

# Try to reach Vorpal
curl http://vorpal:8000/health

# Exit container
exit
```

**Verify services are on same network:**
```bash
docker network ls
docker network inspect archive-ai_archive-net
```

### Redis Connection Errors

**Check Redis:**
```bash
# Test Redis
docker exec $(docker ps -qf "name=redis") redis-cli ping
# Expected: PONG

# Check Redis logs
docker-compose logs redis
```

**Verify Redis URL:**
```bash
# In .env
REDIS_URL=redis://redis:6379  # Must match service name in docker-compose.yml
```

### Port Already in Use

**Find process using port:**
```bash
# Example for port 8080
sudo lsof -i :8080

# Kill the process
sudo kill -9 <PID>
```

**Or change port in docker-compose.yml:**
```yaml
services:
  brain:
    ports:
      - "8090:8080"  # Use 8090 externally instead
```

### Out of Disk Space

**Check disk usage:**
```bash
df -h

# Check Docker disk usage
docker system df
```

**Clean up:**
```bash
# Remove old containers
docker container prune

# Remove old images
docker image prune -a

# Remove old volumes (BE CAREFUL - loses data)
docker volume prune
```

### Memory Issues

**Check memory:**
```bash
free -h
```

**Reduce memory limits in docker-compose.yml:**
```yaml
services:
  redis:
    environment:
      - REDIS_ARGS=--maxmemory 16gb  # Reduce from 20gb
```

---

## Backup Procedures

### What to Backup

**Critical Data:**
- `data/redis/` - All memories and state
- `.env` - Configuration
- `config/user-config.env` - User overrides (if exists)
- `data/library/` - Processed library chunks

**Optional:**
- `models/` - Large model files (can re-download)
- `data/archive/` - Archived memories

### Backup Script

```bash
#!/bin/bash
# backup-archive-ai.sh

BACKUP_DIR="$HOME/archive-ai-backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="archive-ai-backup-$TIMESTAMP"

# Create backup directory
mkdir -p "$BACKUP_DIR/$BACKUP_NAME"

# Stop services for consistent backup
echo "Stopping services..."
cd /path/to/Archive-AI
docker-compose stop

# Backup data
echo "Backing up data..."
cp -r data/ "$BACKUP_DIR/$BACKUP_NAME/"
cp .env "$BACKUP_DIR/$BACKUP_NAME/"
cp -r config/ "$BACKUP_DIR/$BACKUP_NAME/" 2>/dev/null || true

# Create archive
echo "Creating archive..."
cd "$BACKUP_DIR"
tar -czf "$BACKUP_NAME.tar.gz" "$BACKUP_NAME"
rm -rf "$BACKUP_NAME"

# Restart services
echo "Restarting services..."
cd /path/to/Archive-AI
docker-compose start

echo "Backup complete: $BACKUP_DIR/$BACKUP_NAME.tar.gz"
```

**Usage:**
```bash
chmod +x backup-archive-ai.sh
./backup-archive-ai.sh
```

### Live Backup (No Downtime)

For Redis data without stopping:

```bash
# Redis creates RDB snapshots automatically
# To force a snapshot:
docker exec $(docker ps -qf "name=redis") redis-cli BGSAVE

# Then copy the dump.rdb file
cp data/redis/dump.rdb backups/dump-$(date +%Y%m%d).rdb
```

### Restore from Backup

```bash
# Extract backup
cd /path/to/Archive-AI
tar -xzf backup-archive-ai-backup-20251230_103045.tar.gz

# Stop services
docker-compose down

# Restore data
rm -rf data/
cp -r archive-ai-backup-20251230_103045/data/ .

# Restore config
cp archive-ai-backup-20251230_103045/.env .

# Start services
docker-compose up -d
```

---

## Update and Upgrade

### Update Archive-AI Code

```bash
# Navigate to Archive-AI directory
cd /path/to/Archive-AI

# Backup first!
bash backup-archive-ai.sh

# Pull latest code
git pull origin main

# Rebuild images
docker-compose build

# Restart services
docker-compose down
docker-compose up -d

# Verify health
bash scripts/health-check.sh
```

### Update Docker Images

```bash
# Pull latest base images
docker-compose pull

# Restart with new images
docker-compose down
docker-compose up -d
```

### Update System Packages

```bash
# Update Ubuntu packages
sudo apt update
sudo apt upgrade

# Update NVIDIA driver (if needed)
sudo ubuntu-drivers autoinstall
sudo reboot
```

### Rollback

If update causes issues:

```bash
# Stop services
docker-compose down

# Restore from backup
tar -xzf backup-archive-ai-backup-<timestamp>.tar.gz
cp -r archive-ai-backup-<timestamp>/data/ .

# Checkout previous version
git checkout <previous-commit-hash>

# Rebuild
docker-compose build

# Start
docker-compose up -d
```

---

## Advanced Operations

### Running Specific Compose Profiles

```bash
# Use AWQ 7B overlay
EXTRA_COMPOSE_FILE=docker-compose.awq-7b.yml bash scripts/start.sh

# Or manually
docker-compose -f docker-compose.yml -f docker-compose.awq-7b.yml up -d
```

### Accessing Container Shells

```bash
# Brain container
docker exec -it $(docker ps -qf "name=brain") bash

# Vorpal container
docker exec -it $(docker ps -qf "name=vorpal") bash

# Redis CLI
docker exec -it $(docker ps -qf "name=redis") redis-cli
```

### Viewing Real-Time Metrics

```bash
# Container stats
docker stats

# GPU monitoring
watch -n 1 nvidia-smi

# Redis monitoring
docker exec -it $(docker ps -qf "name=redis") redis-cli --stat
```

### Custom Service Orchestration

Create custom startup sequence:

```bash
#!/bin/bash
# custom-start.sh

# Start infrastructure first
docker-compose up -d redis

# Wait for Redis
sleep 5

# Start compute engines
docker-compose up -d vorpal goblin

# Wait for models to load
sleep 30

# Start application layer
docker-compose up -d brain sandbox voice librarian

echo "Custom startup complete"
```

### Database Inspection

```bash
# Enter Redis CLI
docker exec -it $(docker ps -qf "name=redis") redis-cli

# Inside Redis CLI:
redis> DBSIZE                    # Count keys
redis> KEYS memory:*             # List memory keys
redis> GET memory:12345          # Get specific memory
redis> INFO memory               # Memory stats
redis> FT._LIST                  # List search indices
redis> quit
```

### Performance Tuning

**Reduce Vorpal VRAM for more Goblin VRAM:**
```bash
# In .env
VORPAL_GPU_MEMORY_UTILIZATION=0.30  # Reduce to 30%
GOBLIN_N_GPU_LAYERS=40              # Increase Goblin layers
```

**Use faster Whisper on GPU:**
```bash
# In .env
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16
```

**Increase Redis memory:**
```bash
# In docker-compose.yml
services:
  redis:
    environment:
      - REDIS_ARGS=--maxmemory 32gb  # If you have RAM
```

---

## Conclusion

You now have comprehensive knowledge of Archive-AI operations:

- **Installation:** From prerequisites to first run
- **Operation:** Starting, stopping, and monitoring services
- **Configuration:** Customizing for your needs
- **Models:** Managing and switching AI models
- **Troubleshooting:** Diagnosing and fixing common issues
- **Maintenance:** Backups, updates, and best practices

### Quick Reference Card

```bash
# Start everything
bash go.sh

# Start with manual control
bash scripts/start.sh

# Stop everything
docker-compose down

# Health check
bash scripts/health-check.sh

# View logs
docker-compose logs -f

# Restart service
docker-compose restart <service-name>

# Backup
bash backup-archive-ai.sh

# Update
git pull && docker-compose build && docker-compose up -d
```

### Getting Help

- **Documentation:** `/home/user/Archive-AI/documentation/`
- **API Docs:** http://localhost:8080/docs
- **Logs:** `docker-compose logs -f`
- **Health Check:** `bash scripts/health-check.sh`

### Best Practices

1. **Always backup before updates**
2. **Monitor GPU temperature** (nvidia-smi)
3. **Check logs regularly** for errors
4. **Keep disk space** above 20% free
5. **Update periodically** but test in dev first
6. **Document custom changes** to configs
7. **Use health checks** after any changes

You're now ready to operate Archive-AI like a pro!
