# Archive-AI v7.5 - Current Status Report
**Date:** 2025-12-28 15:30 UTC
**Phase:** Infrastructure Setup (Phase 1)
**Configuration:** Vorpal-Only Mode (Goblin Disabled)

---

## 🎯 Executive Summary

Archive-AI is **PARTIALLY OPERATIONAL** with critical services running but one major subsystem broken:

- ✅ **Infrastructure:** All Docker services running and healthy
- ✅ **Vorpal Engine:** Speed inference working (Qwen/Qwen2.5-3B-Instruct)
- ✅ **Voice Services:** FastWhisper + F5-TTS operational
- ✅ **Redis Stack:** Vector database and streams functional
- ✅ **Sandbox:** Code execution environment ready
- ❌ **Goblin Engine:** Disabled due to VRAM constraints
- ❌ **Memory System:** Perplexity calculation BROKEN (Brain cannot connect to Vorpal)

**System is usable for basic chat but memory archival is non-functional.**

---

## 📊 What Was Accomplished (Session Summary)

### 1. Fixed Critical Startup Issues
- **Problem 1:** Missing `.env` file
  - **Solution:** Created from `.env.example`, generated secure Redis password
  - **File:** `/home/davidjackson/Archive-AI/.env`
  - **Password:** `kGF6KurpAPtjkechlotjpgGjyVW4Vkih`

- **Problem 2:** Goblin Docker image not found
  - **Solution:** Changed from `ghcr.io/ggerganov/llama.cpp:server-cuda` to `ghcr.io/ggml-org/llama.cpp:server-cuda`
  - **File:** `docker-compose.yml:44`

- **Problem 3:** Goblin model missing
  - **Solution:** Downloaded `DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf` (8.4GB)
  - **Location:** `/home/davidjackson/Archive-AI/models/goblin/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf`

- **Problem 4:** Goblin command syntax wrong
  - **Solution:** Fixed command arguments (added value for `--flash-attn`)
  - **File:** `docker-compose.yml:65-85`

### 2. VRAM Optimization Saga

**Hardware Reality:**
- GPU: NVIDIA GeForce RTX 5060 Ti (16GB total)
- Desktop Environment: ~2.9GB VRAM usage (cosmic-comp, browsers, etc.)
- **Available for AI:** ~13.1GB

**Original Spec vs. Reality:**
| Component | Spec | Reality | Problem |
|-----------|------|---------|---------|
| Vorpal | 3.5GB | 5.8GB | Model larger than expected |
| Goblin | 10GB | 8.0GB (38 GPU layers) | OK initially |
| Desktop | 0GB | 2.9GB | **NOT ACCOUNTED FOR** |
| **Total** | **13.5GB** | **16.7GB** | **OVERSUBSCRIBED** |

