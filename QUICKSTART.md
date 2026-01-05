# Archive-AI Quick Start Guide

**Get Archive-AI running in 5 minutes!**

This guide will get you from zero to a running AI system with permanent memory, dual inference engines, and agentic capabilities.

---

## Prerequisites Check

Before starting, ensure you have:

- **NVIDIA GPU** with 16GB VRAM (RTX 4060 Ti 16GB, 3090, 4090, or similar)
- **32GB RAM** minimum (64GB recommended)
- **50GB+ free disk space**
- **Ubuntu 22.04+** or similar Linux distribution
- **Docker 24.0+** and **Docker Compose 2.20+** installed
- **NVIDIA Driver 535+** installed
- **NVIDIA Container Toolkit** installed

### Quick Prerequisite Check

```bash
# Check GPU
nvidia-smi

# Check Docker
docker --version
docker-compose --version

# Check NVIDIA Container Toolkit
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

If any of these fail, see [DEPLOYMENT.md](Docs/DEPLOYMENT.md) for installation instructions.

---

## 5-Minute Setup

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/archive-ai.git
cd archive-ai
```

### Step 2: Configure Environment

```bash
# Copy example config
cp .env.example .env

# Generate secure password
openssl rand -base64 32

# Edit .env and set REDIS_PASSWORD to the generated value
nano .env
```

**Minimum required change:**
- Set `REDIS_PASSWORD` to a secure value (use the output from `openssl rand -base64 32`)

### Step 3: Launch Everything

```bash
./go.sh
```

This single command will:
- Download Goblin model if missing (DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf, ~8.4GB, resumable)
- Start all 6 microservices (Redis, Vorpal, Goblin, Brain, Voice, Librarian)
- Launch Web UI on http://localhost:8888
- Load Qwen 2.5-7B-AWQ (~6GB VRAM) + DeepSeek-R1-Distill-Qwen-7B-Q4_K_M (~5-6GB VRAM)

**First run takes 5-10 minutes** to download models. Subsequent starts take ~30 seconds.

### Step 4: Verify Health

Wait for models to load (watch terminal output), then:

```bash
# In a new terminal
bash scripts/health-check.sh
```

You should see all services reporting healthy.

---

## Access Your System

Once started, you can access:

| Interface | URL | Description |
|-----------|-----|-------------|
| **Main UI** | http://localhost:8888 | Chat interface and memory browser |
| **Metrics Dashboard** | http://localhost:8080/ui/metrics-panel.html | Real-time performance monitoring |
| **Config Editor** | http://localhost:8080/ui/config-panel.html | Live configuration editor |
| **API Docs** | http://localhost:8080/docs | Interactive Swagger documentation |
| **Redis Insight** | http://localhost:8002 | Database browser (optional) |

---

## First Steps

### 1. Send Your First Message

**Via Web UI:**
- Open http://localhost:8888
- Type a message in the chat box
- Press Send

**Via API:**
```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello! What can you help me with?"}'
```

### 2. Check Your Memories

Archive-AI automatically stores surprising/novel information using a "Surprise Score" algorithm.

**View stored memories:**
```bash
curl http://localhost:8080/memories | jq
```

### 3. Try an Agent

**Research assistant with library search:**
```bash
curl -X POST http://localhost:8080/research \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is quantum computing?",
    "use_library": true,
    "use_memory": true
  }'
```

**Code assistant with execution:**
```bash
curl -X POST http://localhost:8080/code_assist \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Write a function to calculate fibonacci numbers",
    "max_attempts": 3
  }'
```

### 4. Add Documents to Your Library

Archive-AI can ingest PDF, TXT, and MD files for semantic search:

```bash
# Create library drop folder
mkdir -p ~/ArchiveAI/Library-Drop

# Copy documents
cp your-document.pdf ~/ArchiveAI/Library-Drop/

# Wait a few seconds for processing, then search
curl -X POST http://localhost:8080/library/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "your search query",
    "top_k": 5
  }'
```

### 5. Monitor Performance

