# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Archive-AI is a production-ready local AI cognitive framework featuring permanent memory, dual inference engines, voice I/O, and agentic workflows. It's optimized for single-GPU (16GB VRAM) deployment with enterprise-grade monitoring and testing infrastructure.

## Common Commands

### Starting and Stopping

```bash
# Start system (interactive menu)
./start

# Start with specific interface
./start --web    # Web UI on port 8888
./start --gui    # Flutter desktop app
./start --api    # Headless (API only)

# Stop: Press Ctrl+C in the terminal running ./start
```

### Health Checks and Monitoring

```bash
# Full health check
bash scripts/health-check.sh

# Quick health check
bash scripts/health-check.sh --quick

# Continuous monitoring
bash scripts/health-check.sh --watch
```

### Testing

```bash
# Stress testing (5-minute concurrent load test)
bash scripts/run-stress-test.sh

# Edge case testing (failure scenarios)
bash scripts/run-edge-case-tests.sh

# Individual service tests
python3 scripts/test-verification.py
python3 scripts/test-research-agent.py
python3 scripts/test-code-assistant.py
python3 scripts/test-code-validator.py
python3 scripts/test-surprise-scoring.py
```

### Development

```bash
# Download models
python3 scripts/download-models.py --model goblin-7b

# Tune surprise score weights
python3 scripts/tune-surprise-weights.py

# View logs
docker-compose logs brain
docker-compose logs -f vorpal  # Follow mode
```

## Architecture

### Service Topology

Archive-AI uses a microservices architecture with 7 core services orchestrated via Docker Compose:

1. **Brain (Python/FastAPI)** - Central orchestrator and API gateway
   - Port: 8080 (external), 8000 (internal)
   - Handles routing, memory, agents, and coordination
   - Entry point: `brain/main.py`

2. **Vorpal (llama.cpp)** - Primary engine for fast inference
   - Port: 8002 (external), 8000 (internal)
   - Default: Llama-3.2-3B-Instruct-Q4_K_M (CPU mode in base config)
   - AWQ mode: Llama-3.1-8B-Instruct-AWQ (~5.9GB VRAM)

3. **Goblin (llama.cpp)** - Fallback engine for reasoning and coding
   - Port: 8003 (external), 8080 (internal)
   - Default: DeepSeek-R1-Distill-Qwen-7B-Q4_K_M
   - Handles complex reasoning and code generation

4. **Redis Stack** - State management and vector database
   - Port: 6379 (Redis), 8006 (RedisInsight UI)
   - Stores memories, vectors, and session state
   - Configured with RediSearch for vector similarity

5. **Sandbox (Python)** - Isolated code execution environment
   - Port: 8004 (external), 8000 (internal)
   - AST-based validation before execution
   - Read-only filesystem with resource limits

6. **Voice (Python)** - Speech I/O service
   - Port: 8005 (external), 8000 (internal)
   - STT: Faster-Whisper
   - TTS: F5-TTS/XTTS

7. **Bifrost** - Semantic router for intent classification
   - Port: 8081 (external), 8080 (internal)
   - Routes requests to appropriate engines

### Key Subsystems

**Memory System** (`brain/memory/`)
- **Vector Store** (`vector_store.py`): Redis-backed semantic memory using sentence-transformers (all-MiniLM-L6-v2)
- **Cold Storage** (`cold_storage.py`): Automatic archival of old memories to disk
- **Surprise Scoring**: Titans-inspired memory retention based on perplexity and semantic novelty
- **Memory Worker** (`brain/workers/memory_worker.py`): Async background worker for memory processing

**Agent System** (`brain/agents/`)
- **ReAct Agent** (`react_agent.py`): Base ReAct loop implementation with tool use
- **Recursive Agent** (`recursive_agent.py`): RLM (Recursive Language Model) for infinite-context tasks
- **Research Agent** (`research_agent.py`): Library search + memory integration
- **Code Agent** (`code_agent.py`): Code generation with auto-testing
- **Tool Registry**: Modular tool system with basic and advanced tool sets
- **Code Validator** (`code_validator.py`): AST-based Python code validation (<5% failure rate)

**LLM Service** (`brain/services/llm.py`)
- Unified client for Vorpal/Goblin
- Automatic connection management with timeouts
- Supports both completion and chat endpoints

**Metrics System** (`brain/services/metrics_service.py`)
- Background collection every 30 seconds
- Tracks CPU, memory, request rates, service health
- Historical data storage and CSV export

### Data Flow

```
User Request
    ↓
Brain API (:8080)
    ↓
Bifrost Gateway (:8081) [semantic routing]
    ↓
Vorpal (primary) or Goblin (fallback) [LLM inference]
    ↓
Surprise Scoring [memory retention]
    ↓
Redis Vector Store [semantic storage]
    ↓
Memory Worker [async processing]
    ↓
Response + Metrics Collection
```

