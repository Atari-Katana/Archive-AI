# Archive-AI Master Operations Guide

This guide documents every major subsystem so operators can run, repair, and adapt Archive-AI v7.5.

## System Overview
- **Brain (FastAPI)** orchestrates users, agents, memories, configuration, metrics, and research endpoints (`/chat`, `/verify`, `/metrics`, `/config`, etc.).
- **Bolt-XL** is the GPU-only Gemma-2B-it engine in `bolt-xl/` that serves `/health` and `/v1/chat/completions`.
- **Vorpal + Goblin** provide faster/longer-context CPU inference paths via vLLM (`vorpal`) and `llama.cpp` (`goblin`).
- **Redis Stack** stores streaming state, vectors, metrics (e.g., `metrics:bolt_xl:tps`), persona info, and the Surprise Score cache.
- **Voice (Whisper + XTTS)** enables STT and TTS; persona samples are referenced from `ui/personas` when synthesizing.
- **Bifrost, Sandbox, Librarian** extend the agentic capability with semantic routing, safe code execution, and document ingestion.

### Research Foundations
- **OctoTools agent stack** runs inside `brain/agents/react_agent.py` (with fallbacks to native ReAct) and mirrors the OctoTools planning+executor design documented in `docs/Archive-AI_System_Atlas_v7.5_REVISED.md`.
- **Recursive Language Model (RLM)** uses a Python REPL to treat massive corpora as variables instead of context windows; see `docs/RECURSIVE_LANGUAGE_MODEL.md` for architecture, workflow, and API patterns.`
- **Titans Surprise Score** filters which experiences are remembered by combining perplexity and vector distance, as described throughout the System Atlas, `docs/OWNERS_MANUAL.md`, and tuning scripts under `scripts/`.
- **Chain of Verification** ensures trusted answers before returning them through `brain/routes/chat.py` (the `/verify` handler wraps multiple verification phases).

## Daily Operations
1. Copy `.env.example` to `.env`, set secrets (e.g., `REDIS_URL`, `HF_TOKEN`), and confirm model folders exist under `./models/`.
2. Run `./start` and choose Web UI (`1`) to launch the full stack including the UI, metrics, and config dashboards. Use `./start` for clean start/stop cycles.
3. For granular control, use `docker-compose up -d`, `docker-compose logs`, or `docker-compose restart <service>` (services defined in `docker-compose.yml`).
4. Monitor system health via the metrics panel (`http://localhost:8080/ui/metrics-panel.html`) and the Brain’s `/metrics` API.

## Troubleshooting & Repair
- **Bolt-XL errors**: rebuild with `docker-compose build bolt-xl` after verifying `bolt-xl/requirements.txt` and GPU availability. Metrics data is stored in Redis keys like `bolt_xl:device` and `bolt_xl:gpu_used_mb`.
- **Redis issues**: confirm every service uses the same `REDIS_URL`. If metrics disappear, restart the Brain+Bolt-XL after ensuring Redis is reachable from inside containers.
- **Voice problems**: check `models/whisper` and `models/xtts` directories, ensure `voice` container has GPU runtime enabled, and inspect `voice/server.py` logs for model load failures.
- **OctoTools errors**: `brain/agents/react_agent.py` will log OctoTools exceptions and revert to native ReAct; ensure `octotools_repo` is synced and Python paths include it.

## Change Management
- Update `.env` for runtime overrides (model names, GPU flags, Surprise threshold). The Brain’s `/config` endpoint persists changes via `brain/routes/config.py` and is accessible from the configuration panel at `http://localhost:8080/ui/config-panel.html`.
- To swap models, see the dedicated Models Guide (`docs/guides/models.md`).
- For agent tweaks, edit `brain/agents/*` and rerun `./start` or `docker-compose restart brain` after building any new Python dependencies with `brain/requirements.txt`.
- Logging and metrics come from both Brain and Bolt-XL; use `docker-compose logs` plus the `metrics` API to validate system health after configuration changes.
