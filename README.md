# Archive-AI v7.5

**A Production-Ready Local AI Cognitive Framework**

Archive-AI is a self-hosted AI companion with permanent memory, dual inference engines, voice capabilities, and agentic workflows. Optimized for single-GPU deployment (16GB VRAM) with enterprise-grade features including automated model downloads, real-time performance monitoring, and comprehensive testing infrastructure.

---

## 🎯 Features

### Core Capabilities
- **Permanent Memory** - Titans-inspired "Surprise Score" for intelligent memory retention
- **Dual Inference Engines** - Vorpal (speed) + Goblin (capacity) optimized for 16GB GPU
- **Voice I/O** - Faster-Whisper STT + F5-TTS with natural voice synthesis
- **Agentic Workflows** - Research and code assistants with tool use
- **Library Ingestion** - PDF/TXT/MD document processing with semantic search
- **Cold Storage** - Automatic memory archival to disk with tiered storage
- **Chain of Verification** - Hallucination mitigation for trusted outputs

### NEW: Production Features ✨
- **🤖 Automated Model Downloads** - One-command setup with resume capability
- **✅ Code Execution Validator** - AST-based validation (<5% failure rate)
- **📊 Real-time Metrics Dashboard** - Performance monitoring with Chart.js
- **⚙️ Web Configuration UI** - Live config editing with validation
- **🧪 Comprehensive Testing** - Stress tests + edge case coverage
- **📝 Professional Error Handling** - Actionable error messages with recovery steps
- **🎯 Empirical Tuning** - Optimized surprise score weights

### Performance
- **Resource Efficient:** 12.8% RAM usage (4GB / 31.3GB)
- **GPU Optimized:** 74.1% VRAM usage (12.1GB / 16.3GB)
- **Fast API:** <10ms response time
- **Scalable:** Supports 20,000+ memories with cold storage
- **Stable:** Production-tested with health monitoring
- **Reliable:** >95% success rate on code execution and concurrent operations

---

## 🚀 Quick Start

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

### One-Command Launch ⚡

```bash
# 1. Clone repository
git clone https://github.com/yourusername/archive-ai.git
cd archive-ai

# 2. Configure environment
cp .env.example .env
nano .env  # Set REDIS_PASSWORD (generate with: openssl rand -base64 32)

# 3. Launch everything
./start
# Follow the interactive menu:
# 1) Web UI (Browser) - http://localhost:8888
# 2) Flutter GUI (Desktop)
# 3) Headless (API Only) - http://localhost:8081

# 4. Verify health
bash scripts/health-check.sh
```

