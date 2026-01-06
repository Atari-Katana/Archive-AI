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
./start
```

This master command will:
- Check for system dependencies and models.
- Download Goblin model if missing (DeepSeek-R1-Distill-Qwen-7B, ~8.4GB).
- Start all backend services (Redis, Vorpal, Goblin, Brain, Voice, Librarian, Bifrost).
- Provide an interactive menu to launch the Web UI or Flutter GUI.

**First run takes 5-10 minutes** to download models. Subsequent starts are near-instant.

### Step 4: Verify Health

The `./start` script checks health automatically, but you can also run:

```bash
# In a new terminal
bash scripts/health-check.sh
```

---

## Access Your System

Once started, you can access:

| Interface | URL | Description |
|-----------|-----|-------------|
| **Main UI** | http://localhost:8888 | Modern chat interface (if started with --web) |
| **Metrics Dashboard** | http://localhost:8081/ui/metrics-panel.html | Real-time performance monitoring |
| **Config Editor** | http://localhost:8081/ui/config-panel.html | Live configuration editor |
| **API Docs** | http://localhost:8081/docs | Interactive Swagger documentation |
| **Redis Insight** | http://localhost:8002 | Database browser (optional) |

---

## First Steps

### 1. Send Your First Message

**Via Web UI:**
- Open http://localhost:8888
- Type a message and press Send.

**Via API:**
```bash
curl -X POST http://localhost:8081/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello! What can you help me with?"}'
```

### 2. Check Your Memories

Archive-AI automatically stores surprising/novel information using a "Surprise Score" algorithm.

**View stored memories:**
```bash
curl http://localhost:8081/memories | jq
```

### 3. Try an Agent

**Research assistant with library search:**
```bash
curl -X POST http://localhost:8081/research \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is quantum computing?",
    "use_library": true,
    "use_memory": true
  }'
```

**Code assistant with execution:**
```bash
curl -X POST http://localhost:8081/code_assist \
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
curl -X POST http://localhost:8081/library/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "your search query",
    "top_k": 5
  }'
```

### 5. Monitor Performance

Open http://localhost:8081/ui/metrics-panel.html to see:
- Real-time CPU, memory, GPU usage
- Request rates and latency
- Service health status

---

## Common Commands

**Start Archive-AI:**
```bash
./start
```

**Stop Archive-AI:**
Press `Ctrl+C` in the terminal where `./start` is running.

**Check health:**
```bash
bash scripts/health-check.sh         # Full check
```

**View logs:**
```bash
docker-compose logs -f              # All services
docker-compose logs -f brain        # Brain only
```

---

## System Requirements Summary

### What You Get (Default AWQ 7B Mode)

**Models loaded:**
- Vorpal: Qwen 2.5-7B-Instruct-AWQ (~6GB VRAM)
- Goblin: DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf (~5-6GB VRAM)
- Gateway: Bifrost Intelligent Router

**VRAM usage:** ~14GB / 16GB
**RAM usage:** ~4-6GB

---

## Troubleshooting

### Models Won't Download

```bash
# Manual download
python3 scripts/download-models.py --model goblin-7b
```

### Out of VRAM

If you have less than 16GB VRAM, use single-engine mode by editing `docker-compose.yml` or using a smaller Vorpal model.

### Service Won't Start

```bash
# Check logs
docker-compose logs brain

# Check ports
sudo netstat -tulpn | grep -E '8081|6379|8000|8080'
```

---

## Next Steps

Now that you're up and running:

1. **Explore the Web UI** - Try different agents and memory features
2. **Read the API Docs** - http://localhost:8081/docs for all endpoints
3. **Configure Your System** - See [CONFIG.md](Docs/CONFIG.md) for advanced options

---

## Quick Reference Card

```bash
# Start
./start

# Stop
Ctrl+C

# Health check
bash scripts/health-check.sh

# Access points
http://localhost:8888                      # Main UI
http://localhost:8081/ui/metrics-panel.html # Metrics
http://localhost:8081/docs                  # API docs
```

---

**You're ready to go! Archive-AI is now running with permanent memory, dual inference engines, and agentic capabilities.**

For questions or issues, run `bash scripts/health-check.sh` to get diagnostic information.
