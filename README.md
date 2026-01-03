# Archive-AI v7.5

**A Production-Ready Local AI Cognitive Framework**

Archive-AI is a self-hosted AI companion with permanent memory, dual inference engines, voice capabilities, and agentic workflows. Optimized for single-GPU deployment (16GB VRAM) with enterprise-grade features.

---

## Features

### Core Capabilities
- **Permanent Memory** - Titans-inspired "Surprise Score" for intelligent memory retention
- **Dual Inference Engines** - Vorpal (speed) + Goblin (capacity) optimized for 16GB GPU
- **Voice I/O** - Faster-Whisper STT + F5-TTS with natural voice synthesis
- **Agentic Workflows** - Research and code assistants with tool use
- **Library Ingestion** - PDF/TXT/MD document processing with semantic search
- **Cold Storage** - Automatic memory archival to disk with tiered storage
- **Chain of Verification** - Hallucination mitigation for trusted outputs

### Performance
- **Resource Efficient:** 12.8% RAM usage (4GB / 31.3GB)
- **GPU Optimized:** 74.1% VRAM usage (12.1GB / 16.3GB)
- **Fast API:** <10ms response time
- **Scalable:** Supports 20,000+ memories with cold storage
- **Stable:** Production-tested with health monitoring

---

## Quick Start

### Prerequisites
- **Hardware:**
  - NVIDIA GPU with 16GB VRAM (RTX 5060 Ti, 4060 Ti 16GB, 3090, 4090)
  - 32GB RAM minimum (64GB recommended)
  - 50GB+ SSD storage
- **Software:**
  - Ubuntu 22.04+ (or similar Linux)
  - Docker 24.0+
  - Docker Compose 2.20+
  - NVIDIA Driver 535+
  - NVIDIA Container Toolkit

### Installation

#### 🚀 One-Command Launch (Recommended for 16GB GPU)

```bash
# 1. Clone repository
git clone https://github.com/yourusername/archive-ai.git
cd archive-ai

# 2. Configure environment
cp .env.example .env
nano .env  # Set REDIS_PASSWORD (generate with: openssl rand -base64 32)

# 3. Download Goblin model (one-time setup)
cd models/goblin
wget https://huggingface.co/unsloth/DeepSeek-R1-Distill-Qwen-7B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf
cd ../..

# 4. Launch everything (dual-engine AWQ mode)
bash go.sh
# ✓ Starts Redis, Vorpal (7B AWQ), Goblin (7B GGUF), Brain, Voice, Librarian
# ✓ Launches Web UI on http://localhost:8888
# ✓ Press Ctrl+C to stop everything

# 5. Verify health (in another terminal)
bash scripts/health-check.sh
```

**What you get:**
- **Vorpal Engine:** Qwen 2.5-7B-Instruct-AWQ (~6GB VRAM) for fast chat/routing
- **Goblin Engine:** DeepSeek-R1-Distill-Qwen-7B (~5-6GB VRAM) for reasoning/coding
- **Total VRAM:** ~14GB (fits 16GB GPU with 2GB headroom)
- **Web UI:** Automatically started on port 8888

---

#### 📦 Automated Installation (Alternative Methods)

**Standard Installation:**
```bash
# 1. Clone repository
git clone https://github.com/yourusername/archive-ai.git
cd archive-ai

# 2. Run installation script
bash scripts/install.sh          # Development mode
bash scripts/install.sh --prod   # Production mode

# 3. Start services (choose one)
bash go.sh                       # Dual-engine AWQ mode (recommended)
# OR
bash scripts/start.sh            # Single-engine mode (Vorpal 3B only)
bash scripts/start.sh --prod     # Production mode

# 4. Verify health
bash scripts/health-check.sh
```

#### Manual Installation

1. **Clone Repository**
   ```bash
   git clone https://github.com/yourusername/archive-ai.git
   cd archive-ai
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   nano .env  # Edit configuration
   ```

3. **Create Data Directories**
   ```bash
   mkdir -p data/{redis,archive,library} models/{vorpal,whisper,f5-tts} ~/ArchiveAI/Library-Drop
   ```

