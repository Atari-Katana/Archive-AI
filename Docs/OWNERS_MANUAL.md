# Archive-AI v7.5 - Owner's Manual
## Technical Documentation & System Architecture

**Version**: 7.5  
**Last Updated**: December 2025  
**Target Hardware**: NVIDIA RTX 5060 Ti (16GB VRAM) + 64GB RAM

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [Component Details](#component-details)
5. [Configuration](#configuration)
6. [Memory System](#memory-system)
7. [Agent System](#agent-system)
8. [API Reference](#api-reference)
9. [Development Guide](#development-guide)
10. [Troubleshooting](#troubleshooting)
11. [Performance Tuning](#performance-tuning)
12. [Security](#security)

---

## System Overview

Archive-AI is a local-first AI cognitive framework with permanent memory capabilities. It combines multiple LLM engines, vector-based memory storage, and agentic reasoning to provide an intelligent, privacy-preserving AI assistant.

### Core Principles

- **Local-First**: All processing happens on your hardware
- **Memory Persistence**: Conversations are stored based on "surprise score"
- **Multi-Engine**: Vorpal (speed) + Goblin (capacity) for optimal resource usage
- **Agentic**: ReAct-based reasoning with tool use
- **Privacy**: No data leaves your machine

### Key Features

- Dual LLM inference engines (GPU + CPU)
- Vector-based semantic memory with RedisStack
- Chain of Verification for hallucination mitigation
- ReAct agents with 11 tools
- Voice I/O (Speech-to-Text + Text-to-Speech)
- Document library ingestion
- Sandbox code execution
- Semantic query routing

---

## Architecture

### System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        User Interface                        │
│                    (Web UI - Port 8888)                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Archive-Brain (Port 8080)                 │
│  ┌────────────────┬─────────────┬────────────────────────┐  │
│  │ FastAPI Server │  Semantic   │  Memory Worker         │  │
│  │                │  Router     │  (Background)          │  │
│  └────────────────┴─────────────┴────────────────────────┘  │
└──┬──────────┬──────────┬──────────┬──────────┬──────────┬──┘
   │          │          │          │          │          │
   ▼          ▼          ▼          ▼          ▼          ▼
┌─────┐  ┌────────┐ ┌────────┐ ┌────────┐ ┌───────┐ ┌────────┐
│Redis│  │Vorpal  │ │Goblin  │ │Sandbox │ │Voice  │ │Library │
│Stack│  │(vLLM)  │ │(llama  │ │(Code)  │ │(STT/  │ │(Docs)  │
│     │  │        │ │.cpp)   │ │        │ │TTS)   │ │        │
│6379 │  │8000    │ │8081    │ │8003    │ │8001   │ │Watch   │
└─────┘  └────────┘ └────────┘ └────────┘ └───────┘ └────────┘
```

### Data Flow

1. **User Input** → Web UI (8888) → Brain API (8080)
2. **Semantic Routing** → Detect intent (chat, search, help)
3. **Memory Capture** → Redis Stream → Background Worker
4. **Surprise Scoring** → Perplexity + Vector Distance → Store if > 0.7
5. **LLM Processing** → Vorpal (fast) or Goblin (deep reasoning)
6. **Response** → UI with typewriter effect

---

## Technology Stack

### Backend Services

| Service | Technology | Purpose | Port |
|---------|-----------|---------|------|
| **Brain** | FastAPI + Python 3.11 | Orchestration, API | 8080 |
| **Vorpal** | vLLM 0.13.0 | Fast GPU inference | 8000 |
| **Goblin** | llama.cpp | CPU-based reasoning | 8081 |
| **Redis** | Redis Stack 7.x | State + Vector DB | 6379 |
| **Sandbox** | FastAPI + RestrictedPython | Code execution | 8003 |
| **Voice** | FastAPI + Faster-Whisper + F5-TTS | Speech I/O | 8001 |
| **Librarian** | Python + Watchdog | Document ingestion | N/A |

### Frontend

- **Framework**: Vanilla JavaScript + HTML/CSS
- **Features**: Typewriter effect, real-time metrics, memory browser
- **Served on**: Port 8888 (user-configured)

### AI Models

| Engine | Model | Size | Quantization | VRAM | Purpose |
|--------|-------|------|--------------|------|---------|
| Vorpal | Qwen/Qwen2.5-7B-Instruct-AWQ | 7B | AWQ 4-bit | ~9.6GB | Chat, routing, perplexity |
| Goblin | DeepSeek-R1-Distill-Qwen-14B | 14B | Q4_K_M (GGUF) | CPU (8GB RAM) | Reasoning, coding |
| Embeddings | all-MiniLM-L6-v2 | 22M | FP32 | CPU | Vector embeddings (384-dim) |

### Python Libraries

**Core**:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `httpx` - Async HTTP client
- `redis` - Redis client + RedisStack
- `pydantic` - Data validation

**AI/ML**:
- `sentence-transformers` - Embeddings
- `vllm` - GPU inference
- `faster-whisper` - Speech-to-Text
- `f5-tts` - Text-to-Speech

**Utilities**:
- `psutil` - System metrics
- `watchdog` - File monitoring
- `RestrictedPython` - Safe code execution

---

## Component Details

### 1. Archive-Brain (Orchestrator)

**Location**: `/brain/`

The central nervous system of Archive-AI. Handles all API requests, coordinates between services, and manages the memory system.

**Key Modules**:
- `main.py` - FastAPI application, endpoints
- `config.py` - Configuration management
- `stream_handler.py` - Redis stream capture
- `router.py` - Semantic intent routing
- `verification.py` - Chain of Verification logic
- `workers/memory_worker.py` - Background memory processing
- `workers/archiver.py` - Memory archival worker
- `memory/vector_store.py` - RedisVL interface
- `agents/` - ReAct agent implementation

**Startup Sequence**:
1. Load configuration from environment
2. Connect to Redis
3. Initialize vector store + create index
4. Wait for Vorpal health check (120s timeout)
5. Start memory worker (background task)
6. Start archival worker (daily at 3 AM)
7. Begin serving requests

**Health Checks**:
- `/health` - Service status
- `/metrics` - System metrics (CPU, RAM, VRAM, tokens/sec)

### 2. Vorpal Engine (Speed)

**Location**: `/vorpal/`  
**Image**: `archive-ai/vorpal:latest`

GPU-accelerated inference using vLLM for fast, streaming responses.

**Configuration**:
```yaml
GPU Memory: 60% (~9.6GB)
Model: Qwen/Qwen2.5-7B-Instruct-AWQ
Max Model Length: 8192 tokens
Chunked Prefill: Enabled (2048 tokens)
Quantization: AWQ (4-bit)
Backend: FlashAttention 2
```

**Endpoints**:
- `GET /health` - Health check
- `POST /v1/chat/completions` - OpenAI-compatible chat
- `POST /v1/completions` - Text completion (used for perplexity)
- `GET /metrics` - Prometheus metrics

**Performance**:
- Time to First Token: ~40-80ms
- Tokens/Second: ~80-100 tok/s
- Latency: ~0.78s for short responses

### 3. Goblin Engine (Capacity)

**Location**: `/goblin/` (uses official llama.cpp Docker image)

CPU-based inference for deep reasoning and coding tasks.

**Configuration**:
```yaml
Model: DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf
Context: 8192 tokens
Threads: 16
Batch Size: 512
Memory Limit: 8GB RAM
GPU Layers: 0 (CPU-only)
```

**Performance**:
- Response Time: ~26s (33x slower than Vorpal)
- Quality: Higher reasoning capability
- Use Case: Complex analysis, coding, research

### 4. Redis Stack (State Engine)

**Configuration**:
```yaml
Max Memory: 20GB
Policy: allkeys-lru
Persistence: AOF (appendonly yes)
Protected Mode: No
```

**Data Structures**:
- **Streams**: `archive:input:stream` (message capture)
- **Hash**: `memory:last_id` (worker checkpoint)
- **Vector Index**: `memory_index` (HNSW, 384-dim)
- **Keys**: `memory:*` (stored memories)

**Memory Schema**:
```json
{
  "id": "memory:1766985567328",
  "message": "User's message text",
  "perplexity": 95.66,
  "surprise_score": 0.949,
  "timestamp": 1766985567.328,
  "session_id": "default",
  "embedding": [0.123, -0.456, ...]  // 384 dimensions
}
```

### 5. Sandbox (Code Execution)

**Location**: `/sandbox/`

Isolated Python execution environment using RestrictedPython.

**Security Measures**:
- No network access
- No file system access
- Blocked modules: `os`, `subprocess`, `socket`, `requests`
- 10-second timeout
- Limited builtins (no `open`, `eval`, `exec`)

**Allowed**:
- Math operations
- Data structures (list, dict, set)
- String manipulation
- Limited stdlib (`math`, `random`, `datetime`, `json`)

### 6. Voice Service

**Location**: `/voice/`

**Components**:
- **STT**: Faster-Whisper (base model, CPU, int8)
- **TTS**: F5-TTS (CPU mode)
- **Voice**: Ian McKellen reference

**Endpoints**:
- `POST /transcribe` - Audio → Text
- `POST /synthesize` - Text → Audio (WAV)

### 7. Librarian Service

**Location**: `/librarian/`

Monitors `~/ArchiveAI/Library-Drop` for documents and ingests them into the vector store.

**Supported Formats**:
- PDF, TXT, MD
- Chunking: 512-token overlapping chunks
- Index: Separate from conversation memories

---

## Configuration

### Environment Variables (.env)

```bash
# === Security ===
REDIS_PASSWORD=<generated>  # Use: openssl rand -base64 32

# === Service Ports ===
BRAIN_PORT=8080

# === Memory Archival ===
ARCHIVE_DAYS=30          # Archive memories older than N days
ARCHIVE_KEEP=1000        # Keep N most recent in Redis
ARCHIVE_HOUR=3           # Daily archival hour (0-23)
ARCHIVE_MINUTE=0

# === Voice Configuration ===
WHISPER_MODEL=base       # tiny, base, small, medium, large
WHISPER_DEVICE=cpu
TTS_DEVICE=cpu

# === Library Drop ===
LIBRARY_DROP=~/ArchiveAI/Library-Drop

# === Logging ===
LOG_LEVEL=INFO           # DEBUG, INFO, WARNING, ERROR

# === GPU Configuration ===
CUDA_VISIBLE_DEVICES=0
VORPAL_GPU_MEMORY_UTILIZATION=0.60  # 0.0-1.0
VORPAL_MODEL=Qwen/Qwen2.5-7B-Instruct-AWQ
```

### Model Configuration

**Changing Models**:

1. **Vorpal (GPU)**:
   ```bash
   # Edit .env
   VORPAL_MODEL=Qwen/Qwen2.5-14B-Instruct-AWQ
   VORPAL_GPU_MEMORY_UTILIZATION=0.90  # Adjust for VRAM
   
   # Restart
   docker-compose restart vorpal
   ```

2. **Goblin (CPU)**:
   ```bash
   # Download new GGUF model to ./models/goblin/
   wget <model_url> -O ./models/goblin/new-model.gguf
   
   # Edit .env
   GOBLIN_MODEL_PATH=/models/new-model.gguf
   
   # Restart
   docker-compose restart goblin
   ```

---

## Memory System

### Surprise Score Mechanism

The memory system uses a "Surprise Score" to determine what's worth remembering.

**Formula**:
```
surprise_score = (0.6 × normalized_perplexity) + (0.4 × vector_distance)
```

**Components**:

1. **Perplexity** (60% weight):
   - Measures how "unexpected" the message is to the LLM
   - Lower = predictable, Higher = surprising
   - Calculated via Vorpal's logprobs API
   - Normalized: `min(1.0, log(perplexity + 1) / 5.0)`

2. **Vector Distance** (40% weight):
   - Measures semantic novelty vs. existing memories
   - Uses cosine distance in 384-dim embedding space
   - 0.0 = very similar, 1.0 = very different

**Threshold**: 0.7  
Only messages with `surprise_score >= 0.7` are stored.

### Memory Worker Flow

```
User Message → Redis Stream → Memory Worker (background)
                                      ↓
                            Calculate Perplexity (Vorpal)
                                      ↓
                            Calculate Vector Distance (RedisVL)
                                      ↓
                            Compute Surprise Score
                                      ↓
                            If >= 0.7: Store in Vector DB
                                      ↓
                            Update last_id checkpoint
```

**Retry Logic**:
- Perplexity failures: 3 retries with 2s delay
- On failure: Skip message (log warning)

### Vector Store

**Index Configuration**:
```python
{
    "index_name": "memory_index",
    "algorithm": "HNSW",
    "dimensions": 384,
    "distance_metric": "COSINE",
    "initial_cap": 10000
}
```

**Search**:
```python
results = vector_store.search_similar(
    query_text="What did I say about Python?",
    top_k=5,
    session_id=None  # Optional filtering
)
```

### Archival System

**Purpose**: Move old memories from Redis (fast, expensive) to disk (slow, cheap)

**Schedule**: Daily at 3:00 AM (configurable)

**Policy**:
- Archive memories older than `ARCHIVE_DAYS` (default: 30)
- Keep `ARCHIVE_KEEP` most recent memories (default: 1000)
- Archive location: `./data/archive/`

**Format**: JSON Lines (`.jsonl`)

---

## Agent System

### ReAct Architecture

Archive-AI uses the ReAct (Reasoning + Acting) pattern:

```
┌─────────────────────────────────────────┐
│   1. THOUGHT: "I need to calculate..."  │
│   2. ACTION: Calculator                 │
│   3. ACTION INPUT: "50 * 8"             │
│   4. OBSERVATION: "Result: 400"         │
│   5. THOUGHT: "Now I have the answer"   │
│   6. ACTION: FINISH                     │
│   7. ACTION INPUT: "The answer is 400"  │
└─────────────────────────────────────────┘
```

### Tool Registry

**Basic Tools** (6 tools):
1. `Calculator` - Math expressions, sqrt, abs
2. `StringLength` - Count characters
3. `WordCount` - Count words
4. `ReverseString` - Reverse text
5. `ToUppercase` - Convert to uppercase
6. `ExtractNumbers` - Find numbers in text

**Advanced Tools** (5 tools):
1. `MemorySearch` - Search vector store
2. `CodeExecution` - Run Python in sandbox
3. `DateTime` - Get current time/date
4. `JSON` - Parse/validate/extract JSON
5. `WebSearch` - Placeholder (not implemented)

### Adding Custom Tools

1. Create tool function:
```python
# /brain/tools/my_tool.py
async def my_tool(input: str) -> str:
    """Clear description for the LLM."""
    return f"Result: {input.upper()}"
```

2. Register in `/brain/agents/basic_tools.py`:
```python
BASIC_TOOLS["MyTool"] = (
    "Description for LLM to understand when to use this tool",
    my_tool
)
```

3. Restart: `docker-compose restart brain`

---

## API Reference

### Core Endpoints

#### POST /chat
**Description**: Direct LLM conversation with semantic routing

**Request**:
```json
{
  "message": "What is 2+2?"
}
```

**Response**:
```json
{
  "response": "2 + 2 equals 4.",
  "engine": "vorpal"
}
```

**Routing**:
- `help` queries → Returns help text (no LLM call)
- `search memory` queries → Searches vector store
- Everything else → Vorpal chat

#### POST /verify
**Description**: Chat with Chain of Verification (hallucination mitigation)

**Request**:
```json
{
  "message": "What is the largest planet?",
  "use_verification": true
}
```

**Response**:
```json
{
  "initial_response": "Jupiter is the largest...",
  "verification_questions": ["Is Jupiter the largest?", "What is Jupiter's size?"],
  "verification_qa": [...],
  "final_response": "Verified: Jupiter is the largest planet...",
  "revised": false
}
```

#### POST /agent
**Description**: Basic ReAct agent with 6 tools

**Request**:
```json
{
  "question": "What is 15 multiplied by 23?",
  "max_steps": 10
}
```

**Response**:
```json
{
  "answer": "345",
  "steps": [
    {
      "step_number": 1,
      "thought": "I need to multiply 15 by 23",
      "action": "Calculator",
      "action_input": "15 * 23",
      "observation": "Result: 345"
    },
    {
      "step_number": 2,
      "thought": "I have the answer",
      "action": "FINISH",
      "action_input": "345"
    }
  ],
  "total_steps": 2,
  "success": true
}
```

#### POST /agent/advanced
**Description**: Advanced agent with all 11 tools

Same interface as `/agent`, but includes:
- Memory search
- Code execution
- Date/time
- JSON parsing

#### GET /memories
**Description**: List stored memories (paginated)

**Query Parameters**:
- `limit` (default: 50, max: 100)
- `offset` (default: 0)

**Response**:
```json
{
  "memories": [
    {
      "id": "memory:1766985567328",
      "message": "What is the capital of France?",
      "perplexity": 95.66,
      "surprise_score": 0.949,
      "timestamp": 1766985567.328,
      "session_id": "default"
    }
  ],
  "total": 127
}
```

#### POST /memories/search
**Description**: Semantic memory search

**Request**:
```json
{
  "query": "conversations about Python",
  "top_k": 5,
  "session_id": null
}
```

**Response**:
```json
{
  "memories": [
    {
      "id": "memory:1766985567328",
      "message": "Can you help me with Python?",
      "perplexity": 95.66,
      "surprise_score": 0.949,
      "timestamp": 1766985567.328,
      "session_id": "default",
      "similarity_score": 0.302
    }
  ],
  "total": 3
}
```

#### GET /health
**Description**: Service health check

**Response**:
```json
{
  "status": "healthy",
  "vorpal_model": "Qwen/Qwen2.5-7B-Instruct-AWQ",
  "services": {
    "redis": "connected",
    "vorpal": "healthy",
    "sandbox": "healthy"
  },
  "async_memory": "running"
}
```

#### GET /metrics
**Description**: System metrics

**Response**:
```json
{
  "uptime_seconds": 3600.5,
  "system": {
    "cpu_percent": 8.4,
    "memory_percent": 74.2,
    "memory_used_mb": 20884.8,
    "memory_total_mb": 32012.96,
    "gpu_memory_used_mb": 13722.0,
    "gpu_memory_total_mb": 16311.0,
    "gpu_memory_percent": 84.1,
    "tokens_per_sec": 95.3
  },
  "memory_stats": {
    "total_memories": 127,
    "storage_threshold": 0.7,
    "embedding_dim": 384,
    "index_type": "HNSW"
  },
  "services": [...],
  "version": "0.4.0"
}
```

---

## Development Guide

### Project Structure

```
archive-ai/
├── brain/              # Main orchestrator
│   ├── main.py         # FastAPI app
│   ├── config.py       # Configuration
│   ├── router.py       # Semantic routing
│   ├── verification.py # Chain of Verification
│   ├── agents/         # ReAct agent system
│   ├── memory/         # Vector store
│   ├── workers/        # Background tasks
│   └── requirements.txt
├── vorpal/             # vLLM service
│   └── Dockerfile
├── sandbox/            # Code execution
│   ├── server.py
│   └── requirements.txt
├── voice/              # Speech I/O
│   ├── server.py
│   └── requirements.txt
├── librarian/          # Document ingestion
│   ├── watcher.py
│   └── requirements.txt
├── ui/                 # Web interface
│   └── index.html
├── models/             # Model storage
│   ├── vorpal/
│   ├── goblin/
│   ├── whisper/
│   └── f5-tts/
├── data/               # Persistent data
│   ├── redis/
│   ├── archive/
│   └── library/
├── docker-compose.yml  # Service orchestration
└── .env                # Configuration
```

### Development Workflow

1. **Make Changes**:
   ```bash
   # Edit code in /brain/, /ui/, etc.
   vim brain/main.py
   ```

2. **Restart Service**:
   ```bash
   docker-compose restart brain
   ```

3. **Check Logs**:
   ```bash
   docker-compose logs -f brain
   ```

4. **Test**:
   ```bash
   curl -X POST http://localhost:8080/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "test"}'
   ```

### Adding Features

**Example: Add a new endpoint**

1. Edit `brain/main.py`:
```python
@app.get("/custom", tags=["custom"])
async def custom_endpoint():
    return {"message": "Hello!"}
```

2. Restart:
```bash
docker-compose restart brain
```

3. Test:
```bash
curl http://localhost:8080/custom
```

4. Check API docs:
```
http://localhost:8080/docs
```

---

## Troubleshooting

### Common Issues

#### 1. Vorpal Won't Start / OOM Error

**Symptom**: `ValueError: Free memory on device is less than desired GPU memory utilization`

**Solution**:
```bash
# Reduce GPU allocation
vim .env
# Set: VORPAL_GPU_MEMORY_UTILIZATION=0.50

# Or use smaller model
# Set: VORPAL_MODEL=Qwen/Qwen2.5-3B-Instruct

docker-compose down
docker-compose up -d
```

#### 2. Redis Connection Failed

**Symptom**: `ConnectionRefusedError: [Errno 111] Connection refused`

**Solution**:
```bash
# Check Redis is running
docker-compose ps redis

# Restart Redis
docker-compose restart redis

# Check logs
docker-compose logs redis
```

#### 3. Memory Worker Not Processing

**Symptom**: Messages sent but not appearing in `/memories`

**Check**:
```bash
# View worker logs
docker-compose logs brain | grep -i "memory_worker"

# Check surprise scores
docker-compose logs brain | grep -i "surprise"

# If scores < 0.7, they're being skipped (working as designed)
```

#### 4. VRAM Meter Shows "--"

**Symptom**: VRAM not displayed in UI

**Solution**:
```bash
# The brain container needs nvidia-smi
# Add to brain/Dockerfile:
RUN apt-get update && apt-get install -y nvidia-utils

# Rebuild
docker-compose build brain
docker-compose up -d brain
```

#### 5. Tokens/Sec Shows "--"

**Symptom**: No tokens/sec metric

**Cause**: No messages sent yet (metric calculated from Vorpal metrics)

**Solution**: Send a few chat messages, then refresh

### Logs

**View All Services**:
```bash
docker-compose logs -f
```

**Specific Service**:
```bash
docker-compose logs -f brain
docker-compose logs -f vorpal
docker-compose logs -f redis
```

**Filter Logs**:
```bash
docker-compose logs brain | grep -i error
docker-compose logs brain | grep -i "surprise"
docker-compose logs vorpal | grep -i "loading"
```

### Health Checks

```bash
# Overall health
curl http://localhost:8080/health

# Vorpal
curl http://localhost:8000/health

# Redis
redis-cli ping

# Sandbox
curl http://localhost:8003/health
```

---

## Performance Tuning

### VRAM Optimization

**Current Allocation** (16GB total):
- Desktop/OS: ~2.4GB
- Vorpal: ~9.6GB (60%)
- Remaining: ~4GB buffer

**Tuning**:
```bash
# For max performance (if no desktop GUI)
VORPAL_GPU_MEMORY_UTILIZATION=0.90  # ~14.5GB

# For stability
VORPAL_GPU_MEMORY_UTILIZATION=0.50  # ~8GB
```

### CPU Optimization (Goblin)

```bash
# Increase threads (if you have >16 cores)
GOBLIN_THREADS=24

# Increase batch size (more RAM)
GOBLIN_BATCH_SIZE=1024
```

### Redis Memory

**Current**: 20GB with LRU eviction

**Monitor**:
```bash
redis-cli INFO memory
```

**Tune**:
```bash
# Edit docker-compose.yml
REDIS_ARGS=--maxmemory 30gb --maxmemory-policy allkeys-lru
```

### Memory Worker Optimization

**Concurrent Processing**:
```python
# Edit workers/memory_worker.py
# Change stream read count
entries = await self.redis_client.xread(
    {config.REDIS_STREAM_KEY: self.last_id},
    count=50,  # Process 50 at a time (default: 10)
    block=1000
)
```

---

## Security

### Attack Surface

**Exposed Ports**:
- 8080: Brain API (local only)
- 8888: Web UI (user-configured)
- 6379: Redis (Docker network only)

**Recommendations**:
1. Use firewall to block external access
2. Run behind reverse proxy (nginx) with auth
3. Use strong `REDIS_PASSWORD`
4. Don't expose to public internet

### Code Execution Sandbox

**Protections**:
- RestrictedPython limits AST
- No `import os`, `subprocess`, `socket`
- No file I/O (`open`, `write`)
- 10-second timeout
- No network access

**Still Vulnerable To**:
- CPU/memory exhaustion (use resource limits)
- Algorithmic complexity attacks

**Recommendation**: Only expose to trusted users

### Data Privacy

**All data stays local**:
- No telemetry
- No cloud API calls (except if you add web search)
- Models run on your hardware
- Redis data in `./data/redis/`

---

## Appendix

### Quick Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f

# Restart single service
docker-compose restart brain

# Check GPU usage
nvidia-smi

# Check disk usage
du -sh data/

# Backup memories
tar -czf memories-backup.tar.gz data/redis/

# Clean old models
docker system prune -a

# Update model
docker-compose pull vorpal
docker-compose up -d vorpal
```

### File Locations

- **Logs**: `docker-compose logs <service>`
- **Memory Data**: `./data/redis/`
- **Archived Memories**: `./data/archive/`
- **Library Chunks**: `./data/library/`
- **Models**: `./models/*/`
- **Config**: `./.env`

### Monitoring

**Prometheus Metrics**: Available at `http://localhost:8000/metrics` (Vorpal)

**System Metrics**: Available at `http://localhost:8080/metrics` (Brain)

---

**End of Owner's Manual**  
For user-focused documentation, see `USER_MANUAL.md`
