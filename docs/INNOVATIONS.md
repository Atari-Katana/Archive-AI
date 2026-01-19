# Archive-AI Research & Technology Highlights

This page summarizes the novel architectures, agent designs, and research references that power Archive-AI v7.5.

## OctoTools-driven agentic framework
- Archive-AI integrates [OctoTools](https://github.com/octotools/octotools), the NAACL 2025 Best Paper framework for planning/executing tool-augmented reasoning flows, inside `brain/agents/react_agent.py` with safe fallbacks to the native ReAct loop when OctoTools is unavailable.
- The `docs/Archive-AI_System_Atlas_v7.5_REVISED.md` chapter VI.2 details the planner/executor/data-flow alongside the “One Logic Graph” orchestrating tool cards, memory recall, and reasoning agents.
- The included `octotools_repo` directory mirrors the upstream OctoTools toolkit and explains how tool cards can be added, swapped, or tuned for the experiments recorded in this codebase.

## Recursive Language Model (RLM)
- The RLM implementation follows the MIT CSAIL model (see [arXiv:2512.24601](https://arxiv.org/pdf/2512.24601)) documented in `docs/RECURSIVE_LANGUAGE_MODEL.md`.
- Instead of stuffing documents into a fixed context window, the agent exposes the corpus as a Python variable and recursively invokes `ask_llm()` while the code sandbox inspects, filters, and summarizes segments.
- The architecture diagram in that doc shows the Brain ↔ LLM ↔ sandbox feedback loop that enables effectively infinite-context processing.

## Titans-inspired Surprise Score Memory
- The asynchronous memory worker computes a Surprise Score per input using a weighted combination of perplexity and vector distance (60% perplexity + 40% novelty), as explained in `docs/OWNERS_MANUAL.md` and the archived checkpoint notes.
- The `scripts/tune-surprise-weights.py` and `scripts/test-surprise-scoring.py` scripts provide empirical tuning harnesses; you can replay them to calibrate thresholds or sampling behavior.
- This metric drives the Titan memory architecture referenced in `README.md` and the System Atlas, ensuring only “interesting” experiences are stored persistently.

## Chain of Verification for reliable answers
- The `/verify` endpoint in `brain/routes/chat.py` dispatches requests through `ChainOfVerification`, which sequentially runs a verification pipeline before returning a final answer.
- This mechanism bundles tool use, hallucination detection, and ensemble voting, letting agents quote why a response is trustworthy.
- The design is documented in the System Atlas and referenced in the README’s hallucination-mitigation bullet.

## Real-time metrics, config, and voice orchestration
- Metrics (CPU/RAM/VRAM/TPS) originate from `brain/services/metrics_service.py` and `bolt-xl/server_transformers.py`, with Vega/Chart.js charts in `ui/metrics-panel.html` plus a config UI that calls `brain/routes/config.py` for validation.
- Redis-backed metrics keys (`metrics:bolt_xl:tps`, `bolt_xl:device`, `bolt_xl:gpu_*`) keep the GUI synced with the GPU engine despite asynchronous inference.
- Voice integration (Faster Whisper + XTTS) and persona management are also described across README, `docs/VOICE_INTEGRATION.md`, and `voice/server.py`.

See `docs/legacy/` for archived planning documents that have been superseded by this consolidated documentation set.
