# Archive-AI Configuration Guide

Archive-AI supports **two deployment modes** with **two configuration layers**:

## Deployment Modes

### Mode 1: Dual-Engine (AWQ 7B) - Recommended for 16GB GPU
**Command:** `bash go.sh`

- **Vorpal:** Qwen 2.5-7B-Instruct-AWQ (~6GB VRAM)
- **Goblin:** DeepSeek-R1-Distill-Qwen-7B Q4_K_M (~5-6GB VRAM)
- **Total VRAM:** ~14GB (fits on 16GB GPU with ~2GB headroom)
- **Use Case:** Full dual-engine capability (speed + reasoning)
- **Startup:** Automatically launches services + Web UI on port 8888

### Mode 2: Single-Engine (Base 3B) - Fallback for VRAM constraints
**Command:** `docker-compose up -d`

- **Vorpal:** Qwen 2.5-3B-Instruct (~12GB VRAM with full allocation)
- **Goblin:** Disabled (CPU-only in base config, typically unused)
- **Total VRAM:** ~12GB
- **Use Case:** Lower VRAM usage, chat + memory only
- **Startup:** Manual service launch, no auto UI server

**Recommendation:** Use `bash go.sh` (Mode 1) if you have 16GB+ VRAM. It provides the best experience with both speed and reasoning engines active.

---

## Configuration Layers

### Layer 1: Core Settings (.env) - Required
Contains secrets and critical configuration:
- `REDIS_PASSWORD` - Database authentication
- `BRAIN_PORT` - API endpoint port (default: 8080)
- `ARCHIVE_DAYS` - Memory archival threshold
- See `.env.example` for all available options

**Setup:**
```bash
cp .env.example .env
nano .env  # Edit secrets and core settings
```

### Layer 2: Model Tuning (config/user-config.env) - Optional
Fine-tune model parameters without editing docker-compose files:
- Vorpal model selection, VRAM allocation, context length
- Goblin model path, GPU layers, CPU threads
- Memory worker settings

**Setup:**
```bash
cp config/user-config.example.env config/user-config.env
nano config/user-config.env  # Edit tuning parameters
```

## Variables (user-config.env)
- `VORPAL_MODEL`: HF repo/tag served by Vorpal (default: `Qwen/Qwen2.5-7B-Instruct-AWQ` in AWQ mode, `Qwen/Qwen2.5-3B-Instruct` in base).
- `VORPAL_GPU_MEMORY_UTILIZATION`: Fraction of GPU VRAM vLLM may use (0.0–1.0).
- `VORPAL_MAX_MODEL_LEN`: Max context length (tokens) for Vorpal.
- `VORPAL_MAX_NUM_SEQS`: Max concurrent sequences vLLM batches; lower to reduce VRAM spikes.
- `GOBLIN_MODEL_PATH`: Path to GGUF model for Goblin (container path; mounted from `./models/goblin`).
- `GOBLIN_N_GPU_LAYERS`: Layers to keep on GPU (lower to save VRAM, higher for speed/quality).
- `GOBLIN_CTX_SIZE`: Context size for Goblin (tokens). Higher uses more RAM/VRAM.
- `GOBLIN_THREADS`: CPU threads for Goblin.
- `GOBLIN_BATCH_SIZE` / `GOBLIN_UBATCH_SIZE`: llama.cpp batch settings; lower if OOM or latency spikes.
- `ASYNC_MEMORY`: `true/false` to enable background memory worker.
- `MEMORY_START_FROM_LATEST`: `true/false` start reading Redis stream from latest (`$`) when no saved ID.
- `MEMORY_LAST_ID_KEY`: Redis key to persist last processed stream ID.
- `MAX_TOKENS`: Maximum number of tokens for LLM responses (default: 1024).

---

## How ./start Works

The `./start` script is the **master launcher** for Archive-AI:

1. **Checks Dependencies:** Ensures Docker, Python, etc., are installed.
2. **Checks Models:** Auto-downloads Goblin model if missing.
3. **Applies Overlays:** Merges `docker-compose.yml` + `docker-compose.awq-7b.yml`.
4. **Starts Services:** Launches Redis, Vorpal, Goblin, Brain, Voice, Librarian.
5. **Launches Interface:** Starts Web UI (8888) or Flutter GUI based on selection.
6. **Handles Cleanup:** Gracefully stops all services on exit (Ctrl+C).

**Usage:**
```bash
./start              # Interactive menu
./start --web        # Web UI
./start --gui        # Flutter GUI
./start --api        # Headless
```

---

## How Configuration Overrides are Applied

**Priority Order (highest to lowest):**
1. Environment variables in your shell
2. `config/user-config.env` (if present)
3. `.env` file (required)
4. `docker-compose.awq-7b.yml` overlay (always used by ./start)
5. `docker-compose.yml` base configuration

**Flow:**
- `./start` calls `docker-compose` with both files.
- Services start with final merged configuration.

---

## When to Use Each Mode

### Standard Mode (Dual-Engine) - `./start`
**Best for:**
- 16GB+ VRAM GPUs (RTX 5060 Ti, 4060 Ti 16GB, 3090, 4090)
- Full Archive-AI experience (speed + reasoning)
- Agentic workflows requiring complex reasoning
- Code generation and debugging
- Research tasks with citation tracking

**Requirements:**
- Qwen 2.5-7B-Instruct-AWQ model downloaded (auto-downloads on first start)
- DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf in `models/goblin/`
- ~14GB VRAM available (close desktop apps if needed)

### Use Single-Engine (Base 3B) - `docker-compose up -d`
**Best for:**
- 12-16GB VRAM GPUs with desktop environment using VRAM
- Chat and memory system only (no advanced reasoning)
- Development and testing
- Lower power consumption

**Requirements:**
- Qwen 2.5-3B-Instruct model (auto-downloads on first start)
- ~12GB VRAM available

---

## Switching Between Modes

**From Dual-Engine to Single-Engine (Manual):**
```bash
# Stop current session (Ctrl+C)
docker-compose down
docker-compose up -d redis vorpal brain  # Start minimal services manually
```

**From Single-Engine to Dual-Engine (Standard):**
```bash
docker-compose down
./start  # Launches with AWQ overlay and UI
```

---

## Advanced Tuning

### Increase Vorpal Context (at cost of VRAM)
```bash
# Edit config/user-config.env
VORPAL_MAX_MODEL_LEN=8192  # Default: 4096 in AWQ mode
VORPAL_GPU_MEMORY_UTILIZATION=0.55  # Default: 0.45 in AWQ mode
# Note: May cause OOM if Goblin is also running
```

### Reduce Goblin VRAM (more CPU, slower)
```bash
# Edit config/user-config.env
GOBLIN_N_GPU_LAYERS=15  # Default: 20 in AWQ mode
# Lower = more CPU offloading, less VRAM usage
```

### Stop Goblin to Free VRAM
```bash
docker-compose stop goblin
# Vorpal now has ~5-6GB more VRAM available
# Increase VORPAL_GPU_MEMORY_UTILIZATION to use freed VRAM
```

---

## Notes
- **Security:** Keep secrets (passwords, tokens) in `.env`, never in `config/user-config.env`
- **Model Paths:** Model files must exist at configured paths (`models/vorpal/`, `models/goblin/`)
- **VRAM Budget:** AWQ+7B profile uses ~14GB. Monitor with `nvidia-smi` to avoid OOM
- **Desktop VRAM:** X11/Wayland compositors can use 2-3GB. Factor this into budget
- **Production:** Use `docker-compose.prod.yml` for hardened deployment with resource limits
