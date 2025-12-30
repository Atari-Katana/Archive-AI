# Archive-AI Owner's Manual

**Version:** 7.5
**Last Updated:** 2025-12-29
**For:** System Administrators and Technical Users

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Service Components](#service-components)
3. [Data Flow](#data-flow)
4. [Configuration](#configuration)
5. [Memory System Architecture](#memory-system-architecture)
6. [Dual-Engine Design](#dual-engine-design)
7. [Security](#security)
8. [Performance Tuning](#performance-tuning)
9. [Monitoring](#monitoring)
10. [Backup and Recovery](#backup-and-recovery)
11. [Troubleshooting](#troubleshooting)
12. [Development](#development)

---

## System Architecture

### Overview

Archive-AI is a **microservices-based** AI system designed for local deployment on consumer hardware. The architecture emphasizes:

- **Privacy**: All processing happens locally
- **Performance**: Optimized for single 16GB GPU + 32-64GB RAM
- **Reliability**: Independent services with health checks
- **Scalability**: Horizontal scaling possible via Redis clustering

### Technology Stack

| Layer | Technology |
|-------|------------|
| **Container Orchestration** | Docker Compose 2.20+ |
| **API Framework** | FastAPI (Python 3.11+) |
| **Async Runtime** | asyncio + httpx |
| **State Management** | Redis Stack 7.2+ |
| **Vector Search** | RediSearch + RedisVL |
| **Embedding Model** | sentence-transformers/all-MiniLM-L6-v2 |
| **LLM Serving** | vLLM (Vorpal), llama.cpp (Goblin) |
| **GPU Compute** | CUDA 12.x, nvidia-docker |
| **Language** | Python 3.11+ |

### Network Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     archive-net (bridge)                 │
│  ┌──────────┐  ┌────────┐  ┌─────────┐  ┌───────────┐ │
│  │  Brain   │←→│ Vorpal │  │ Goblin  │  │   Redis   │ │
│  │  :8080   │  │ :8000  │  │ :8081   │  │   :6379   │ │
│  └────┬─────┘  └────────┘  └─────────┘  └─────┬─────┘ │
│       │                                        │        │
│       ├───→ Sandbox :8003                     │        │
│       ├───→ Voice :8001                       │        │
│       └───→ Librarian (no exposed port)       │        │
│                                                │        │
└────────────────────────────────────────────────┼────────┘
                                                 │
                                          RedisInsight
                                              :8002
```

**Port Mapping:**
- `8080` → Brain (FastAPI orchestrator)
- `8000` → Vorpal (vLLM inference engine)
- `8081` → Goblin (llama.cpp inference, mapped from internal :8080)
- `6379` → Redis (database)
- `8002` → RedisInsight (web UI for Redis)
- `8001` → Voice (STT/TTS service)
- `8003` → Sandbox (code execution)
- `8888` → Web UI (static file server)

**Service Dependencies:**
```
Brain depends_on → [Redis, Vorpal]
Librarian depends_on → [Redis]
Voice (independent)
Sandbox (independent)
Goblin (optional)
```

---

## Service Components

### 1. Brain (Orchestrator)

**Location:** `/home/user/Archive-AI/brain/`

**Purpose:** Central API gateway and coordination layer

**Key Files:**
- `main.py` - FastAPI application with all endpoints (1,615 lines)
- `config.py` - Configuration management
- `router.py` - Intent classification
- `stream_handler.py` - Redis Stream input capture
- `verification.py` - Chain of Verification implementation

**Responsibilities:**
- HTTP API endpoints (14 routes)
- Request proxying to Vorpal/Goblin
- Background workers coordination
- Redis Stream management
- Health checks and metrics

**Dependencies:**
```python
fastapi==0.104.1
httpx==0.25.1
redis[asyncio]==5.0.1
sentence-transformers==2.2.2
redisvl==0.13.2
pydantic==2.5.0
```

**Environment Variables:**
```bash
REDIS_URL=redis://redis:6379
VORPAL_URL=http://vorpal:8000
GOBLIN_URL=http://goblin:8080
SANDBOX_URL=http://sandbox:8000
VOICE_URL=http://voice:8001
ASYNC_MEMORY=true
VORPAL_MODEL=Qwen/Qwen2.5-7B-Instruct-AWQ  # or Qwen/Qwen2.5-3B-Instruct
```

**Resource Usage:**
- CPU: ~0.1% idle, ~5-10% during inference
- RAM: ~525 MB
- No GPU usage (CPU-bound)

---

### 2. Vorpal (Speed Engine)

**Location:** `/home/user/Archive-AI/vorpal/`

**Purpose:** Fast LLM inference for chat, routing, perplexity

**Engine:** vLLM (OpenAI-compatible API)

**Models:**
- **Default:** Qwen/Qwen2.5-3B-Instruct (3 billion parameters)
- **AWQ Profile:** Qwen/Qwen2.5-7B-Instruct-AWQ (7 billion parameters, quantized)

**VRAM Usage:**
- 3B model: ~5.8 GB (includes KV cache, PyTorch overhead)
- 7B AWQ model: ~6.0 GB (quantized weights, efficient)

**Configuration:**
```yaml
environment:
  - GPU_MEMORY_UTILIZATION=0.45    # 45% of total VRAM (tunable)
  - CUDA_VISIBLE_DEVICES=0
command:
  - "Qwen/Qwen2.5-7B-Instruct-AWQ"
  - "--host" "0.0.0.0"
  - "--port" "8000"
  - "--gpu-memory-utilization" "0.45"
  - "--max-model-len" "4096"       # Context window
  - "--max-num-seqs" "64"          # Batch size
```

**API Endpoints:**
- `POST /v1/completions` - OpenAI-compatible completion
- `POST /v1/chat/completions` - Chat format
- `GET /health` - Health check
- `GET /v1/models` - List loaded models

**Performance:**
- **Throughput:** 50-100 tokens/second (7B AWQ on RTX 5060 Ti)
- **Latency:** ~2-4 seconds for typical responses
- **Concurrent Requests:** 5-10 (limited by VRAM)

**Model Loading Time:**
- Cold start: ~2 minutes (model download + CUDA graph compilation)
- Warm start: ~30 seconds (if model cached)

---

### 3. Goblin (Capacity Engine)

**Location:** `/home/user/Archive-AI/models/goblin/`

**Purpose:** Deep reasoning, code analysis, complex tasks

**Engine:** llama.cpp server

**Models:**
- **14B Profile:** DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf (8.4 GB file)
- **7B Profile:** DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf (4.4 GB file)

**VRAM Usage:**
- 14B model (28 GPU layers): ~8-10 GB
- 7B model (20 GPU layers): ~4-5 GB

**Configuration:**
```yaml
environment:
  - MODEL_PATH=/models/DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf
  - N_GPU_LAYERS=20                # Number of layers on GPU
  - CTX_SIZE=8192
  - CUDA_VISIBLE_DEVICES=0
command:
  - "--model" "/models/DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf"
  - "--host" "0.0.0.0"
  - "--port" "8080"
  - "--ctx-size" "8192"
  - "--n-gpu-layers" "20"
  - "--threads" "8"
  - "--batch-size" "512"
  - "--ubatch-size" "512"
  - "--flash-attn" "on"
  - "--cont-batching"
  - "--metrics"
```

**API Endpoints:**
- `POST /completion` - Text completion
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

**Performance:**
- **Throughput:** 20-40 tokens/second (7B Q4_K_M)
- **Latency:** ~5-10 seconds for complex reasoning
- **Context:** 8192 tokens

**Status:** Optional (not used by default endpoints, available for custom agents)

---

### 4. Redis Stack

**Location:** Container image `redis/redis-stack:latest`

**Purpose:** State engine, vector database, stream processing

**Modules:**
- **RedisJSON** - JSON document storage
- **RediSearch** - Full-text and vector search
- **RedisGraph** - Graph database (unused)
- **RedisTimeSeries** - Time-series data (unused)

**Configuration:**
```yaml
environment:
  - REDIS_ARGS=--maxmemory 20gb --maxmemory-policy allkeys-lru --appendonly yes --protected-mode no
ports:
  - "6379:6379"      # Redis protocol
  - "8002:8001"      # RedisInsight web UI
volumes:
  - ./data/redis:/data
```

**Memory Management:**
- **Max Memory:** 20 GB
- **Eviction Policy:** allkeys-lru (least recently used)
- **Persistence:** AOF (append-only file) + RDB snapshots
- **Current Usage:** ~6-50 MB (very low, room for 400x growth)

**Data Structures:**
- **Streams:** `session:input_stream` (max 1000 entries)
- **Hashes:** `memory:timestamp` (384-byte vectors + metadata)
- **Indexes:** `memory_index` (HNSW vector index), `library_index` (library chunks)
- **Keys:** `memory_last_id` (stream position tracker)

**Vector Index Configuration:**
```python
schema = (
    NumericField("timestamp"),
    TextField("message"),
    NumericField("perplexity"),
    NumericField("surprise_score"),
    TextField("session_id"),
    VectorField("embedding",
        "HNSW", {
            "TYPE": "FLOAT32",
            "DIM": 384,
            "DISTANCE_METRIC": "COSINE"
        }
    )
)
```

---

### 5. Sandbox (Code Execution)

**Location:** `/home/user/Archive-AI/sandbox/`

**Purpose:** Safe Python code execution for agents

**Security Model:**
- Read-only filesystem
- No new privileges
- Limited builtins (no `open`, `exec`, `eval`, `__import__`)
- No network access
- No file system access
- Tmpfs `/tmp` only (512MB, noexec, nosuid)

**Resource Limits:**
```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
```

**Available Builtins:**
```python
SAFE_BUILTINS = {
    'print', 'len', 'range', 'enumerate', 'zip',
    'sum', 'min', 'max', 'abs', 'round', 'sorted',
    'list', 'dict', 'set', 'tuple', 'str', 'int',
    'float', 'bool', 'type', 'isinstance'
}
```

**Available Modules:**
```python
import math
import random
import datetime
import json
import re
```

**API:**
- `POST /execute` - Execute code with timeout
- `GET /health` - Health check

**Timeout:** 1-30 seconds (configurable per request)

---

### 6. Voice Service

**Location:** `/home/user/Archive-AI/voice/`

**Purpose:** Speech-to-text and text-to-speech

**Components:**
1. **Faster-Whisper** (STT)
   - Model: base (configurable: tiny, base, small, medium, large)
   - Device: CPU with int8 quantization
   - Features: VAD, beam search, language detection

2. **F5-TTS** (TTS)
   - Neural TTS with voice cloning
   - Device: CPU or CUDA
   - Natural voice synthesis

**Configuration:**
```yaml
environment:
  - WHISPER_MODEL=base
  - WHISPER_DEVICE=cpu
  - WHISPER_COMPUTE_TYPE=int8
  - TTS_DEVICE=cpu
  - TTS_MODEL_CACHE=/models/cache
volumes:
  - ./models/whisper:/root/.cache/huggingface
  - ./models/f5-tts:/models/cache
```

**Resource Usage:**
- RAM: ~2.16 GB (models loaded in memory)
- CPU: Burst to 100% during transcription/synthesis
- Inference Time: 2-5s (STT), 3-8s (TTS)

---

### 7. Librarian (Document Ingestion)

**Location:** `/home/user/Archive-AI/librarian/`

**Purpose:** Watch folder, process documents, index content

**Components:**
- `watcher.py` - File system monitoring (watchdog)
- `processor.py` - PDF/text extraction and chunking
- `storage.py` - RedisVL vector storage

**Watch Folder:** `~/ArchiveAI/Library-Drop/`

**Supported Formats:**
- PDF (PyPDF2 + pytesseract OCR)
- Plain text (.txt)
- Markdown (.md)

**Processing Pipeline:**
```
File Drop → Event Detection → Text Extraction → Chunking → Embedding → Redis Storage
```

**Chunking Strategy:**
- **Size:** 250 tokens per chunk
- **Overlap:** 50 tokens between chunks
- **Tokenizer:** GPT-4 (cl100k_base encoding)
- **Reason:** Balances context vs granularity for search

**Embedding:**
- **Model:** sentence-transformers/all-MiniLM-L6-v2
- **Dimension:** 384
- **Method:** HFTextVectorizer (RedisVL)
- **Storage:** Binary format (as_buffer=True)

---

## Data Flow

### Chat Request Flow

```
┌──────────────────────────────────────────────────────────────┐
│ 1. User sends POST /chat {"message": "Hello"}               │
└──────────┬───────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. Brain receives request                                    │
│    - Validates input                                          │
│    - Captures to Redis Stream (async, non-blocking)          │
│      └─→ XADD session:input_stream * message "Hello"         │
└──────────┬───────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. Brain proxies to Vorpal                                   │
│    POST http://vorpal:8000/v1/completions                    │
│    {                                                          │
│      "model": "Qwen/Qwen2.5-7B-Instruct-AWQ",               │
│      "prompt": "Hello",                                       │
│      "max_tokens": 256,                                       │
│      "temperature": 0.7                                       │
│    }                                                          │
└──────────┬───────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. Vorpal generates response                                 │
│    - Loads from KV cache if available                        │
│    - Runs forward pass                                        │
│    - Returns completion                                       │
│    {                                                          │
│      "choices": [{                                            │
│        "text": "Hello! How can I help you today?",          │
│        "finish_reason": "stop"                                │
│      }]                                                       │
│    }                                                          │
└──────────┬───────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. Brain returns response to user                            │
│    {                                                          │
│      "response": "Hello! How can I help you today?",        │
│      "engine": "vorpal"                                       │
│    }                                                          │
└───────────────────────────────────────────────────────────────┘


PARALLEL BACKGROUND PROCESS:

┌──────────────────────────────────────────────────────────────┐
│ Memory Worker (runs continuously)                            │
│                                                               │
│ 1. XREAD session:input_stream (blocking, waits for new)     │
│    └─→ Receives: {"message": "Hello", "timestamp": ...}     │
│                                                               │
│ 2. Calculate Perplexity                                      │
│    POST http://vorpal:8000/v1/completions                    │
│    {"prompt": "Hello", "logprobs": 1, "echo": true}         │
│    └─→ Extract logprobs, compute exp(avg(negative logprob)) │
│    └─→ Result: perplexity = 1.43 (very predictable)         │
│                                                               │
│ 3. Calculate Vector Distance                                 │
│    - Generate embedding for "Hello"                          │
│    - Search Redis vector index for nearest neighbor          │
│    FT.SEARCH memory_index "@embedding:[VECTOR ...KNN 1]"    │
│    └─→ Result: distance = 0.15 (similar greetings exist)    │
│                                                               │
│ 4. Calculate Surprise Score                                  │
│    surprise = 0.6 * normalize(perplexity) + 0.4 * distance  │
│    surprise = 0.6 * 0.05 + 0.4 * 0.15 = 0.09                │
│                                                               │
│ 5. Storage Decision                                          │
│    if surprise >= 0.7:                                        │
│        store_in_vector_index()                               │
│    else:                                                      │
│        skip  # "Hello" is too common, not stored             │
└───────────────────────────────────────────────────────────────┘
```

### Agent Execution Flow

```
POST /agent/advanced {"question": "Calculate fibonacci(10)"}
    │
    ▼
┌───────────────────────────────────────────────────────────────┐
│ ReActAgent.solve()                                            │
│   step = 1                                                    │
│   prompt = """                                                │
│   You have access to the following tools:                    │
│   - Calculator: Perform math operations                      │
│   - CodeExecution: Execute Python code                       │
│   ... (11 tools listed)                                      │
│                                                               │
│   Question: Calculate fibonacci(10)                          │
│   Thought:                                                    │
│   """                                                         │
└───────┬───────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ Vorpal LLM generates reasoning                                │
│   Thought: I need to write Python code to calculate          │
│            fibonacci(10) and then execute it.                 │
│   Action: CodeExecution                                       │
│   Action Input:                                               │
│   def fibonacci(n):                                           │
│       if n <= 1: return n                                     │
│       return fibonacci(n-1) + fibonacci(n-2)                  │
│   print(fibonacci(10))                                        │
└───────┬───────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ CodeExecution tool execution                                  │
│   POST http://sandbox:8000/execute                            │
│   {"code": "def fibonacci...", "timeout": 10}                │
│   └─→ Sandbox executes in isolated environment               │
│   └─→ Returns: {"output": "55", "error": null}               │
└───────┬───────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ ReActAgent appends observation                                │
│   step = 2                                                    │
│   prompt += """                                               │
│   Observation: 55                                             │
│   Thought:                                                    │
│   """                                                         │
└───────┬───────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ Vorpal LLM generates final answer                             │
│   Thought: I have the result from the code execution.        │
│   Action: Final Answer                                        │
│   Action Input: fibonacci(10) = 55                           │
└───────┬───────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ Return AgentResponse                                          │
│   {                                                           │
│     "answer": "fibonacci(10) = 55",                          │
│     "steps": [                                                │
│       {                                                       │
│         "step_number": 1,                                     │
│         "thought": "I need to write Python code...",         │
│         "action": "CodeExecution",                            │
│         "action_input": "def fibonacci...",                  │
│         "observation": "55"                                   │
│       },                                                      │
│       {                                                       │
│         "step_number": 2,                                     │
│         "thought": "I have the result...",                   │
│         "action": "Final Answer",                             │
│         "action_input": "fibonacci(10) = 55"                 │
│       }                                                       │
│     ],                                                        │
│     "total_steps": 2,                                         │
│     "success": true                                           │
│   }                                                           │
└───────────────────────────────────────────────────────────────┘
```

---

## Configuration

### Configuration Layers

Archive-AI uses a **two-layer configuration system**:

1. **`.env`** (required) - Secrets and production settings
2. **`config/user-config.env`** (optional) - Model tuning and runtime defaults

### .env File

**Location:** `/home/user/Archive-AI/.env`

**Required Variables:**
```bash
# Redis password (generate with: openssl rand -base64 32)
REDIS_PASSWORD=your_secure_password_here

# Port configuration
BRAIN_PORT=8080

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

**Optional Production Variables:**
```bash
# Archive settings
ARCHIVE_DAYS_THRESHOLD=30
ARCHIVE_KEEP_RECENT=1000
ARCHIVE_HOUR=3
ARCHIVE_MINUTE=0

# Feature flags
ASYNC_MEMORY=true
ARCHIVE_ENABLED=true

# Library
LIBRARY_DROP=/home/user/ArchiveAI/Library-Drop

# Voice
WHISPER_MODEL=base
WHISPER_DEVICE=cpu
TTS_DEVICE=cpu

# GPU
CUDA_VISIBLE_DEVICES=0
```

### config/user-config.env

**Location:** `/home/user/Archive-AI/config/user-config.env`

**Purpose:** Tune models and runtime without editing compose files

**Example:**
```bash
# Vorpal configuration
VORPAL_MODEL=Qwen/Qwen2.5-7B-Instruct-AWQ
VORPAL_GPU_MEMORY_UTILIZATION=0.45
VORPAL_MAX_MODEL_LEN=4096
VORPAL_MAX_NUM_SEQS=64

# Goblin configuration
GOBLIN_MODEL_PATH=/models/DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf
GOBLIN_N_GPU_LAYERS=20
GOBLIN_CTX_SIZE=8192
GOBLIN_THREADS=8

# Memory worker
MEMORY_START_FROM_LATEST=true
MEMORY_LAST_ID_KEY=memory_last_id
```

**Loading:** `go.sh` and `scripts/start.sh` automatically source this file

### Brain Configuration

**File:** `/home/user/Archive-AI/brain/config.py`

**Key Settings:**
```python
class Config:
    # Service URLs
    VORPAL_URL = os.getenv("VORPAL_URL", "http://vorpal:8000")
    GOBLIN_URL = os.getenv("GOBLIN_URL", "http://goblin:8080")
    SANDBOX_URL = os.getenv("SANDBOX_URL", "http://sandbox:8000")
    VOICE_URL = os.getenv("VOICE_URL", "http://voice:8001")
    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

    # Model configuration
    VORPAL_MODEL = os.getenv("VORPAL_MODEL", "Qwen/Qwen2.5-3B-Instruct")

    # Feature flags
    ASYNC_MEMORY = os.getenv("ASYNC_MEMORY", "true").lower() == "true"
    ARCHIVE_ENABLED = os.getenv("ARCHIVE_ENABLED", "true").lower() == "true"

    # Memory settings
    REDIS_STREAM_KEY = "session:input_stream"
    REDIS_MEMORY_PREFIX = "memory:"
    MEMORY_START_FROM_LATEST = os.getenv("MEMORY_START_FROM_LATEST", "true").lower() == "true"
    MEMORY_LAST_ID_KEY = "memory_last_id"

    # Archival settings
    ARCHIVE_DAYS_THRESHOLD = int(os.getenv("ARCHIVE_DAYS_THRESHOLD", "30"))
    ARCHIVE_KEEP_RECENT = int(os.getenv("ARCHIVE_KEEP_RECENT", "1000"))
    ARCHIVE_HOUR = int(os.getenv("ARCHIVE_HOUR", "3"))
    ARCHIVE_MINUTE = int(os.getenv("ARCHIVE_MINUTE", "0"))
    ARCHIVE_DIR = os.getenv("ARCHIVE_DIR", "/app/data/archive")

    # Timeouts
    REQUEST_TIMEOUT = 60.0  # HTTP timeout for LLM requests

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR = "/app/logs"
```

---

## Memory System Architecture

### Three-Tier Storage

```
┌───────────────────────────────────────────────────────────┐
│                     HOT STORAGE (Redis)                    │
│  - Most recent 1,000 memories                             │
│  - Vector index (HNSW) for fast semantic search           │
│  - Sub-second query times                                 │
│  - 384-dim embeddings (sentence-transformers)             │
│                                                            │
│  Eviction: Memories > 30 days OR count > 1,000           │
└──────────────┬────────────────────────────────────────────┘
               │
               │ Automatic Archival (daily 3 AM)
               ▼
┌───────────────────────────────────────────────────────────┐
│                   COLD STORAGE (Disk)                     │
│  - JSON files organized by month                          │
│  - Path: data/archive/YYYY-MM/memories-YYYYMMDD.json    │
│  - All memory fields preserved (except binary vectors)    │
│  - Searchable via file-based scan (slower)               │
│                                                            │
│  Retention: Indefinite (until manual deletion)            │
└───────────────────────────────────────────────────────────┘
```

### Surprise Score Algorithm

**Purpose:** Filter important/novel information from mundane repetition

**Formula:**
```python
surprise_score = 0.6 * perplexity_score + 0.4 * vector_distance

where:
  perplexity_score = normalize(perplexity, min=1.0, max=100.0)
  vector_distance = cosine_distance(new_embedding, nearest_existing)

Storage condition:
  if surprise_score >= 0.7:
      store_in_vector_index()
```

**Perplexity Calculation:**
```python
# Request from Vorpal with logprobs
response = await vorpal.post("/v1/completions", {
    "prompt": message,
    "max_tokens": 1,
    "logprobs": 1,
    "echo": true
})

# Extract token logprobs
logprobs = [token.logprob for token in response.choices[0].logprobs.tokens]

# Perplexity = exp(average negative logprob)
perplexity = math.exp(-sum(logprobs) / len(logprobs))
```

**Interpretation:**
- **Perplexity = 1.0** - Perfectly predictable (e.g., "hello")
- **Perplexity = 10-20** - Somewhat unexpected (normal conversation)
- **Perplexity = 50+** - Very unexpected (novel/complex questions)

**Vector Distance:**
```python
# Generate embedding for new message
embedding = sentence_transformer.encode(message)

# Find nearest neighbor in existing memories
results = redis.ft("memory_index").search(
    Query(f"@embedding:[VECTOR_RANGE 0.3 $vec]=>{$YIELD_DISTANCE_AS: distance}")
    .dialect(2),
    query_params={"vec": embedding.tobytes()}
)

# Distance to nearest
vector_distance = results[0].distance if results else 1.0
```

**Interpretation:**
- **Distance < 0.3** - Very similar to existing memory
- **Distance 0.3-0.7** - Moderately novel
- **Distance > 0.7** - Highly novel

### Memory Worker Implementation

**File:** `/home/user/Archive-AI/brain/workers/memory_worker.py`

**Lifecycle:**
```python
# Startup
await memory_worker.connect()
worker_task = asyncio.create_task(memory_worker.run())

# Run loop
async def run(self):
    while self.running:
        # Block until new stream entry
        entries = await redis.xread(
            {config.REDIS_STREAM_KEY: self.last_id},
            count=1,
            block=1000  # 1 second timeout
        )

        for stream_name, messages in entries:
            for message_id, data in messages:
                # Process message
                await self.process_message(data['message'])

                # Update position
                self.last_id = message_id
                await redis.set(config.MEMORY_LAST_ID_KEY, message_id)

# Shutdown
worker_task.cancel()
await worker_task
```

**Retry Logic:**
```python
PERPLEXITY_RETRIES = 3
PERPLEXITY_RETRY_DELAY = 2.0  # seconds

for attempt in range(PERPLEXITY_RETRIES):
    try:
        perplexity = await self.calculate_perplexity(message)
        break
    except httpx.HTTPError as e:
        if attempt < PERPLEXITY_RETRIES - 1:
            await asyncio.sleep(PERPLEXITY_RETRY_DELAY * (attempt + 1))
        else:
            logger.error(f"Perplexity calculation failed after {PERPLEXITY_RETRIES} attempts")
            return None
```

**Graceful Degradation:**
- If perplexity calculation fails, memory worker logs error but continues
- Messages without perplexity are not stored
- Stream processing continues for next message

---

## Dual-Engine Design

### Why Two Engines?

| Aspect | Vorpal (Speed) | Goblin (Capacity) |
|--------|---------------|-------------------|
| **Purpose** | Chat, routing, real-time | Deep reasoning, code analysis |
| **Model Size** | 3-7B parameters | 7-14B parameters |
| **Inference Speed** | 50-100 tokens/sec | 20-40 tokens/sec |
| **VRAM Usage** | 3.5-6 GB | 4-10 GB |
| **Context Window** | 4096-8192 tokens | 8192 tokens |
| **Quantization** | None or AWQ | Q4_K_M (4-bit) |
| **Framework** | vLLM (optimized batching) | llama.cpp (CPU fallback) |
| **Use Cases** | Every endpoint | Optional specialized tasks |

### VRAM Budget Management

**Total Available:** 16 GB (RTX 5060 Ti)

**Allocation:**
```
Desktop Environment: ~2-3 GB (cosmic-comp, browsers)
Available for AI:    ~13-14 GB

Option 1 (3B Profile):
  Vorpal (3B):        5.8 GB
  Goblin (14B):       8.0 GB (28 GPU layers)
  Total:             13.8 GB  ✓ Fits (barely)

Option 2 (7B AWQ Profile - RECOMMENDED):
  Vorpal (7B AWQ):    6.0 GB
  Goblin (7B):        4.5 GB (20 GPU layers)
  Total:             10.5 GB  ✓ Comfortable headroom

Option 3 (Vorpal-Only):
  Vorpal (7B AWQ):   10.4 GB (higher utilization)
  Total:             10.4 GB  ✓ Maximum single-engine performance
```

### Switching Profiles

**Use 7B AWQ profile (default):**
```bash
bash go.sh
# Automatically uses docker-compose.awq-7b.yml overlay
```

**Use 3B profile:**
```bash
docker-compose up -d
# Uses default docker-compose.yml (3B Vorpal + 14B Goblin)
```

**Vorpal-only (maximum chat performance):**
```bash
docker-compose up -d redis vorpal brain sandbox voice librarian
# Omit Goblin entirely
```

**Goblin-only (maximum reasoning):**
```bash
# Edit config/user-config.env
VORPAL_MODEL=Qwen/Qwen2.5-3B-Instruct  # Use smaller Vorpal
VORPAL_GPU_MEMORY_UTILIZATION=0.22     # Reduce VRAM usage

docker-compose up -d
```

### Model Download

**Vorpal models** (auto-downloaded by vLLM on first start):
```bash
# 3B model
docker-compose up vorpal  # Downloads Qwen/Qwen2.5-3B-Instruct from HuggingFace

# 7B AWQ model
docker-compose -f docker-compose.yml -f docker-compose.awq-7b.yml up vorpal
# Downloads Qwen/Qwen2.5-7B-Instruct-AWQ
```

**Goblin models** (manual download required):
```bash
# 14B model
cd models/goblin
huggingface-cli download \
  unsloth/DeepSeek-R1-Distill-Qwen-14B-GGUF \
  DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf \
  --local-dir . --local-dir-use-symlinks False

# 7B model
huggingface-cli download \
  unsloth/DeepSeek-R1-Distill-Qwen-7B-GGUF \
  DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf \
  --local-dir . --local-dir-use-symlinks False
```

---

## Security

### Sandbox Security Model

**Isolation Mechanisms:**
1. **Docker Container** - Namespace isolation
2. **Read-Only Filesystem** - No persistent changes
3. **No New Privileges** - Cannot escalate permissions
4. **Restricted Builtins** - No dangerous Python functions
5. **Tmpfs /tmp** - Memory-only temporary storage (noexec, nosuid)
6. **Resource Limits** - CPU and memory caps

**Docker Configuration:**
```yaml
sandbox:
  security_opt:
    - no-new-privileges:true
  read_only: true
  tmpfs:
    - /tmp:size=512m,noexec,nosuid
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
```

**Code Execution Safeguards:**
```python
# Restricted built-in functions
SAFE_BUILTINS = {
    'print', 'len', 'range', 'enumerate', 'zip',
    'sum', 'min', 'max', 'abs', 'round', 'sorted',
    'list', 'dict', 'set', 'tuple', 'str', 'int',
    'float', 'bool', 'type', 'isinstance'
}

# Forbidden (not available)
BLOCKED = {
    'open', 'file', 'input', 'compile', 'eval', 'exec',
    '__import__', 'globals', 'locals', 'vars', 'dir',
    'getattr', 'setattr', 'delattr', 'hasattr'
}

# Execution with timeout
try:
    exec(code, namespace, namespace)
except TimeoutError:
    return {"output": "", "error": "Execution timeout"}
except Exception as e:
    return {"output": "", "error": str(e)}
```

### Redis Security

**Authentication:**
```yaml
# Production only
environment:
  - REDIS_PASSWORD=${REDIS_PASSWORD}

command:
  - redis-server
  - --requirepass ${REDIS_PASSWORD}
```

**Network Binding:**
```yaml
# Production: localhost only
ports:
  - "127.0.0.1:6379:6379"

# Development: all interfaces
ports:
  - "6379:6379"
```

### HTTPS/SSL (Production)

**Reverse Proxy with nginx:**
```nginx
server {
    listen 443 ssl http2;
    server_name archive-ai.local;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Firewall Configuration

**Production hardening:**
```bash
# Allow only necessary ports
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP (redirect to HTTPS)
sudo ufw allow 443/tcp     # HTTPS

# Block direct access to services
sudo ufw deny 6379         # Redis
sudo ufw deny 8000         # Vorpal
sudo ufw deny 8001         # Voice
sudo ufw deny 8002         # RedisInsight
sudo ufw deny 8003         # Sandbox
sudo ufw deny 8080         # Brain (only via nginx proxy)
sudo ufw deny 8081         # Goblin

sudo ufw enable
```

---

## Performance Tuning

### Vorpal Optimization

**GPU Memory Utilization:**
```yaml
# Conservative (allows more desktop usage)
GPU_MEMORY_UTILIZATION=0.35  # ~5.7 GB

# Balanced (recommended for dual-engine)
GPU_MEMORY_UTILIZATION=0.45  # ~7.4 GB

# Aggressive (single-engine max performance)
GPU_MEMORY_UTILIZATION=0.75  # ~12.2 GB
```

**Context Window vs VRAM:**
```yaml
# Small context (saves VRAM)
MAX_MODEL_LEN=2048     # ~4 GB VRAM

# Medium context (balanced)
MAX_MODEL_LEN=4096     # ~6 GB VRAM

# Large context (more VRAM)
MAX_MODEL_LEN=8192     # ~9 GB VRAM
```

**Batch Size:**
```yaml
# Low latency (fewer concurrent requests)
MAX_NUM_SEQS=16        # 1-2 concurrent users

# Balanced (recommended)
MAX_NUM_SEQS=64        # 5-10 concurrent users

# High throughput (more batching)
MAX_NUM_SEQS=256       # 20+ concurrent users (requires more VRAM)
```

### Goblin Optimization

**GPU Layers:**
```yaml
# CPU fallback (slowest, no VRAM)
N_GPU_LAYERS=0

# Partial GPU (balanced)
N_GPU_LAYERS=20        # ~4-5 GB VRAM

# All GPU (fastest, most VRAM)
N_GPU_LAYERS=40        # ~9-10 GB VRAM (14B model)
```

**Thread Count:**
```yaml
# Low CPU usage
GOBLIN_THREADS=4

# Balanced
GOBLIN_THREADS=8

# High CPU usage (faster CPU inference)
GOBLIN_THREADS=16
```

### Redis Optimization

**Memory Policy:**
```yaml
# LRU eviction (recommended)
--maxmemory-policy allkeys-lru

# No eviction (risky, may cause OOM)
--maxmemory-policy noeviction

# Volatile LRU (only keys with TTL)
--maxmemory-policy volatile-lru
```

**Persistence:**
```yaml
# AOF + RDB (maximum durability, slower writes)
--appendonly yes
--save 900 1 300 10 60 10000

# AOF only (good balance)
--appendonly yes
--save ""

# RDB only (faster, less durable)
--appendonly no
--save 900 1 300 10 60 10000

# No persistence (fastest, volatile)
--appendonly no
--save ""
```

### Voice Service Optimization

**Whisper Model Size:**
```yaml
# Fastest (lowest accuracy)
WHISPER_MODEL=tiny     # ~1 GB RAM, ~2-3s transcription

# Balanced (recommended)
WHISPER_MODEL=base     # ~1.5 GB RAM, ~3-5s transcription

# Accurate (slower)
WHISPER_MODEL=medium   # ~3 GB RAM, ~8-12s transcription
```

**Compute Type:**
```yaml
# Fastest (CPU)
WHISPER_COMPUTE_TYPE=int8

# Higher quality
WHISPER_COMPUTE_TYPE=float16  # Requires GPU

# Maximum quality
WHISPER_COMPUTE_TYPE=float32  # Requires GPU
```

---

## Monitoring

### Health Checks

**Quick check:**
```bash
curl http://localhost:8080/health
```

**Response:**
```json
{
  "status": "healthy",
  "vorpal_url": "http://vorpal:8000",
  "vorpal_model": "Qwen/Qwen2.5-7B-Instruct-AWQ",
  "async_memory": {
    "enabled": true,
    "start_from_latest": true,
    "last_id": "1234567890-0",
    "stream_length": 42
  }
}
```

**System metrics:**
```bash
curl http://localhost:8080/metrics
```

**Response:**
```json
{
  "uptime_seconds": 3600.5,
  "system": {
    "cpu_percent": 7.1,
    "memory_percent": 49.2,
    "memory_used_mb": 2048.5,
    "memory_total_mb": 4096.0
  },
  "memory_stats": {
    "total_memories": 107,
    "storage_threshold": 0.7,
    "embedding_dim": 384,
    "index_type": "HNSW"
  },
  "services": [
    {"name": "Brain", "status": "healthy", "url": "internal"},
    {"name": "Vorpal", "status": "healthy", "url": "http://vorpal:8000"},
    {"name": "Redis", "status": "healthy", "url": "redis://redis:6379"},
    {"name": "Sandbox", "status": "healthy", "url": "http://sandbox:8000"}
  ],
  "version": "0.4.0"
}
```

### Log Monitoring

**View service logs:**
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f brain
docker compose logs -f vorpal

# Follow with timestamp
docker compose logs -f --timestamps brain

# Last N lines
docker compose logs --tail 100 brain
```

**Log patterns to watch:**

**Normal operation:**
```
[MemoryWorker] Perplexity: 15.43
[MemoryWorker] Surprise Score: 0.628
[MemoryWorker] ❌ SKIPPED (below threshold 0.7)

[MemoryWorker] Perplexity: 42.80
[MemoryWorker] Surprise Score: 0.851
[MemoryWorker] ✅ STORED memory:1735477200
```

**Errors to investigate:**
```
[MemoryWorker] Failed to calculate perplexity
[MemoryWorker] All connection attempts failed
ERROR: Connection to Vorpal timed out
ERROR: Redis connection refused
```

### Resource Monitoring

**GPU monitoring:**
```bash
# Real-time GPU stats
nvidia-smi -l 1

# Query specific metrics
nvidia-smi --query-gpu=timestamp,name,utilization.gpu,utilization.memory,memory.used,memory.total --format=csv -l 1
```

**Container resource usage:**
```bash
docker stats

# Specific service
docker stats archive-ai-brain-1 archive-ai-vorpal-1
```

**Redis monitoring:**
```bash
# Memory usage
docker exec archive-ai-redis-1 redis-cli INFO memory

# Key counts
docker exec archive-ai-redis-1 redis-cli DBSIZE

# Stream length
docker exec archive-ai-redis-1 redis-cli XLEN session:input_stream
```

### Prometheus Integration (Optional)

**Goblin metrics endpoint:**
```
http://localhost:8081/metrics
```

**Sample metrics:**
```
# HELP llama_prompt_tokens_total Number of prompt tokens processed
# TYPE llama_prompt_tokens_total counter
llama_prompt_tokens_total 123456

# HELP llama_generation_tokens_total Number of tokens generated
# TYPE llama_generation_tokens_total counter
llama_generation_tokens_total 78910

# HELP llama_request_duration_seconds Request duration
# TYPE llama_request_duration_seconds histogram
llama_request_duration_seconds_bucket{le="1"} 42
```

---

## Backup and Recovery

### What to Backup

**Critical data:**
1. **Redis RDB/AOF files** - `./data/redis/`
2. **Cold storage archives** - `./data/archive/`
3. **Library chunks** - `./data/library/` (optional, can reprocess)
4. **Configuration** - `.env`, `config/user-config.env`

**Not necessary to backup:**
- Docker images (rebuildable)
- Model files (re-downloadable)
- Logs (ephemeral)
- Web UI static files (in git)

### Backup Script

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=~/backups/archive-ai

mkdir -p $BACKUP_DIR

# Save Redis (force RDB snapshot)
docker exec archive-ai-redis-1 redis-cli SAVE
sleep 5

# Copy Redis data
cp -r data/redis $BACKUP_DIR/redis-$DATE

# Archive cold storage
tar -czf $BACKUP_DIR/archive-$DATE.tar.gz data/archive

# Archive library (optional)
tar -czf $BACKUP_DIR/library-$DATE.tar.gz data/library

# Copy configuration
cp .env $BACKUP_DIR/env-$DATE
cp config/user-config.env $BACKUP_DIR/user-config-$DATE 2>/dev/null

# Verify backup
du -sh $BACKUP_DIR/*-$DATE*

echo "Backup complete: $BACKUP_DIR"
```

### Restore Procedure

```bash
#!/bin/bash
# Restore from backup

BACKUP_DATE=20250129_143000  # Adjust to your backup timestamp
BACKUP_DIR=~/backups/archive-ai

# Stop services
docker compose down

# Restore Redis data
rm -rf data/redis/*
cp -r $BACKUP_DIR/redis-$BACKUP_DATE/* data/redis/

# Restore archives
tar -xzf $BACKUP_DIR/archive-$BACKUP_DATE.tar.gz

# Restore library (optional)
tar -xzf $BACKUP_DIR/library-$BACKUP_DATE.tar.gz

# Restore configuration
cp $BACKUP_DIR/env-$BACKUP_DATE .env
cp $BACKUP_DIR/user-config-$BACKUP_DATE config/user-config.env 2>/dev/null

# Restart services
docker compose up -d

echo "Restore complete"
```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue: "Vorpal not responding" / "Connection timeout"

**Symptoms:**
- Memory worker logs "Failed to calculate perplexity"
- `/chat` endpoint returns 503 errors
- Health check shows Vorpal unhealthy

**Diagnosis:**
```bash
# Check if Vorpal is running
docker compose ps vorpal

# Check Vorpal logs
docker compose logs vorpal | tail -50

# Test Vorpal directly
curl http://localhost:8000/health
```

**Solutions:**
1. **Model still loading** - Wait 2-3 minutes for CUDA graph compilation
2. **Out of VRAM** - Reduce `GPU_MEMORY_UTILIZATION` or stop Goblin
3. **Model download failed** - Check internet, HuggingFace token, disk space
4. **Port conflict** - Verify no other process on port 8000

**Fix:**
```bash
# Restart Vorpal
docker compose restart vorpal

# Or rebuild if needed
docker compose up -d --build vorpal
```

---

#### Issue: "Memory not being stored"

**Symptoms:**
- All messages show "❌ SKIPPED" in logs
- `/memories` endpoint returns empty list
- Surprise scores always < 0.7

**Diagnosis:**
```bash
# Check memory worker logs
docker compose logs brain | grep MemoryWorker

# Check surprise scores
docker compose logs brain | grep "Surprise Score"
```

**Common causes:**
1. **All inputs too predictable** - Normal for greetings, common questions
2. **Perplexity calculation failing** - Vorpal connection issue
3. **Threshold too high** - Default 0.7 filters ~70% of inputs

**Solutions:**
1. **Try novel questions** - "Explain quantum entanglement in simple terms"
2. **Lower threshold** - Edit `brain/workers/memory_worker.py`, set `STORAGE_THRESHOLD = 0.5`
3. **Fix Vorpal connection** - See previous issue

---

#### Issue: "High VRAM usage" / "CUDA out of memory"

**Symptoms:**
- `nvidia-smi` shows 15-16 GB usage
- Services crash with CUDA OOM errors
- Slow inference or timeouts

**Diagnosis:**
```bash
# Check VRAM usage
nvidia-smi

# Check per-service
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
```

**Solutions:**

**Option 1: Reduce Vorpal VRAM**
```yaml
# Edit docker-compose.awq-7b.yml or config/user-config.env
VORPAL_GPU_MEMORY_UTILIZATION=0.35  # Down from 0.45
VORPAL_MAX_MODEL_LEN=2048          # Down from 4096
```

**Option 2: Stop Goblin**
```bash
docker compose stop goblin
```

**Option 3: Reduce Goblin GPU layers**
```yaml
# Edit config/user-config.env
GOBLIN_N_GPU_LAYERS=10  # Down from 20
```

**Option 4: Switch to 3B model**
```yaml
# Edit config/user-config.env
VORPAL_MODEL=Qwen/Qwen2.5-3B-Instruct
VORPAL_GPU_MEMORY_UTILIZATION=0.22
```

**Restart:**
```bash
docker compose down
docker compose up -d
```

---

#### Issue: "Library files not being processed"

**Symptoms:**
- Files added to `~/ArchiveAI/Library-Drop/` but not indexed
- `/library/stats` shows 0 chunks
- `/library/search` returns empty results

**Diagnosis:**
```bash
# Check librarian logs
docker compose logs librarian

# Check watch folder
ls -lh ~/ArchiveAI/Library-Drop/

# Test library storage manually
docker exec archive-ai-librarian-1 python -c "from storage import LibraryStorage; s=LibraryStorage(); print(s.get_stats())"
```

**Common causes:**
1. **Librarian service not running** - Check `docker compose ps`
2. **Watch folder incorrect** - Verify mount in compose file
3. **File permissions** - Librarian can't read files
4. **Unsupported format** - Only .pdf, .txt, .md supported

**Solutions:**
```bash
# Restart librarian
docker compose restart librarian

# Check folder mount
docker exec archive-ai-librarian-1 ls -la /watch/

# Fix permissions
chmod -R 755 ~/ArchiveAI/Library-Drop/
chown -R $USER:$USER ~/ArchiveAI/Library-Drop/

# Test with sample file
echo "Test document" > ~/ArchiveAI/Library-Drop/test.txt
```

---

#### Issue: "Agent gets stuck / infinite loop"

**Symptoms:**
- Agent reaches max_steps (10) without answer
- Same action repeated multiple times
- Response takes > 30 seconds

**Diagnosis:**
- Review agent reasoning trace in response
- Look for repeated actions or circular logic

**Common patterns:**
```
Step 1: Thought: I need to calculate...
        Action: Calculator
        Observation: Result: 42

Step 2: Thought: I need to calculate...
        Action: Calculator
        Observation: Result: 42

Step 3: Thought: I need to calculate...
        Action: Calculator
        Observation: Result: 42
```

**Solutions:**
1. **Rephrase question** - More specific instructions
2. **Reduce complexity** - Break into multiple simpler questions
3. **Use different mode** - Basic agent for simple math, Advanced for complex
4. **Increase max_steps** - Some tasks legitimately need > 10 steps

**Example fix:**
```bash
# Instead of:
curl -X POST http://localhost:8080/agent \
  -d '{"question": "Solve this complex problem..."}'

# Try:
curl -X POST http://localhost:8080/agent \
  -d '{"question": "What is step 1 to solve...?"}'
```

---

#### Issue: "Code execution fails" / "Sandbox timeout"

**Symptoms:**
- CodeExecution tool returns errors
- "Execution timeout" in agent trace
- Infinite loops in generated code

**Diagnosis:**
```bash
# Check sandbox logs
docker compose logs sandbox

# Test sandbox directly
curl -X POST http://localhost:8003/execute \
  -H "Content-Type: application/json" \
  -d '{"code": "print(2+2)", "timeout": 10}'
```

**Common issues:**
1. **No print() statement** - Code defines function but never calls it
2. **Infinite loop** - Recursion without base case
3. **Timeout too short** - Complex calculation needs > 10s

**Solutions:**
```python
# Bad: No output
def factorial(n):
    if n <= 1: return 1
    return n * factorial(n-1)

# Good: Includes print
def factorial(n):
    if n <= 1: return 1
    return n * factorial(n-1)
print(factorial(10))

# Increase timeout if needed
curl -X POST http://localhost:8080/code_assist \
  -d '{"task": "...", "timeout": 30}'
```

---

### Advanced Debugging

**Enable debug logging:**
```yaml
# Edit .env
LOG_LEVEL=DEBUG

# Restart
docker compose restart brain
```

**Redis command monitoring:**
```bash
docker exec archive-ai-redis-1 redis-cli MONITOR
```

**Network packet capture:**
```bash
# Inside brain container
docker exec -it archive-ai-brain-1 bash
apt-get update && apt-get install -y tcpdump
tcpdump -i any -n port 8000  # Monitor Vorpal traffic
```

**Python debugger (development):**
```python
# Add to brain/main.py
import pdb; pdb.set_trace()

# Attach to container
docker attach archive-ai-brain-1
```

---

## Development

### Development Setup

**Clone repository:**
```bash
git clone https://github.com/Atari-Katana/Archive-AI.git
cd Archive-AI
```

**Install Python dependencies (for IDE):**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r brain/requirements.txt
pip install -r sandbox/requirements.txt
pip install -r librarian/requirements.txt
pip install -r voice/requirements.txt
```

**Development workflow:**
```bash
# Edit code in ./brain/, ./sandbox/, etc.

# Rebuild specific service
docker compose build brain

# Restart to test changes
docker compose up -d brain

# View logs
docker compose logs -f brain
```

### Code Quality

**Linting:**
```bash
# Install flake8
pip install flake8

# Lint all Python files
flake8 brain/ sandbox/ librarian/ voice/

# Auto-format (optional)
pip install black
black brain/ sandbox/ librarian/ voice/
```

**Type checking (optional):**
```bash
pip install mypy
mypy brain/main.py
```

### Testing

**Manual API testing:**
```bash
# Use provided test scripts
python scripts/test-redis.py
python scripts/test-vector-store.py
python scripts/test-surprise-scoring.py
python scripts/test-router.py
python scripts/test-verification.py
python scripts/test-research-agent.py
python scripts/test-code-assistant.py
```

**Automated testing (recommended for production):**
```bash
# Install pytest
pip install pytest pytest-asyncio httpx

# Write tests
cat > tests/test_brain.py <<EOF
import pytest
import httpx

@pytest.mark.asyncio
async def test_health():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8080/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
EOF

# Run tests
pytest tests/
```

### Contributing

**Branch naming:**
```bash
git checkout -b feature/agent-improvements
git checkout -b fix/memory-worker-timeout
git checkout -b docs/update-readme
```

**Commit messages:**
```bash
git commit -m "Add: New research agent with multi-query support"
git commit -m "Fix: Memory worker timeout handling"
git commit -m "Docs: Update Owner's Manual with VRAM tuning"
```

**Pull request process:**
1. Fork repository
2. Create feature branch
3. Make changes with tests
4. Update documentation
5. Submit PR with description

---

## Appendix: File Locations

### Configuration Files

| File | Purpose |
|------|---------|
| `.env` | Production secrets (gitignored) |
| `.env.example` | Environment template |
| `config/user-config.env` | Model tuning (gitignored) |
| `config/user-config.example.env` | User config template |
| `docker-compose.yml` | Main orchestration (3B profile) |
| `docker-compose.awq-7b.yml` | 7B AWQ overlay |
| `docker-compose.prod.yml` | Production deployment |

### Service Directories

| Directory | Purpose |
|-----------|---------|
| `brain/` | FastAPI orchestrator |
| `vorpal/` | vLLM inference engine |
| `sandbox/` | Code execution service |
| `voice/` | STT/TTS service |
| `librarian/` | Document ingestion |
| `ui/` | Web interface |

### Data Directories

| Directory | Purpose |
|-----------|---------|
| `data/redis/` | Redis persistence (RDB + AOF) |
| `data/archive/` | Cold storage (JSON files) |
| `data/library/` | Processed library chunks (debugging) |
| `models/vorpal/` | Vorpal model cache |
| `models/goblin/` | Goblin GGUF models |
| `models/whisper/` | Whisper model cache |
| `models/f5-tts/` | F5-TTS model cache |

### Log Locations

| Service | Log Location |
|---------|--------------|
| Brain | `docker logs archive-ai-brain-1` |
| Vorpal | `docker logs archive-ai-vorpal-1` |
| Goblin | `docker logs archive-ai-goblin-1` |
| Redis | `docker logs archive-ai-redis-1` |
| Sandbox | `docker logs archive-ai-sandbox-1` |
| Voice | `docker logs archive-ai-voice-1` |
| Librarian | `docker logs archive-ai-librarian-1` |

---

**End of Owner's Manual**

For user-facing features, see the **User's Manual**.
For building custom agents, see the **Agent Manual**.
For installation and operations, see the **Go Manual**.
For use case ideas, see the **Use Case Manual**.
