# Archive-AI v7.5 - Project Context

**Status:** In Development (Phase 1)
**Target:** Production-ready local AI cognitive framework
**Hardware:** Single NVIDIA RTX 5060 Ti (16GB VRAM) + 64GB RAM

---

## What This Is

Archive-AI is a local-first AI companion system with:
- **Permanent memory** using "Surprise Score" metric (Titans architecture)
- **Dual inference engines** (Vorpal + Goblin) optimized for 16GB GPU
- **Voice I/O** (FastWhisper + XTTS with Ian McKellen voice)
- **Agentic capabilities** (LangGraph with ReAct loops)
- **Library ingestion** for document knowledge base
- **Chain of Verification** for hallucination mitigation

---

## The Sacred Constraints

### VRAM Budget (DO NOT EXCEED)
- **Vorpal** (vLLM): 3.5GB - Chat, routing, perplexity
- **Goblin** (llama.cpp): 10GB - Reasoning, coding
- **Total**: 13.5GB (leaves 2.5GB buffer for OS/CUDA)

### Memory Limits
- **Redis**: 20GB max with `allkeys-lru` eviction
- **System RAM**: < 24GB excluding Redis

### Security (Sandbox)
- No root access
- No external network
- Isolated execution only

---

## The Development Process

### Chunk Discipline
- **43 chunks** across 4 phases
- **1-3 hours** per chunk
- **Test & checkpoint** after each one
- **NO combining chunks** - this is critical

### Checkpoint Format
After every chunk, create `checkpoints/checkpoint-X.Y-name.md` with:
- Files created/modified
- Implementation summary
- Test results with evidence
- Hygiene checklist completion
- Pass criteria verification
- Status: PASS / FAIL / PARTIAL / BLOCKED

### Hygiene Checklist (Every Chunk)
1. Syntax & linting (`flake8`)
2. Function call audit (signatures match)
3. Import trace (all in requirements.txt)
4. Logic walk (bug check)
5. Manual test (all pass criteria)
6. Integration check (doesn't break previous work)

---

## Key Documents

- **[CLAUDE_CODE_HANDOFF.md](/home/davidjackson/Archive-AI/Docs/CLAUDE_CODE_HANDOFF.md)** - Mission, autonomy guidelines, David's preferences
- **[System Atlas v7.5](/home/davidjackson/Archive-AI/Docs/Archive-AI_System_Atlas_v7.5_REVISED.md)** - Architecture spec (THE GOSPEL)
- **[Implementation Plan](/home/davidjackson/Archive-AI/Docs/Archive-AI_Implementation_Plan_v7.5.md)** - 43-chunk work order

---

## Model Catalog

| Role | Model | Engine | Format | VRAM | Purpose |
|------|-------|--------|--------|------|---------|
| Scout | Llama-3-8B-Instruct (4.0bpw) | Vorpal | EXL2 | ~3.0GB | Chat, routing, perplexity |
| Thinker | DeepSeek-R1-Distill-Qwen-14B (Q4_K_M) | Goblin | GGUF | ~8.5GB | Reasoning, CoT, agents |
| Coder | Qwen-2.5-Coder-14B (Q4_K_M) | Goblin | GGUF | ~8.0GB | Python, system engineering |

---

## Progress Tracker

### Phase 1: Infrastructure (Week 1)
- [ ] 1.1 - Redis Stack Setup
- [ ] 1.2 - Code Sandbox Container
- [ ] 1.3 - Vorpal Engine Setup
- [ ] 1.4 - Goblin Engine Setup
- [ ] 1.5 - VRAM Stress Test

### Phase 2: Logic Layer + Voice (Week 2)
- [ ] 2.1 - Archive-Brain Core (Minimal)
- [ ] 2.2 - Redis Stream Input Capture
- [ ] 2.3 - Async Memory Worker (Perplexity Only)
- [ ] 2.4 - RedisVL Vector Storage
- [ ] 2.5 - Complete Surprise Scoring
- [ ] 2.6 - Semantic Router (Basic)
- [ ] 2.7 - Voice Service - FastWhisper
- [ ] 2.8 - Voice Service - XTTS
- [ ] 2.9 - Voice Round-Trip Integration

### Phase 3: Integration, Agents & Tuning (Week 3)
- [ ] 3.1-3.11 (Library ingestion, agents, CoV, tuning)

### Phase 4: UI & Polish (Week 4)
- [ ] 4.1-4.12 (Dashboard, model hub, stress tests, docs)

---

## Autonomy Guidelines

### ✅ Decide Autonomously
- Implementation details (code structure, variable names)
- Library choices within reason
- Bug fixes (syntax, imports, type errors, logic bugs)
- Minor optimizations that don't change architecture

### 🚫 Escalate to David
- Architecture changes (VRAM allocation, model choices, Redis schema)
- Spec conflicts or impossibilities
- Major blockers (hardware access, unclear requirements)
- Security/data loss risks

---

## Quick Reference

### Common Commands
```bash
# Start services
docker-compose up -d [service]

# Check VRAM
nvidia-smi

# Lint code
flake8 <files>

# Test imports
python -c "import X"

# Redis CLI
redis-cli
```

### Project Structure
```
archive-ai/
├── brain/          # Orchestrator + LangGraph
├── vorpal/         # Speed engine (vLLM)
├── goblin/         # Capacity engine (llama.cpp)
├── sandbox/        # Code execution
├── voice/          # Speech I/O
├── librarian/      # Library ingestion
├── ui/             # Dashboard
├── scripts/        # Test scripts
├── checkpoints/    # Progress tracking
├── models/         # Model storage
└── data/           # Persistent data
```

---

## Current Status

**Active Chunk:** None (starting Chunk 1.1)
**Last Checkpoint:** None
**Blockers:** None

---

## Notes for Future Claude

- Read this file first for quick orientation
- Check latest checkpoint in `checkpoints/` for current state
- Never combine chunks - discipline is key to success
- VRAM budget is non-negotiable
- When in doubt about architecture, escalate to David
- Test thoroughly, checkpoint honestly (FAIL is okay, lying is not)

---

**Last Updated:** 2025-12-27
**Next Chunk:** 1.1 - Redis Stack Setup