For agents:
```
Agent Request
    ↓
ReAct Loop [thought → action → observation]
    ↓
Tool Execution (CodeExecution, Search, Memory, etc.)
    ↓
Sandbox/Library/Memory Services
    ↓
LLM Reflection
    ↓
Final Answer
```

## Important Patterns

### Configuration

All configuration is centralized in `brain/config.py` as a singleton `Config` class. Service URLs use Docker internal networking (e.g., `http://vorpal:8000`). Environment variables override defaults.

Key env vars:
- `REDIS_URL`: Redis connection string
- `VORPAL_URL`, `GOBLIN_URL`: LLM service URLs
- `SANDBOX_URL`, `VOICE_URL`, `BIFROST_URL`: Support service URLs
- `ASYNC_MEMORY`: Enable async memory worker (default: true)
- `ARCHIVE_ENABLED`: Enable cold storage archival (default: true)
- `METRICS_ENABLED`: Enable metrics collection (default: true)

### Error Handling

Professional error messages use `brain/error_handlers.py` with ASCII box formatting. All errors include:
- Clear description of the problem
- Probable cause
- Recovery steps
- Relevant context (service URLs, timeouts)

### Async Patterns

- Brain uses FastAPI with async/await throughout
- Background workers use `asyncio.create_task()` for non-blocking execution
- Memory worker processes Redis stream asynchronously
- LLM client uses `httpx.AsyncClient` with connection pooling

### Agent Tool Development

Tools are defined in `brain/agents/basic_tools.py` and `brain/agents/advanced_tools.py`. Each tool:
1. Has a descriptive docstring (used as tool description)
2. Takes string parameters
3. Returns string results
4. Handles errors gracefully

Tools are registered in `ToolRegistry` and passed to agents.

### Memory Storage

Memories are stored as Redis hashes with the prefix `memory:`. Each memory includes:
- `message`: Original text
- `embedding`: 384-dim vector from sentence-transformers
- `surprise_score`: Float (0-1) based on perplexity and semantic novelty
- `timestamp`: Unix timestamp
- `session_id`: Session identifier
- `metadata`: JSON metadata

Vector search uses RediSearch with HNSW indexing and cosine similarity.

### Code Execution

Code execution via Sandbox:
1. Validate code with AST parser (blocks dangerous imports: os, subprocess, sys, socket)
2. POST to `/execute` with code and optional context dict
3. Sandbox returns `{status, result, error}`
4. Timeout: 10 seconds (configurable via `SANDBOX_TIMEOUT`)

## Development Notes

### Docker Compose Handling

The `./start` script automatically detects Docker Compose version:
- Prefers `docker compose` (plugin v2)
- Falls back to `docker-compose` (standalone v1)
- Stored in `DOCKER_COMPOSE_CMD` variable

### Model Downloads

Models are auto-downloaded by `scripts/download-models.py`:
- Checks for existing models before download
- Shows progress bars
- Supports resume capability
- Verifies SHA256 checksums (when available)

### Submodules

- `octotools_repo`: Advanced tool library (submodule)
- `archive-ai-rs`: Experimental Rust rewrite (submodule)

Initialize with: `git submodule update --init --recursive`

### Testing Philosophy

1. **Integration tests**: Focus on real service interactions
2. **Stress tests**: 5-minute concurrent load with p50/p95/p99 metrics
3. **Edge cases**: Test graceful degradation (Redis loss, LLM unavailable, invalid code)
4. **Target**: >95% success rate on all tests

### Persona System

Personas defined in `data/personas.json` with:
- `name`, `description`, `system_prompt`
- Optional `avatar` image in `ui/assets/personas/`
- Managed via `/personas` API endpoints

### UI Architecture

- **Web UI**: Static HTML/CSS/JS served from `ui/` directory
- **Mounted at**: `/ui` on Brain service
- **Main pages**:
  - `index.html`: Chat interface
  - `metrics-panel.html`: Real-time metrics dashboard
  - `config-panel.html`: Configuration editor
- **API calls**: Direct to Brain at `http://localhost:8080`

## Access Points

- **Main UI**: http://localhost:8888 or http://localhost:8080/ui/
- **Metrics Dashboard**: http://localhost:8080/ui/metrics-panel.html
- **Config Editor**: http://localhost:8080/ui/config-panel.html
- **API Docs**: http://localhost:8080/docs
- **Health Check**: http://localhost:8080/health
- **RedisInsight**: http://localhost:8006

## Critical Files

- `brain/main.py`: FastAPI application entry point
- `brain/config.py`: Central configuration
- `brain/services/llm.py`: LLM client abstraction
- `brain/memory/vector_store.py`: Memory storage and search
- `brain/agents/react_agent.py`: Base agent implementation
- `docker-compose.yml`: Service orchestration
- `./start`: Master startup script
- `.env`: Environment variables (create from `.env.example`)