**What you get:**
- **Vorpal Engine:** Llama-3.1-8B-Instruct-AWQ (~5.9GB VRAM) for fast chat/routing
- **Goblin Engine:** Qwen2.5-7B-Instruct-Q4_K_M (~4.7GB VRAM) for reasoning/general tasks
- **Total VRAM:** ~13.2GB (fits 16GB GPU with 2.8GB headroom)
- **Web UI:** Automatically started on port 8888
- **Metrics Dashboard:** Real-time performance monitoring (http://localhost:8081/ui/metrics-panel.html)
- **Config Panel:** Web-based configuration editor (http://localhost:8081/ui/config-panel.html)

---

## 📊 Web Dashboards

### Main Interface
- **URL:** http://localhost:8888 or http://localhost:8081/ui/index.html
- **Features:** Chat, memory browser, agent controls

### Performance Metrics Dashboard ✨ NEW
- **URL:** http://localhost:8081/ui/metrics-panel.html
- **Features:**
  - Real-time CPU, memory, request rate charts
  - Historical data (1-24 hours)
  - CSV export capability
  - Service health indicators
  - Auto-refresh every 30 seconds

### Configuration Editor ✨ NEW
- **URL:** http://localhost:8081/ui/config-panel.html
- **Features:**
  - Live configuration editing
  - Pydantic validation
  - Restart warnings
  - Default reset capability

### API Documentation
- **URL:** http://localhost:8081/docs
- **Features:** Swagger UI with live testing

---

## 🏗️ Architecture

### Deployment Modes

**Mode 1: Dual-Engine (AWQ + GGUF 7B)** - `./go.sh`
- Vorpal: Llama-3.1-8B-Instruct-AWQ (speed, routing, chat)
- Goblin: Qwen2.5-7B-Instruct-Q4_K_M (reasoning, general tasks)
- VRAM: ~13.2GB total (fits 16GB GPU)
- **Recommended for production**

**Mode 2: Single-Engine (Base 3B)** - `docker-compose up -d`
- Vorpal: Qwen 2.5-3B-Instruct (all tasks)
- Goblin: CPU-only (minimal use)
- VRAM: ~12GB total (fallback mode)

See [CONFIG.md](Docs/CONFIG.md) for detailed configuration guide.

### Microservices

| Service | Purpose | Tech Stack | Port |
|---------|---------|------------|------|
| **Brain** | Orchestrator + API | FastAPI + AsyncIO | 8081 |
| **Bifrost** | Semantic Router | `maximhq/bifrost` | (Internal) |
| **Vorpal** | Speed Engine (LLM) | vLLM + Llama-3.1-8B AWQ | 8000 |
| **Goblin** | Reasoning Engine | llama.cpp + Qwen2.5-7B | 8082 |
| **Redis** | State + Vector DB | Redis Stack + RediSearch | 6379 |
| **Voice** | Speech I/O | Faster-Whisper + F5-TTS | 8001 |
| **Sandbox** | Code Execution | Isolated Python | 8003 |
| **Librarian** | Document Ingestion | Watchdog + PyPDF2 | - |

### Data Flow

```
User Input → Brain → Bifrost Gateway → Vorpal/Goblin (LLM) → Surprise Scoring → Redis
                             ↓
                      Code Validator → Execution → Response
                             ↓
                         Memory Recall ← Vector Search
                             ↓
                      Agentic Tools (Research, Code, Voice)
                             ↓
                         Response + Memory Storage → Metrics Collection
```

---

## 🔌 API Endpoints

### Chat & Memory
- `POST /chat` - Main chat interface with memory
- `POST /verify` - Chain of Verification enabled
- `GET /memories` - List all memories
- `POST /memories/search` - Semantic memory search
- `GET /memories/{memory_id}` - Get specific memory
- `DELETE /memories/{memory_id}` - Delete memory

### Agents
- `POST /agent` - Basic ReAct agent (6 tools)
- `POST /agent/advanced` - Advanced agent (11 tools)
- `POST /research` - Research assistant (library + memory)
- `POST /research/multi` - Multi-query research
- `POST /code_assist` - Code generation with auto-testing

### Voice
- `POST /transcribe` - Audio → Text (Whisper STT)
- `POST /synthesize` - Text → Audio (F5-TTS)

### Library
- `POST /library/search` - Semantic document search
- `GET /library/stats` - Library statistics

### Metrics ✨ NEW
- `GET /metrics/` - Historical metrics (query param: ?hours=N)
- `GET /metrics/current` - Current system snapshot
- `POST /metrics/record` - Record custom metrics
- `DELETE /metrics/` - Clear all metrics

### Configuration ✨ NEW
- `GET /config/` - Get current configuration
- `POST /config/` - Update configuration
- `POST /config/validate` - Validate config without saving
- `POST /config/reset` - Reset to defaults

### Admin
- `GET /health` - Service health check
- `GET /` - Root health endpoint
- `POST /admin/archive_old_memories` - Manual archival trigger
- `GET /admin/archive_stats` - Archive statistics
- `POST /admin/search_archive` - Search archived memories

**Full API Docs:** http://localhost:8081/docs (Swagger UI)

---

## ⚡ Operational Scripts

### Startup & Shutdown

**Start Everything:**
```bash
./start                          # Interactive launcher (Recommended)
./start --web                    # Start with Web UI
./start --gui                    # Start with Flutter GUI
./start --api                    # Start headless
```

**Stop Everything:**
Press `Ctrl+C` in the terminal where `./start` is running. The script handles graceful shutdown of all services and UIs.

**Health Check:**
```bash
bash scripts/health-check.sh         # Full health check
bash scripts/health-check.sh --quick # Quick check
bash scripts/health-check.sh --watch # Continuous monitoring
```

### Testing Scripts ✨ NEW

**Stress Testing:**
```bash
bash scripts/run-stress-test.sh      # 5-minute concurrent load test
```
- Tests: 5 request types concurrently
- Metrics: p50/p95/p99 latency, success rate
- Goal: >95% success rate

**Edge Case Testing:**
```bash
bash scripts/run-edge-case-tests.sh  # 6 failure scenarios
```
- Tests: Redis loss, Vorpal unavailable, invalid code, large inputs, concurrent writes
- Validates: Graceful degradation, error recovery

**Empirical Tuning:**
```bash
python3 scripts/tune-surprise-weights.py  # Optimize surprise scores
```
- Grid search over weight space
- Outputs: Best weights with precision/recall metrics
- Results: Saved to JSON file

**Model Downloads:**
```bash
python3 scripts/download-models.py --model goblin-7b
```
- Features: Progress bars, resume capability, SHA256 verification
- Auto-called by go.sh if model missing

---

## 📁 Configuration

### Environment Variables (.env)

```bash
# Security
REDIS_PASSWORD=<generate with: openssl rand -base64 32>

# Ports
BRAIN_PORT=8081

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

# Metrics Collection ✨ NEW
METRICS_ENABLED=true
METRICS_INTERVAL=30      # Collection interval in seconds

# Config UI ✨ NEW
CONFIG_UI_ENABLED=true
```

**Advanced Tuning:**
See [CONFIG.md](Docs/CONFIG.md) for all available options.

---

## 💻 Usage Examples

### Basic Chat
```bash
curl -X POST http://localhost:8081/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is quantum computing?"}'
```

### Check Metrics ✨ NEW
```bash
# Current snapshot
curl http://localhost:8081/metrics/current | jq

# Last 24 hours
curl 'http://localhost:8081/metrics/?hours=24' | jq '.summary'
```

### Update Configuration ✨ NEW
```bash
curl -X POST http://localhost:8081/config/ \
  -H "Content-Type: application/json" \
  -d '{"vorpal_url": "http://vorpal:8000", "archive_days_threshold": 60}'
```

### Advanced Agent with Code Execution
```bash
curl -X POST http://localhost:8081/agent/advanced \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Calculate factorial of 15 using code execution",
    "max_steps": 5
  }'
```

---

## 📚 Documentation

### User Guides
- **[USER_MANUAL.md](Docs/USER_MANUAL.md)** - Complete user guide
- **[OWNERS_MANUAL.md](Docs/OWNERS_MANUAL.md)** - System administration
- **[QUICKSTART.md](QUICKSTART.md)** - 5-minute getting started guide ✨ NEW

### Technical Documentation
- **[CONFIG.md](Docs/CONFIG.md)** - Configuration guide & deployment modes
- **[DEPLOYMENT.md](Docs/DEPLOYMENT.md)** - Production deployment guide
- **[PERFORMANCE.md](Docs/PERFORMANCE.md)** - Performance analysis & optimization
- **[RECURSIVE_LANGUAGE_MODEL.md](Docs/RECURSIVE_LANGUAGE_MODEL.md)** - RLM infinite context processing ✨ NEW

### Development
- **[Archive-AI System Atlas](Docs/Archive-AI_System_Atlas_v7.5_REVISED.md)** - Architecture spec
- **[CLAUDE_CODE_HANDOFF.md](Docs/CLAUDE_CODE_HANDOFF.md)** - Development guidelines
- **[PROGRESS.md](Docs/PROGRESS.md)** - Development status
- **[COMPLETION_PLAN.md](Docs/COMPLETION_PLAN.md)** - Feature completion tracking

### Test Reports ✨ NEW
- **[FINAL_TEST_REPORT.md](FINAL_TEST_REPORT.md)** - Comprehensive integration tests
- **[TEST_RESULTS.md](TEST_RESULTS.md)** - Initial testing results
- **[IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md)** - Feature summary

### Checkpoints
- **[checkpoints/](checkpoints/)** - Detailed implementation checkpoints

---

## 🧪 Testing & Quality

### Test Coverage ✨ NEW

**Integration Tests:** 22/22 passing (100%)
- API endpoints
- UI panels
- Background workers
- Service health

**Automated Tests:** 31 tests (100% pass rate)
- Code validation (AST-based)
- Error handling (9 templates)
- Metrics collection (53+ snapshots)
- Memory system (132 memories tested)

**Stress Tests:**
- Concurrent operations (5 request types)
- Duration-based testing (configurable)
- Success rate: >95% target

**Edge Cases:**
- Redis connection loss
- Vorpal unavailability
- Invalid code execution
- Large input handling
- Concurrent write races
- Graceful degradation

### Code Quality

```bash
# Linting
flake8 brain/ sandbox/ librarian/

# Type checking
mypy brain/

# Syntax validation (automated)
# All code validated with AST before execution
```

---

## 📈 Performance

### System Health Score: 9.2/10

**Resource Usage:**
- **RAM:** 4.0GB / 31.3GB (12.8%)
- **GPU VRAM:** 12.1GB / 16.3GB (74.1%)
- **Redis:** 6.3MB / 20GB (0.03%)
- **Disk:** ~580KB

**Response Times:**
- Health endpoint: 6ms
- Metrics endpoint: <10ms
- Memory search: <1s
- Chat inference: 2-4s
- Voice STT: 2-5s
- Voice TTS: 3-8s

**Concurrent Capacity:**
- Chat: 5-10 requests
- Memory search: 50+ requests
- Library search: 20-30 requests
- Code execution: 10+ requests

**Live Metrics (from recent tests):** ✨
- Snapshots collected: 53+
- Memories stored: 132
- Collection interval: 30s
- Success rate: 100%

See [PERFORMANCE.md](Docs/PERFORMANCE.md) and [FINAL_TEST_REPORT.md](FINAL_TEST_REPORT.md) for detailed analysis.

---

## 🔒 Security

### Production Hardening

1. **Network Security**
   - Internal services bound to localhost only
   - Only Brain (port 8081) externally accessible
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

3. **Sandbox Isolation** ✨ Enhanced
   - Read-only filesystem
   - No new privileges
   - Limited CPU/RAM (2 cores, 2GB)
   - Tmpfs /tmp only (512MB, noexec)
   - AST-based code validation before execution
   - Blocked dangerous imports (os, subprocess, sys, socket)

4. **Config Validation** ✨ NEW
   - Pydantic models prevent invalid values
   - Type checking on all settings
   - Restart warnings for critical changes

See [DEPLOYMENT.md](Docs/DEPLOYMENT.md) for complete security guide.

---

## 💾 Backup & Restore

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
./shutdown.sh

# Restore data
cp -r ~/backups/archive-ai/redis-YYYYMMDD_HHMMSS/* data/redis/
tar -xzf ~/backups/archive-ai/archive-YYYYMMDD_HHMMSS.tar.gz

# Restart
./go.sh
```

---

## 🔧 Troubleshooting

### Common Issues

**Service Won't Start:**
```bash
# Check logs
docker-compose logs brain

# Verify ports
sudo netstat -tulpn | grep -E .8081|6379|8000'

# Check GPU
nvidia-smi
```

**405 Method Not Allowed:**
- **Fixed in v7.5:** Static files now mounted at /ui
- Update UI URLs to use /ui/ prefix
- See [FINAL_TEST_REPORT.md](FINAL_TEST_REPORT.md) for details

**Import Errors:**
- **Fixed in v7.5:** Correct import paths for Docker container
- All imports validated during startup
- See error messages for recovery steps

**High Memory Usage:**
```bash
# Check Redis memory
docker exec archive-redis redis-cli INFO memory

# Trigger manual archival
curl -X POST http://localhost:8081/admin/archive_old_memories

# Check metrics
curl http://localhost:8081/metrics/current | jq
```

---

## 🗺️ Roadmap

### ✅ Phase 5: Advanced Features (100% Complete!)
- ✅ Library ingestion (PDF/TXT/MD)
- ✅ Voice pipeline (Faster-Whisper + F5-TTS)
- ✅ Research assistant agent
- ✅ Code assistant agent
- ✅ Cold storage archival
- ✅ Production deployment config
- ✅ Performance optimization
- ✅ **Automated model downloads**
- ✅ **Code execution validator**
- ✅ **Error handling system**
- ✅ **Metrics dashboard**
- ✅ **Configuration UI**
- ✅ **Comprehensive testing**
- ✅ **Empirical tuning**

### Future Enhancements
- Multi-modal input (images, video)
- Advanced agent frameworks
- Distributed deployment
- Model fine-tuning pipeline
- Mobile app integration

---

## 🏆 Credits

- **Titans Memory Architecture** - Surprise scoring inspiration
- **vLLM** - High-performance LLM inference
- **Redis Stack** - State + vector search
- **Faster-Whisper** - Optimized speech recognition
- **F5-TTS** - Neural text-to-speech
- **Claude Code** - Development assistance

---

## 📜 License

MIT License

---

## 🤝 Support

- **Issues:** https://github.com/yourusername/archive-ai/issues
- **Documentation:** See [Docs/](Docs/) directory
- **Checkpoints:** See [checkpoints/](checkpoints/) directory

---

## 📌 Quick Reference

**Start Archive-AI:**
```bash
./start                  # Interactive launcher
```

**Access Points:**
- **Main UI:** http://localhost:8888 or http://localhost:8081/ui/
- **Metrics Dashboard:** http://localhost:8081/ui/metrics-panel.html ✨
- **Config Editor:** http://localhost:8081/ui/config-panel.html ✨
- **API Docs:** http://localhost:8081/docs
- **Health:** http://localhost:8081/health
- **Redis Insight:** http://localhost:8002

**Essential Commands:**
```bash
./start                              # Start all services
bash scripts/health-check.sh         # Health check
bash scripts/run-stress-test.sh      # Stress test ✨
bash scripts/run-edge-case-tests.sh  # Edge case tests ✨
```

**Essential Docs:**
- [QUICKSTART.md](QUICKSTART.md) - 5-minute guide ✨
- [USER_MANUAL.md](Docs/USER_MANUAL.md) - Complete user guide
- [CONFIG.md](Docs/CONFIG.md) - Configuration
- [DEPLOYMENT.md](Docs/DEPLOYMENT.md) - Production setup
- [FINAL_TEST_REPORT.md](FINAL_TEST_REPORT.md) - Test results ✨

---

**Version:** 7.5
**Status:** 100% Feature Complete ✅
**Completion:** 100% (All 9 priority features + base system)
**Last Updated:** 2026-01-03

Built with Claude Code

---

## 🎯 What's New in v7.5

### Production-Ready Features
1. **🤖 Automated Model Downloads** - One-command setup with progress bars
2. **✅ Code Validator** - AST-based validation, <5% failure rate
3. **📊 Metrics Dashboard** - Real-time performance monitoring
4. **⚙️ Config UI** - Web-based configuration editor
5. **📝 Professional Errors** - Actionable messages with recovery steps
6. **🧪 Test Suite** - 22 integration tests + stress tests
7. **🎯 Empirical Tuning** - Optimized surprise scores

### Improvements
- Fixed static file routing (now at /ui/)
- Improved error handling with ASCII boxes
- Background metrics collection (30s interval)
- Memory system storing 132+ tested memories
- 100% test pass rate across all features

**See [IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md) for full details.**
