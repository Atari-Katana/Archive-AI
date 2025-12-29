# Archive-AI Configuration Guide

Two layers of config are used:
1) **.env** (required) for secrets like Redis passwords.
2) **config/user-config.env** (optional) for tuning models, memory, and runtime defaults.

## Quick start
1) Copy the example: `cp config/user-config.example.env config/user-config.env`
2) Edit the values you need.
3) Run `bash go.sh` (it automatically loads these overrides).

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

## How overrides are applied
- `go.sh` runs `scripts/start.sh` with the AWQ overlay (`docker-compose.awq-7b.yml`).
- `scripts/start.sh` exports values from `config/user-config.env` if present.
- `docker-compose.yml` and `docker-compose.awq-7b.yml` read these env vars to set model names and runtime knobs.

## Notes
- Keep secrets (passwords, tokens) in `.env`, not in `config/user-config.env`.
- Model files must exist at the paths you set (e.g., `models/goblin/...` on host maps to `/models/...` in the container).
- For 16GB GPUs running dual engines, prefer the AWQ+7B profile (default via `go.sh`). If you need more context, stop Goblin and raise Vorpal’s `VORPAL_MAX_MODEL_LEN` and `VORPAL_GPU_MEMORY_UTILIZATION`.