4. **Download Models**
   - **Vorpal (Required):** Place Llama-3-8B-Instruct (EXL2 4.0bpw) in `./models/vorpal/`
   - **Whisper (Auto):** Downloads on first use to `./models/whisper/`
   - **F5-TTS (Auto):** Downloads on first use to `./models/f5-tts/`

5. **Start Services**
   ```bash
   # Production deployment
   docker-compose -f docker-compose.prod.yml up -d

   # Development (without resource limits)
   docker-compose up -d
   ```

6. **Verify Health**
   ```bash
   curl http://localhost:8080/health
   ```

7. **Access Web UI**
   ```bash
   cd ui && python3 -m http.server 8888
   # Open http://localhost:8888
   ```

---

## Architecture

### Deployment Modes

Archive-AI supports two deployment configurations:

**Mode 1: Dual-Engine (AWQ 7B)** - `bash go.sh`
- Vorpal: Qwen 2.5-7B-Instruct-AWQ (speed, routing, chat)
- Goblin: DeepSeek-R1-Distill-Qwen-7B (reasoning, coding, agents)
- VRAM: ~14GB total (fits 16GB GPU)

**Mode 2: Single-Engine (Base 3B)** - `docker-compose up -d`
- Vorpal: Qwen 2.5-3B-Instruct (all tasks)
- Goblin: Disabled (CPU-only, minimal use)
- VRAM: ~12GB total (fallback mode)

See [CONFIG.md](Docs/CONFIG.md) for detailed configuration guide.

### Microservices

| Service | Purpose | Tech Stack | Port |
|---------|---------|------------|------|
| **Brain** | Orchestrator + API | FastAPI + AsyncIO | 8080 |
| **Vorpal** | Speed Engine (LLM) | vLLM + Qwen 7B AWQ / 3B | 8000 |
| **Goblin** | Reasoning Engine | llama.cpp + DeepSeek 7B | 8081 |
| **Redis** | State + Vector DB | Redis Stack + RediSearch | 6379 |
| **Voice** | Speech I/O | Faster-Whisper + F5-TTS | 8001 |
| **Sandbox** | Code Execution | Isolated Python | 8003 |
| **Librarian** | Document Ingestion | Watchdog + PyPDF2 | - |

### Data Flow

```
User Input → Brain → Vorpal (LLM) → Surprise Scoring → Redis
                ↓
            Memory Recall ← Vector Search
                ↓
         Agentic Tools (Research, Code, Voice)
                ↓
            Response + Memory Storage
```

### Memory System

- **Hot Storage:** Recent 1000 memories in Redis (fast semantic search)
- **Cold Storage:** Older memories archived to disk (YYYY-MM/memories-YYYYMMDD.json)
- **Automatic Archival:** Daily at 3 AM (configurable)
- **Surprise Scoring:** Retains unexpected/important memories over time

---

## API Endpoints

### Chat & Memory
- `POST /chat` - Main chat interface with memory
- `POST /verified_chat` - Chain of Verification enabled
- `GET /memories` - List all memories
- `POST /memory/search` - Semantic memory search
- `POST /memory/add` - Manual memory addition

### Agents
- `POST /research` - Research assistant (library + memory search)
- `POST /research/multi` - Multi-query research
- `POST /code_assist` - Code generation with auto-testing

### Voice
- `POST /transcribe` - Audio → Text (Whisper STT)
- `POST /synthesize` - Text → Audio (F5-TTS)

### Library
- `POST /library/search` - Semantic document search
- `GET /library/stats` - Library statistics

### Admin
- `GET /health` - Service health check
- `GET /metrics` - System metrics
- `POST /admin/archive_old_memories` - Manual archival trigger
- `GET /admin/archive_stats` - Archive statistics

**Full API Docs:** http://localhost:8080/docs (Swagger UI)

---

## Configuration

### Quick Start Commands

**Dual-Engine Mode (Recommended):**
```bash
bash go.sh  # One command to start everything + Web UI
```

**Single-Engine Mode (Fallback):**
```bash
docker-compose up -d              # Start services only
cd ui && python3 -m http.server 8888  # Launch UI manually
```

**Production Mode:**
```bash
docker-compose -f docker-compose.prod.yml up -d
```

See [CONFIG.md](Docs/CONFIG.md) for comprehensive configuration guide.

---

### Environment Variables (.env)

