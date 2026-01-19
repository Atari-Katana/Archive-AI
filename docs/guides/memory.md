# Memory System Guide

Archive-AI’s memory pipeline stores only the most informative experiences using the **Surprise Score** and tiered storage.

## Pipeline overview
1. **Input stream**: every user message is pushed into a Redis stream; the memory worker (`brain/workers/memory_worker.py`) pulls entries asynchronously.
2. **Surprise Score calculation** combines language perplexity and vector distance to recent memories:
   - `surprise = 0.6 * perplexity + 0.4 * semantic_distance`
   - Higher values (≥0.7 by default) signal novel/interesting content worth persisting.
3. **Storage**: surprising memories are archived to Redis + vector store (via `memory/vector_store.py`) and optionally persisted to disk (cold storage) for offline recall.
4. **Recall**: conversations query `POST /memories/search` or a Research Agent merges matching nodes.

## Config & tuning
- Types/thresholds live in `.env` (e.g., `ARCHIVE_DAYS_THRESHOLD`, `ARCHIVE_KEEP_RECENT`, `ARCHIVE_ENABLED`).
- Use `scripts/tune-surprise-weights.py` to run experiments; the script reports Surprise Score distributions and suggestions for weights.
- `scripts/test-surprise-scoring.py` validates the metric against known inputs; run it after tweaking the formula.

## Repair & introspection
- For debugging, check `logs/memory-worker.log` (if enabled) or monitor `brain/workers/memory_worker.py` output—each stored memory includes Surprise and timestamp annotations.
- The UI’s memory browser (section 4.4 in the archived checkpoint notes) displays Surprise Scores; use it to verify the worker filters noise correctly.
- To clear or archive old memories, call `/memories/archive` (if implemented) or run the Brain’s archival worker as described in `docs/ARCHIVE` (if available).