Open http://localhost:8080/ui/metrics-panel.html to see:
- Real-time CPU, memory, GPU usage
- Request rates and latency
- Service health status
- Historical data with charts

---

## Common Commands

**Start Archive-AI:**
```bash
./go.sh
```

**Stop Archive-AI:**
```bash
./shutdown.sh
```

**Check health:**
```bash
bash scripts/health-check.sh         # Full check
bash scripts/health-check.sh --quick # Quick check
bash scripts/health-check.sh --watch # Continuous monitoring
```

**View logs:**
```bash
docker-compose logs -f              # All services
docker-compose logs -f brain        # Brain only
docker-compose logs -f vorpal       # Vorpal LLM only
```

**Restart a service:**
```bash
docker-compose restart brain
```

---

## System Requirements Summary

### What You Get (Default AWQ 7B Mode)

**Models loaded:**
- Vorpal: Qwen 2.5-7B-Instruct-AWQ (~6GB VRAM)
- Goblin: DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf (~5-6GB VRAM)
- Embeddings: all-MiniLM-L6-v2 (~90MB)

**VRAM usage:** ~14GB / 16GB (87% utilization)
**RAM usage:** ~4-6GB
**Disk usage:** ~12GB (models + data)

### Performance Expectations

- **Chat response:** 2-4 seconds
- **Code execution:** 1-3 seconds
- **Memory search:** <1 second
- **Voice STT:** 2-5 seconds
- **Voice TTS:** 3-8 seconds

---

## Troubleshooting

### Models Won't Download

```bash
# Manual download
python3 scripts/download-models.py --model goblin-7b

# Check disk space
df -h .
```

### Out of VRAM

If you have less than 16GB VRAM, use single-engine mode:

```bash
# Stop everything
./shutdown.sh

# Start in 3B mode (uses ~12GB VRAM)
docker-compose up -d
```

### Service Won't Start

```bash
# Check logs
docker-compose logs brain

# Check ports
sudo netstat -tulpn | grep -E '8080|6379|8000'

# Restart service
docker-compose restart brain
```

### Can't Access Web UI

```bash
# Check if UI server is running
lsof -i:8888

# Manually start UI
cd ui && python3 -m http.server 8888
```

### Import Errors or Code Issues

```bash
# Rebuild containers
docker-compose build brain
docker-compose up -d
```

---

## Next Steps

Now that you're up and running:

1. **Explore the Web UI** - Try different agents and memory features
2. **Read the API Docs** - http://localhost:8080/docs for all endpoints
3. **Configure Your System** - See [CONFIG.md](Docs/CONFIG.md) for advanced options
4. **Add Voice** - Enable voice I/O in the UI
5. **Run Tests** - `bash scripts/run-stress-test.sh` to verify performance
6. **Read User Manual** - [USER_MANUAL.md](Docs/USER_MANUAL.md) for comprehensive guide

---

## Production Deployment

For production use, see:
- [DEPLOYMENT.md](Docs/DEPLOYMENT.md) - Production deployment guide
- [CONFIG.md](Docs/CONFIG.md) - Configuration options
- [PERFORMANCE.md](Docs/PERFORMANCE.md) - Performance tuning

---

## Getting Help

- **Documentation:** See [Docs/](Docs/) directory
- **Issues:** https://github.com/yourusername/archive-ai/issues
- **Health Check:** `bash scripts/health-check.sh` for diagnostic info

---

## Quick Reference Card

```bash
# Start
./go.sh

# Stop
./shutdown.sh

# Health check
bash scripts/health-check.sh

# View logs
docker-compose logs -f

# Restart service
docker-compose restart <service>

# Access points
http://localhost:8888                      # Main UI
http://localhost:8080/ui/metrics-panel.html # Metrics
http://localhost:8080/docs                  # API docs
```

---

**You're ready to go! Archive-AI is now running with permanent memory, dual inference engines, and agentic capabilities.**

For questions or issues, run `bash scripts/health-check.sh` to get diagnostic information.