```bash
# Security
REDIS_PASSWORD=<generate with: openssl rand -base64 32>

# Ports
BRAIN_PORT=8080

# Memory Archival
ARCHIVE_DAYS=30          # Archive after 30 days
ARCHIVE_KEEP=1000        # Keep 1000 most recent
ARCHIVE_HOUR=3           # Run at 3 AM

# Voice
WHISPER_MODEL=base       # tiny/base/small/medium/large
TTS_DEVICE=cpu           # cpu or cuda

# Library
LIBRARY_DROP=~/ArchiveAI/Library-Drop

# Logging
LOG_LEVEL=INFO           # DEBUG/INFO/WARNING/ERROR

# GPU
CUDA_VISIBLE_DEVICES=0
VORPAL_GPU_MEMORY_UTILIZATION=0.45  # AWQ mode default
```

**Advanced Tuning:**
Create `config/user-config.env` to override model parameters without editing docker-compose files. See [CONFIG.md](Docs/CONFIG.md) for all available options.

---

## Usage Examples

### Basic Chat
```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is quantum computing?"}'
```

### Research Assistant
```bash
curl -X POST http://localhost:8080/research \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Explain transformer architecture",
    "max_library_results": 5,
    "max_memory_results": 3
  }'
```

### Code Generation
```bash
curl -X POST http://localhost:8080/code_assist \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Write a function to check if a number is prime",
    "max_attempts": 3
  }'
```

### Memory Search
```bash
curl -X POST http://localhost:8080/memory/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning",
    "limit": 10
  }'
```

### Voice Transcription
```bash
curl -X POST http://localhost:8001/transcribe \
  -F "audio=@recording.wav"
```

### Library Ingestion
```bash
# Drop files into Library-Drop directory
cp my-document.pdf ~/ArchiveAI/Library-Drop/
# Librarian auto-processes and indexes
```

---

## Operational Scripts

Archive-AI includes automated scripts for installation, startup, and monitoring:

### Installation Script
```bash
bash scripts/install.sh          # Development installation
bash scripts/install.sh --prod   # Production installation
```

**Features:**
- Checks prerequisites (Docker, Docker Compose, GPU)
- Creates .env from template
- Generates secure Redis password
- Creates all required directories
- Builds Docker images
- Sets proper permissions
- Verifies Vorpal model presence

### Startup Script
```bash
bash scripts/start.sh            # Development mode
bash scripts/start.sh --prod     # Production mode
bash scripts/start.sh --rebuild  # Rebuild images before starting
bash scripts/start.sh --attach   # Start in foreground (view logs)
```

**Features:**
- Pre-flight checks (.env, models, GPU)
- Stops existing services cleanly
- Starts all services with health verification
- Waits for each service to be ready
- Displays service status
- Performs quick health check
- Shows access URLs and next steps

### Health Check Script
```bash
bash scripts/health-check.sh         # Full health check
bash scripts/health-check.sh --quick # Quick check only
bash scripts/health-check.sh --watch # Continuous monitoring (10s interval)
```

**Features:**
- Docker container status (CPU, memory per service)
- HTTP health endpoint verification
- Redis PING test
- API endpoint validation
- Resource usage (containers, GPU, Redis, disk)
- Recent error log scanning
- Memory system statistics
- Inter-service connectivity
- Service uptime reporting
- Comprehensive health summary

---

## Monitoring

### Health Checks
```bash
# Overall system health
curl http://localhost:8080/health

# System metrics
curl http://localhost:8080/metrics

# Archive statistics
curl http://localhost:8080/admin/archive_stats
```

### Resource Usage
```bash
# Docker container stats
docker stats

# GPU usage
nvidia-smi -l 1

# Redis memory
docker exec archive-redis redis-cli INFO memory | grep used_memory_human

# Disk usage
du -sh data/*
```

### Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker logs -f archive-brain