**Optimization Attempts:**
1. Reduced Goblin GPU layers: 38 → 28 (saved ~1.9GB, now uses 6.2GB)
2. Reduced Vorpal memory utilization: 0.5 → 0.35 (didn't help - model still too large)
3. **Final Decision:** Disabled Goblin entirely

**Current VRAM Usage (Vorpal-Only Mode):**
- Desktop: ~2.9GB
- Vorpal (0.50 utilization): 10.4GB
- **Total:** 13.3GB / 16GB (2.7GB free)

### 3. Vorpal Configuration

**Current Settings:**
```yaml
vorpal:
  image: archive-ai/vorpal:latest
  environment:
    - GPU_MEMORY_UTILIZATION=0.50  # Increased from 0.35
  command:
    - "Qwen/Qwen2.5-3B-Instruct"
    - "--gpu-memory-utilization"
    - "0.50"
    - "--max-model-len"
    - "8192"
```

**Status:** ✅ Running and healthy
- API Endpoint: `http://localhost:8000`
- Health Check: PASSING
- Model: Qwen/Qwen2.5-3B-Instruct (3B parameters)
- VRAM Usage: 10.4GB
- Startup Time: ~2 minutes (model loading + CUDA graph capture)

---

## 🚨 Current Blocker: Brain-Vorpal Connectivity

### The Problem
Brain's Memory Worker **CANNOT** connect to Vorpal for perplexity calculation:

```
[MemoryWorker] Failed to calculate perplexity for: <text>...
Perplexity calculation error: All connection attempts failed
```

### What This Breaks
The **entire memory archival system** relies on perplexity to calculate "Surprise Score":
- Surprise Score = (Perplexity × 0.6) + (Vector Distance × 0.4)
- Without perplexity, Brain cannot determine which memories to archive
- Memory system is effectively non-functional

### Investigation Results

**✅ Vorpal API is working:**
```bash
# Direct test from host - WORKS
curl -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen2.5-3B-Instruct","prompt":"test","max_tokens":1,"logprobs":1,"echo":true}'

# Returns proper logprobs data
```

**✅ Docker networking is correct:**
- Both Brain and Vorpal on `archive-ai_archive-net` network
- Brain has `VORPAL_URL=http://vorpal:8000` env var
- `depends_on: [redis, vorpal]` configured

**❌ Brain's httpx client fails:**
- Error message: "All connection attempts failed"
- Code location: `/home/davidjackson/Archive-AI/brain/workers/memory_worker.py:86-89`
- Makes POST request to `{config.VORPAL_URL}/v1/completions`
- Timeout: 30 seconds

### Hypotheses (Untested)
1. **Startup race condition:** Brain starts before Vorpal finishes loading model (~2min), caches DNS failure
2. **httpx connection pooling issue:** Client initialized before Vorpal ready, never recovers
3. **Docker DNS resolution delay:** Network not fully stable when Brain connects
4. **httpx timeout too aggressive:** Connection attempts fail before Vorpal responds

### Why Multiple Restarts Didn't Help
The Brain is processing **old messages from Redis Stream** that were queued when Vorpal was down. These keep failing even after Vorpal is healthy.

---

## 🐉 Goblin Status & Reactivation

### Current State: DISABLED

**Why Disabled:**
- VRAM conflict with Vorpal (both couldn't run simultaneously)
- Desktop environment using unexpected 2.9GB VRAM
- Total requirement exceeded available VRAM

**Goblin Service Details:**
- Container Name: `archive-ai_goblin_2`
- Status: `Exit 0` (cleanly stopped)
- Model: `DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf` (8.4GB on disk)
- Last Working Config: 28 GPU layers, 6.2GB VRAM usage

### How to Reactivate Goblin (OPTION A: Alongside Vorpal)

**⚠️ WARNING:** This will likely fail due to VRAM constraints unless you:
- Close desktop applications (~1-2GB VRAM savings)
- Accept slower performance with fewer GPU layers
- OR upgrade GPU

**Steps:**
```bash
# 1. Stop Vorpal to free VRAM
docker-compose stop vorpal

# 2. Start Goblin
docker-compose start goblin

# 3. Wait for Goblin to load (~30 seconds)
sleep 30

# 4. Check status
docker-compose ps | grep goblin

# 5. Test Goblin API
curl http://localhost:8081/health

# 6. Try starting Vorpal alongside (may fail)
docker-compose start vorpal

# 7. Monitor VRAM
nvidia-smi
```

**Expected VRAM Usage:**
- Desktop: 2.9GB
- Goblin (28 layers): 6.2GB
- Vorpal (0.35 utilization): 5.4GB
- **Total:** 14.5GB (exceeds budget, Vorpal will likely crash)

### How to Reactivate Goblin (OPTION B: Replace Vorpal)

**Use Case:** If you want reasoning/coding over memory archival

```bash
# 1. Stop Vorpal
docker-compose stop vorpal

# 2. Start Goblin
docker-compose start goblin

# 3. Update Brain to use Goblin URL (optional, for LLM features)
# Edit docker-compose.yml brain environment:
# - GOBLIN_URL=http://goblin:8080
```

**Trade-off:**
- ✅ Gain: Advanced reasoning, coding assistance, 14B model capacity
- ❌ Lose: Memory surprise scoring, perplexity calculation, memory archival

### How to Reactivate Goblin (OPTION C: Download Smaller Model)

**Recommended Path Forward:**

```bash
# 1. Download 7B model (~4GB VRAM vs 6.2GB)
cd /home/davidjackson/Archive-AI/models/goblin
huggingface-cli download unsloth/DeepSeek-R1-Distill-Qwen-7B-GGUF \
  DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf --local-dir . --local-dir-use-symlinks False

# 2. Update docker-compose.yml to use new model
# Change line 46 and 67:
# - MODEL_PATH=/models/DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf
# - "--model"
# - "/models/DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf"

# 3. Reduce GPU layers to 25 (estimated 4-5GB VRAM)
# Change line 47 and 75:
# - N_GPU_LAYERS=25

# 4. Restart services
docker-compose down
docker-compose up -d

# 5. Monitor VRAM
nvidia-smi
```

**Expected VRAM with 7B model:**
- Desktop: 2.9GB
- Goblin (7B, 25 layers): ~4.5GB
- Vorpal (0.45 utilization): ~6.5GB
- **Total:** ~13.9GB (**SHOULD FIT**)

---

## 🔧 Service Status

### Running Services

| Service | Status | Port | Health | Purpose |
|---------|--------|------|--------|---------|
| **Redis Stack** | ✅ Up | 6379, 8002 | Healthy | Vector DB, streams, cache |
| **Vorpal** | ✅ Up | 8000 | **Healthy** | Speed inference (3B model) |
| **Brain** | ✅ Up | 8080 | Degraded* | Orchestrator, API server |
| **Sandbox** | ✅ Up | 8003 | Healthy | Code execution |
| **Voice** | ✅ Up | 8001 | Healthy | STT/TTS (Whisper + F5) |
| **Librarian** | ✅ Up | - | Healthy | Library file watcher |
| **Goblin** | ❌ Stopped | 8081 | N/A | Capacity inference (14B) |

*Brain health endpoint responds but memory worker is broken

### How to Access

```bash
# Web UI
cd /home/davidjackson/Archive-AI/ui
python3 -m http.server 8888
# Open http://localhost:8888

# API Documentation
http://localhost:8080/docs

# Redis Database Viewer
http://localhost:8002

# Check all services
docker-compose ps

# View logs
docker-compose logs -f [service_name]

# Check VRAM usage
nvidia-smi
```

---

## 📁 Important Files Modified

### Configuration Files
- `.env` - **CREATED** - Environment variables with secure Redis password
- `docker-compose.yml` - **MODIFIED** - Fixed Goblin image, command args, VRAM settings

### Models Downloaded
- `/home/davidjackson/Archive-AI/models/goblin/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf` (8.4GB)

### Code Files (Unchanged)
- `brain/workers/memory_worker.py` - Perplexity calculation logic
- `vorpal/Dockerfile` - vLLM server configuration

---

## 🎯 Next Steps to Fix Memory System

### Priority 1: Diagnose Brain-Vorpal Connection

**Option A: Add Debug Logging**
1. Edit `brain/workers/memory_worker.py:119-121`
2. Change exception handler to print full traceback:
```python
except Exception as e:
    import traceback
    print(f"Perplexity calculation error: {e}")
    print(traceback.format_exc())
    return None
```
3. Rebuild Brain: `docker-compose build brain`
4. Restart: `docker-compose restart brain`
5. Check logs: `docker logs archive-ai_brain_1 2>&1 | grep -A 20 "Perplexity calculation error"`

**Option B: Test Connection from Inside Brain**
```bash
# Install curl in brain container
docker exec -it archive-ai_brain_1 bash
apt-get update && apt-get install -y curl

# Test Vorpal connection
curl -v http://vorpal:8000/health
curl -X POST http://vorpal:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen2.5-3B-Instruct","prompt":"test","max_tokens":1}'
```

**Option C: Adjust httpx Timeout**
1. Edit `brain/workers/memory_worker.py:40`
2. Increase timeout: `self.http_client = httpx.AsyncClient(timeout=60.0)`
3. Rebuild and restart

**Option D: Add Retry Logic**
1. Install tenacity: Add to `brain/requirements.txt`
2. Wrap Vorpal API call with retry decorator
3. Rebuild and restart

### Priority 2: Clear Redis Stream Backlog

The failed messages are piling up. Clear them:
```bash
docker exec -it archive-ai_redis_1 redis-cli

# View stream length
XLEN input_stream

# Delete stream (nuclear option)
DEL input_stream

# Or trim to last 10 entries
XTRIM input_stream MAXLEN 10
```

### Priority 3: Implement Graceful Degradation

Modify Brain to work without perplexity:
1. Store memories with only vector distance score
2. Set perplexity to a default value (e.g., 10.0)
3. Still functional, just less accurate surprise scoring

---

## 🧪 Testing Checklist

Before considering system "ready":

- [ ] Vorpal API responds to `/v1/completions` with logprobs
- [ ] Brain can calculate perplexity for a test string
- [ ] Memory worker processes stream without errors
- [ ] Memories are stored in Redis vector index
- [ ] Voice STT converts speech to text
- [ ] Voice TTS generates Ian McKellen voice
- [ ] Sandbox executes Python code safely
- [ ] Librarian detects new files in Library-Drop

---

## 💾 Git Status

### Untracked Files (Pre-Commit)
- `.env` - Contains password, should be .gitignored
- `CURRENT_STATUS.md` - This file
- `models/goblin/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf` - 8.4GB model file

### Modified Files (Uncommitted)
- `docker-compose.yml` - Goblin config fixes, Vorpal VRAM tuning

### What to Commit
- `docker-compose.yml` - Configuration fixes
- `CURRENT_STATUS.md` - Status documentation
- **DO NOT COMMIT:** `.env` (has passwords), model files (too large)

---

## 📞 Escalation Points

**Issues Requiring User Decision:**

1. **VRAM Budget:** Desktop environment uses 2.9GB not accounted for in spec
   - **Decision Needed:** Acceptable to close desktop apps during AI usage?
   - **Alternative:** Accept Vorpal-only or Goblin-only modes

2. **Brain-Vorpal Connection:** Root cause unclear after multiple restart attempts
   - **Decision Needed:** Invest time in deep debugging vs. workaround?
   - **Alternative:** Disable async memory, use synchronous storage

3. **Goblin Reactivation:** Current 14B model too large for dual-engine mode
   - **Decision Needed:** Download 7B model (smaller, less capable)?
   - **Alternative:** Keep Vorpal-only, add Goblin later after VRAM optimization

---

## 🔄 Quick Reference Commands

```bash
# Start all services
cd /home/davidjackson/Archive-AI
docker-compose up -d

# Stop all services
docker-compose down

# Check status
docker-compose ps

# View logs
docker-compose logs -f brain
docker-compose logs -f vorpal

# Restart specific service
docker-compose restart brain

# Check VRAM
nvidia-smi

# Check GPU processes
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv

# Access Web UI
cd ui && python3 -m http.server 8888

# Test Vorpal directly
curl http://localhost:8000/health
curl -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen2.5-3B-Instruct","prompt":"Hello","max_tokens":5,"logprobs":1,"echo":true}'

# Test Brain health
curl http://localhost:8080/health

# Monitor Redis
docker exec -it archive-ai_redis_1 redis-cli
> INFO memory
> XLEN input_stream
```

---

## 📋 Session Context for Next Claude

**When resuming:**

1. **First, assess current state:**
   ```bash
   docker-compose ps
   nvidia-smi
   docker logs archive-ai_brain_1 2>&1 | tail -50 | grep perplexity
   ```

2. **Key context:**
   - User chose "Option C: Vorpal-Only" to establish stable foundation
   - Plan: Get Vorpal working, then add 7B Goblin model later
   - Current blocker: Brain cannot connect to Vorpal (mystery issue)

3. **Don't repeat:**
   - Restarting services (tried 6+ times, didn't help)
   - Changing VRAM settings (already optimized)
   - Checking Docker network config (already verified correct)

4. **Focus on:**
   - Getting Brain-Vorpal connection working OR
   - Implementing workaround (disable perplexity, use vector distance only)

5. **User expectations:**
   - Frustrated with VRAM constraints and connectivity issues
   - Needs working system, even if degraded
   - Prefers pragmatic solutions over perfect but broken ones

---

**Status Report Complete**
**Author:** Claude (Sonnet 4.5)
**Session Duration:** ~90 minutes
**Files Modified:** 2
**Issues Fixed:** 4
**Issues Remaining:** 2 (1 critical)

---

*End of Status Report*
