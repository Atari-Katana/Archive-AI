# Archive-AI Quickstart Guide

## Prerequisites
- Linux 22.04+ with NVIDIA driver >= 535 and Docker/NVIDIA Container Toolkit installed.
- 16GB+ VRAM GPU (RTX 5060 Ti, 4060 Ti 16GB, etc.) and 32GB RAM.
- Clone repo, then `cp .env.example .env` and edit:
  - `REDIS_URL` should point to the `redis` service (default `redis://redis:6379`).
  - `HF_TOKEN` only if pulling gated models.
  - `BOLT_MODEL`, `VORPAL_MODEL`, etc., can follow the defaults for Gemma-2B-it + Llama-3.2-3B-Instruct.

## Launching the Stack
1. Run `./start` and choose option `1` (Web UI). The script: cleans old resources, builds Docker images, starts `redis`, `brain`, `bolt-xl`, `vorpal`, `voice`, `bifrost`, `goblin`, etc., and opens the UI on `http://localhost:8888`.
2. After services are healthy, open the metrics panel (`http://localhost:8080/ui/metrics-panel.html`) to ensure TPS/VRAM/RAM meters populate.
3. Use the web interface for chat or switch to headless API mode (option `3` in `./start`), hitting `http://localhost:8080/chat` and `/metrics` endpoints.

## Verifying Installation
- Run `bash scripts/health-check.sh` (if available) or use `curl http://localhost:8080/health`.
- Check Bolt-XL: `curl http://localhost:8007/health` and `curl http://localhost:8007/v1/chat/completions` with a simple payload.

## Routine Commands
- Restart services: `docker-compose restart bolt-xl brain voice`.
- Tail logs: `docker-compose logs --tail=60 bolt-xl` or `brain`.
- Clean run: `docker-compose down -v` then `./start` again.

## Tips
- Keep `models/` populated (see Models Guide) so `bolt-xl` and `vorpal` can mount them at runtime.
- Edit config via the UI’s config drawer or call `POST http://localhost:8080/config/`.
- If the metrics panel or UI seems stale, do a hard refresh (`Ctrl+Shift+R`).