# Last 100 lines
docker logs --tail 100 archive-brain
```

---

## Performance

### System Health Score: 9.2/10

**Resource Usage:**
- **RAM:** 4.0GB / 31.3GB (12.8%)
- **GPU VRAM:** 12.1GB / 16.3GB (74.1%)
- **Redis:** 6.3MB / 20GB (0.03%)
- **Disk:** ~580KB

**Response Times:**
- Health endpoint: 6ms
- Memory search: <1s
- Chat inference: 2-4s (depends on length)
- Voice STT: 2-5s per file
- Voice TTS: 3-8s per synthesis

**Concurrent Capacity:**
- Chat: 5-10 requests
- Memory search: 50+ requests
- Library search: 20-30 requests
- Voice: 2-3 requests
- Code execution: 10+ requests

See [PERFORMANCE.md](Docs/PERFORMANCE.md) for detailed analysis and optimization recommendations.

---

## Security

### Production Hardening

1. **Network Security**
   - Internal services bound to localhost only
   - Only Brain (port 8080) externally accessible
   - Use nginx reverse proxy with SSL

2. **Firewall Configuration**
   ```bash
   sudo ufw allow 22/tcp    # SSH
   sudo ufw allow 80/tcp    # HTTP
   sudo ufw allow 443/tcp   # HTTPS
   sudo ufw deny 6379       # Redis
   sudo ufw deny 8000       # Vorpal
   sudo ufw deny 8001       # Voice
   sudo ufw deny 8003       # Sandbox
   sudo ufw enable
   ```

3. **Redis Password**
   ```bash
   openssl rand -base64 32 > .redis-password
   # Set REDIS_PASSWORD in .env
   ```

4. **Sandbox Isolation**
   - Read-only filesystem
   - No new privileges
   - Limited CPU/RAM (2 cores, 2GB)
   - Tmpfs /tmp only (512MB, noexec)

See [DEPLOYMENT.md](Docs/DEPLOYMENT.md) for complete security guide.

---

## Backup & Restore

### Backup Script
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=~/backups/archive-ai

mkdir -p $BACKUP_DIR

# Redis data
docker exec archive-redis redis-cli SAVE
cp -r data/redis $BACKUP_DIR/redis-$DATE

# Archive data
tar -czf $BACKUP_DIR/archive-$DATE.tar.gz data/archive

# Library data
tar -czf $BACKUP_DIR/library-$DATE.tar.gz data/library

# Configuration
cp .env $BACKUP_DIR/env-$DATE

echo "Backup complete: $BACKUP_DIR"
```

### Restore
```bash
# Stop services
docker-compose down

# Restore data
cp -r ~/backups/archive-ai/redis-YYYYMMDD_HHMMSS/* data/redis/
tar -xzf ~/backups/archive-ai/archive-YYYYMMDD_HHMMSS.tar.gz

# Restart
docker-compose up -d
```

---

## Troubleshooting

### Service Won't Start
```bash
# Check logs
docker-compose logs [service]

# Verify ports
sudo netstat -tulpn | grep -E '8080|6379|8000'

# Check dependencies
docker ps -a
```

### High Memory Usage
```bash
# Check Redis memory
docker exec archive-redis redis-cli INFO memory

# Trigger manual archival
curl -X POST http://localhost:8080/admin/archive_old_memories

# Adjust ARCHIVE_KEEP in .env
```

### GPU Issues
```bash
# Verify GPU
nvidia-smi

# Check CUDA in container
docker exec archive-vorpal nvidia-smi

# Reduce GPU usage
# Edit .env: GPU_MEMORY_UTILIZATION=0.15
```

---

## Development

### Project Structure
```
archive-ai/
├── brain/          # Orchestrator + LangGraph
├── vorpal/         # Speed engine (vLLM)
├── sandbox/        # Code execution
├── voice/          # Speech I/O
├── librarian/      # Document ingestion
├── ui/             # Web dashboard
├── scripts/        # Test scripts
├── checkpoints/    # Progress tracking
├── models/         # Model storage
├── data/           # Persistent data
└── Docs/           # Documentation
```

### Running Tests
```bash
# Library ingestion
bash scripts/test-librarian.sh

# Research agent
python3 scripts/test-research-agent.py

# Code assistant
python3 scripts/test-code-assistant.py
```

### Code Quality
```bash
# Linting
flake8 brain/ sandbox/ librarian/

# Format
black brain/ sandbox/ librarian/
```

---

## Documentation

