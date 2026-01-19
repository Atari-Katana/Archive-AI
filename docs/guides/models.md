# Archive-AI Models Guide

## What the stack currently ships with
- **Bolt-XL (GPU-only)**: `Gemma-2B-it` (via `bolt-xl/server_transformers.py`) running under Docker with the Transformers stack. The model lives in `models/hf` (mounted into the container) and uses FP16/padded prompting. Default env settings are `BOLT_MODEL=google/gemma-2b-it`, `BOLT_DTYPE=float16`.
- **Vorpal Engine**: `Llama-3.2-3B-Instruct` (Q4_K_M) optimized for low-latency, CPU inference. Stored at `models/vorpal/Llama-3.2-3B-Instruct-Q4_K_M.gguf` and referenced via `VORPAL_MODEL_PATH`.
- **Goblin Engine**: `DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf` (CPU) for longer-form reasoning when Vorpal is busy.
- **Voice Models**
  - Whisper STT: `models/whisper` (base) with `WHISPER_DEVICE=cuda`, `WHISPER_COMPUTE_TYPE=float16`.
  - XTTS-v2: stored under `models/xtts` for Coqui/portraits.

## Changing or adding models
1. **Place new files** under `models/<service>/` (e.g., `models/goblin/your-model.gguf`).
2. **Update `.env` or `.env.example`**:
   - Set `BOLT_MODEL`/`BOLT_DTYPE` for GPU; `VORPAL_MODEL_PATH`, `GOBLIN_MODEL_PATH` and context/threads for CPU engines.
   - If you prefer a different tokenizer, adjust the `bolt-xl/server_transformers.py` defaults accordingly and rebuild the image.
3. **Rebuild & restart**:
   - Run `docker-compose build bolt-xl` if Bolt-XL’s Dockerfile paths or inertia change.
   - Restart `docker-compose up -d bolt-xl vorpal goblin` or rerun `./start`.
4. **Custom conversion**
   - Use `scripts/download-models.py` or external tools (Qwen to GGUF, AWQ to GGUF) before placing files in `models/`.
   - Ensure the `start` script’s autop-run path points to the correct file; update `BOLT_MODEL_DEFAULT` if needed.
5. **GPU constraints**
   - Gemma-2B-it consumes ~8-9GB VRAM; adjust `BOLT_DTYPE` to `float32` if you need precision or set `BOLT_MODEL` to a smaller option (e.g., `constellation/bolt-1b`).
   - For CPU fallback (Vorpal/Goblin), track `VORPAL_THREADS`, `GOBLIN_THREADS`, and `*_BATCH_SIZE` in `.env`.

## Tips
- Keep `models/hf` cached (the Bolt-XL image exposes it via `HF_HOME`). Use `huggingface-cli` to prefetch if needed.
- Document your new model in `docs/INNOVATIONS.md` or an appropriate sub-section.