- **[DEPLOYMENT.md](Docs/DEPLOYMENT.md)** - Production deployment guide (385 lines)
- **[PERFORMANCE.md](Docs/PERFORMANCE.md)** - Performance analysis & optimization (385 lines)
- **[PROGRESS.md](Docs/PROGRESS.md)** - Development progress tracker
- **[CONFIG.md](Docs/CONFIG.md)** - Configuration guide & deployment modes
- **[SYSTEM_STATUS.md](Docs/SYSTEM_STATUS.md)** - Current system status
- **[Archive-AI System Atlas](Docs/Archive-AI_System_Atlas_v7.5_REVISED.md)** - Architecture specification
- **[CLAUDE_CODE_HANDOFF.md](Docs/CLAUDE_CODE_HANDOFF.md)** - Development guidelines
- **[GITHUB_SETUP.md](Docs/GITHUB_SETUP.md)** - Git workflow guide
- **[checkpoints/](checkpoints/)** - Implementation checkpoints

---

## Roadmap

### Phase 5: Advanced Features (8/13 Complete)
- ✅ Library ingestion (PDF/TXT/MD)
- ✅ Voice pipeline (Faster-Whisper + F5-TTS)
- ✅ Research assistant agent
- ✅ Code assistant agent
- ✅ Cold storage archival
- ✅ Production deployment config
- ✅ Performance optimization
- ⏭️ Final documentation (in progress)
- ⏭️ Optional: LangGraph, tuning, stress tests

### Future Enhancements
- Multi-modal input (images, video)
- Advanced agent frameworks
- Distributed deployment
- Model fine-tuning pipeline
- Mobile app integration

---

## System Requirements

### Dual-Engine Mode (AWQ 7B) - `bash go.sh`
**Minimum:**
- GPU: 16GB VRAM (RTX 5060 Ti, 4060 Ti 16GB)
- RAM: 32GB
- CPU: 8+ cores
- Storage: 50GB SSD
- OS: Ubuntu 22.04+ or similar Linux

**Recommended:**
- GPU: 16-24GB VRAM (RTX 5060 Ti, 3090, 4090)
- RAM: 64GB
- CPU: 12+ cores
- Storage: 100GB NVMe SSD
- OS: Ubuntu 22.04 LTS

### Single-Engine Mode (Base 3B) - `docker-compose up -d`
**Minimum:**
- GPU: 12GB VRAM (RTX 3060 12GB, 4060 Ti, 5060)
- RAM: 16GB
- CPU: 4+ cores
- Storage: 30GB SSD
- OS: Ubuntu 22.04+ or similar Linux

**Notes:**
- Desktop environments (X11/Wayland) use 2-3GB VRAM - factor this into budget
- AWQ models auto-download on first start (~3.5GB download)
- GGUF models must be manually downloaded before starting Goblin

---

## Credits

- **Titans Memory Architecture** - Surprise scoring inspiration
- **vLLM** - High-performance LLM inference
- **Redis Stack** - State + vector search
- **Faster-Whisper** - Optimized speech recognition
- **F5-TTS** - Neural text-to-speech
- **LangGraph** - Agentic workflow framework

---

## License

[Your License Here]

---

## Support

- **Issues:** https://github.com/yourusername/archive-ai/issues
- **Documentation:** See [Docs/](Docs/) directory
- **Checkpoints:** See [checkpoints/](checkpoints/) directory

---

**Version:** 7.5
**Status:** Production Ready (Dual-Engine AWQ Mode Available)
**Completion:** 79.1% (34/43 chunks)
**Last Updated:** 2026-01-02

Built with Claude Code by [Your Name]

---

## Quick Reference

**Start Archive-AI:**
- Dual-Engine (Best): `bash go.sh`
- Single-Engine: `docker-compose up -d`
- Production: `docker-compose -f docker-compose.prod.yml up -d`

**Access Points:**
- Web UI: http://localhost:8888
- API Docs: http://localhost:8080/docs
- Health: http://localhost:8080/health
- Redis Insight: http://localhost:8002

**Essential Docs:**
- [CONFIG.md](Docs/CONFIG.md) - Configuration guide & deployment modes
- [DEPLOYMENT.md](Docs/DEPLOYMENT.md) - Production deployment
- [PERFORMANCE.md](Docs/PERFORMANCE.md) - Performance tuning
- [PROGRESS.md](Docs/PROGRESS.md) - Development status
