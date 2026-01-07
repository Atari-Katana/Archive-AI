# Phase 5: Advanced Features - Implementation Plan

**Date:** 2025-12-28
**Status:** Planning
**Prerequisites:** Phases 1-4 Complete (26/43 original chunks, 60.5%)
**Estimated Duration:** 2-3 weeks
**Target Chunks:** 11-13 new chunks

---

## Overview

Phase 5 focuses on advanced features that were deferred from earlier phases or represent new capabilities beyond the base system. Based on the original 43-chunk plan, we're incorporating library ingestion (originally Phase 3), voice testing (originally Phase 2/4), and new advanced features.

---

## Phase 5 Chunks (Proposed)

### **5.1: Library Ingestion - File Watcher & Processing**
**Files:** `librarian/watcher.py`, `librarian/processor.py`, `librarian/Dockerfile`, `librarian/requirements.txt`

**Combines original chunks 3.1 + 3.2 for efficiency**

**Task:**
- Watch `~/ArchiveAI/Library-Drop` for new files (PDF, TXT, MD)
- OCR for PDFs (Tesseract)
- Text extraction for TXT/MD
- Chunk into 250-token pieces with 50-token overlap
- Add metadata (filename, chunk index, type)
- Add librarian service to docker-compose

**Test:**
```bash
docker-compose up -d librarian
echo "Test document content for Archive-AI" > ~/ArchiveAI/Library-Drop/test.txt
# Check logs for processing trigger
# Verify chunks created with correct overlap
```

**Pass Criteria:**
- File changes detected automatically
- PDFs correctly OCR'd (test with sample PDF)
- Text files processed and chunked
- Chunk sizes within 200-300 token range
- Overlap preserved (50 tokens)
- Metadata complete (filename, chunk_index, timestamp)
- No crashes on invalid files

**CHECKPOINT:** `checkpoints/checkpoint-5.1-library-ingestion.md`

---

### **5.2: Library Storage & Search Integration**
**Files:** `librarian/storage.py`, `brain/tools/library_search.py`, `brain/main.py` (update)

**Combines original chunks 3.3 + 3.4**

**Task:**
- Store chunks in RedisVL with embeddings
- Tag with `type: library_book`
- Create search index for library content
- Integrate library search into Brain API
- Add `/library/search` endpoint
- Query both `type:memory` and `type:library_book` in unified search

**Test:**
```bash
# Add sample document
cp sample_doc.pdf ~/ArchiveAI/Library-Drop/
# Wait for processing (check logs)

# Search via API
curl -X POST http://localhost:8081/library/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Victorian railways", "top_k": 5}'

# Should return relevant chunks with similarity scores
```

**Pass Criteria:**
- Documents automatically processed and stored
- Chunks searchable via RedisVL
- Embeddings generated (sentence-transformers)
- Hybrid search works (memory + library)
- Results ranked by relevance
- Redis memory stays under 20GB cap
- Search latency < 500ms

**CHECKPOINT:** `checkpoints/checkpoint-5.2-library-search.md`

---

### **5.3: Voice Pipeline Testing & Integration**
**Files:** `scripts/test-voice-roundtrip.sh`, `brain/voice_handler.py`, `brain/main.py` (update)

**Combines original chunks 2.9 + 4.7 (voice features deferred earlier)**

**Task:**
- Download Piper voice model (one-time setup)
- Add `/voice_chat` endpoint to Brain
- Pipeline: audio → transcribe (Whisper) → chat → synthesize (Piper) → audio
- Measure total latency (target < 5 seconds)
- Create test script with sample audio files
- Optional: Add voice mode toggle to web UI

**Test:**
```bash
# Download voice model
./scripts/download-piper-voice.sh

# Test voice service directly
curl -X POST http://localhost:8001/transcribe -F "audio=@test_question.wav"
curl -X POST http://localhost:8001/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, this is a test"}' \
  --output test_output.wav

# Test full round-trip
./scripts/test-voice-roundtrip.sh
# Should: transcribe → get response → synthesize → save audio
```

**Pass Criteria:**
- Piper voice model loaded successfully
- Whisper transcription accurate (>90% WER on test set)
- TTS quality acceptable (no artifacts, clear speech)
- Full pipeline latency < 5 seconds
- Audio quality preserved through pipeline
- No race conditions or deadlocks
- Voice service stable under repeated use

**CHECKPOINT:** `checkpoints/checkpoint-5.3-voice-pipeline.md`

---

### **5.4: Specialized Agent - Research Assistant**
**Files:** `brain/agents/research_agent.py`, `brain/graph/research_flow.py`, `brain/main.py` (update)

**New chunk - implements specialized agent pattern**

**Task:**
- Create research agent with multi-step workflow:
  1. Break down research question into sub-questions
  2. Search library + memories for each sub-question
  3. Synthesize findings into coherent answer
  4. Cite sources
- Add `/research` endpoint
- Use Chain of Verification to validate claims
- Track research steps for transparency

**Test:**
```bash
curl -X POST http://localhost:8081/research \
  -H "Content-Type: application/json" \
  -d '{"question": "What were the major innovations in railway technology during the Victorian era?"}'

# Should return:
# - Detailed answer
# - Sub-questions asked
# - Sources cited
# - Verification status
```

**Pass Criteria:**
- Question decomposition works (generates 3-5 sub-questions)
- Library search returns relevant chunks
- Synthesis coherent and accurate
- Sources properly cited (chunk IDs, filenames)
- CoV catches hallucinations
- Research trace visible for debugging
- Works with empty library (graceful fallback)

**CHECKPOINT:** `checkpoints/checkpoint-5.4-research-agent.md`

---

### **5.5: Specialized Agent - Code Assistant**
**Files:** `brain/agents/code_agent.py`, `brain/main.py` (update)

**New chunk - coding-focused agent**

**Task:**
- Create code assistant agent with workflow:
  1. Understand coding task
  2. Generate code using CodeExecution tool
  3. Test code with sample inputs
  4. Debug if errors occur
  5. Return working code + explanation
- Add `/code_assist` endpoint
- Support: Python, bash scripts, SQL queries
- Include error recovery (max 3 retry attempts)

**Test:**
```bash
curl -X POST http://localhost:8081/code_assist \
  -H "Content-Type: application/json" \
  -d '{"task": "Write a Python function to calculate fibonacci numbers recursively, then test it with n=10"}'

# Should return:
# - Working Python code
# - Test output showing fibonacci(10) = 55
# - Explanation of approach
```

**Pass Criteria:**
- Generates syntactically correct code (>90%)
- Tests code automatically (print results)
- Debug loop works (fixes errors if found)
- Returns explanation of code logic
- Handles edge cases (invalid tasks, infinite loops)
- Sandbox timeout enforced (10s per execution)
- Code assistant doesn't hallucinate libraries

**CHECKPOINT:** `checkpoints/checkpoint-5.5-code-assistant.md`

---

### **5.6: Long-Term Memory - Cold Storage**
**Files:** `brain/memory/cold_storage.py`, `brain/workers/archiver.py`, `brain/config.py` (update)

**New chunk - implements memory tiering**

**Task:**
- Archive memories older than 30 days to disk (JSON files)
- Keep only last 1000 memories in Redis (FIFO + surprise threshold)
- Create archive search function (slower, searches JSON files)
- Automatic archival worker (runs daily)
- Archive format: `data/archive/YYYY-MM/memories-YYYYMMDD.json`

**Test:**
```bash
# Manually trigger archival
curl -X POST http://localhost:8081/admin/archive_old_memories

# Check archive files created
ls data/archive/2025-12/

# Search archived memories
curl -X POST http://localhost:8081/memories/search \
  -H "Content-Type: application/json" \
  -d '{"query": "old conversation", "include_archive": true}'
```

**Pass Criteria:**
- Old memories archived to disk (preserves all fields)
- Redis memory usage stays under limit
- Archive search works (slower but functional)
- Archived memories readable (valid JSON)
- No data loss during archival
- Archive files organized by date
- Automatic archival runs on schedule

**CHECKPOINT:** `checkpoints/checkpoint-5.6-cold-storage.md`

---

### **5.7: LangGraph Integration (Optional)**
**Files:** `brain/graph/langgraph_flow.py`, `brain/requirements.txt` (update), `brain/main.py` (update)

**Original chunk 3.5 - optional advanced orchestration**

**Task:**
- Install LangGraph
- Create graph-based workflow: Input → Route → Chat/Memory/Code/Research
- Replace direct endpoint logic with graph execution
- Support conditional routing (e.g., if memory search fails, try library)
- Add graph visualization endpoint (`/graph/visualize`)
- Maintain backward compatibility with existing endpoints

**Test:**
```bash
# Test routing through graph
curl -X POST http://localhost:8081/chat -d '{"message": "Hello"}'
# Should route to chat node

curl -X POST http://localhost:8081/chat -d '{"message": "Search my memories for pizza"}'
# Should route to memory search node

# Visualize graph
curl http://localhost:8081/graph/visualize > graph.html
# Open in browser, should see workflow diagram
```

**Pass Criteria:**
- LangGraph orchestrates all requests
- Routing decisions correct (>90% accuracy)
- Conditional logic works (fallback paths)
- Graph visualization clear
- Performance not degraded (< 100ms overhead)
- All existing endpoints still work
- Error handling in graph nodes

**CHECKPOINT:** `checkpoints/checkpoint-5.7-langgraph.md`

**Note:** This chunk is OPTIONAL. LangGraph adds complexity but enables advanced workflows. Skip if you prefer simpler direct routing.

---

### **5.8: Empirical Tuning - Surprise Weights**
**Files:** `scripts/tune-surprise-weights.py`, `brain/config.py` (update)

**Original chunk 3.10 - optimize memory filtering**

**Task:**
- Create test dataset (50+ examples, labeled high/low surprise)
- Test weight combinations: 0.5/0.5, 0.6/0.4, 0.7/0.3, 0.8/0.2
- Measure precision/recall for each combination
- Plot results (precision-recall curve)
- Update config with best weights
- Document optimal threshold value

**Test:**
```bash
python scripts/tune-surprise-weights.py --dataset tests/surprise-test-set.json
# Outputs:
# - Best weights: 0.6 perplexity / 0.4 novelty
# - Precision: 85%
# - Recall: 78%
# - Optimal threshold: 0.72
```

**Pass Criteria:**
- Test set represents realistic scenarios
- Best weights identified (maximize F1 score)
- Precision > 80%
- Recall > 70%
- Config updated with findings
- Results documented in checkpoint

**CHECKPOINT:** `checkpoints/checkpoint-5.8-tuning-surprise.md`

---

### **5.9: Multi-Modal Stress Test**
**Files:** `tests/multi-modal-stress-test.py`

**Original chunk 4.9 - concurrent workload testing**

**Task:**
- Automated test with concurrent workloads:
  - 10 chat threads
  - 5 library search threads
  - 3 code execution threads
  - 2 voice round-trips (if voice enabled)
  - 5 memory search threads
- Duration: 1 hour
- Monitor: VRAM, RAM, CPU, response times, errors
- Test for race conditions, deadlocks, resource exhaustion

**Test:**
```bash
python tests/multi-modal-stress-test.py --duration 3600 --threads 25
# Runs for 1 hour with 25 concurrent threads
# Generates report with metrics
```

**Pass Criteria:**
- All features work concurrently
- No deadlocks or race conditions
- VRAM stays under 14GB (if both engines running)
- RAM stays under 60GB total
- No data corruption (memories, library)
- Response times acceptable under load (<10s p95)
- Error rate < 5%

**CHECKPOINT:** `checkpoints/checkpoint-5.9-multi-modal-stress.md`

---

### **5.10: Edge Case Testing**
**Files:** `tests/edge-cases.py`

**Original chunk 4.11 - robustness testing**

**Task:**
- Test edge cases with automated script:
  - OOM trigger (attempt to load oversized model)
  - Invalid code execution (malformed Python, infinite loops)
  - Missing models (delete model, try to use it)
  - Redis connection loss (kill Redis, watch recovery)
  - Disk full during library ingestion (mock with small volume)
  - Corrupted memory data (inject bad JSON)
  - Network timeout (mock slow sandbox)
- Verify graceful degradation for each
- Document recovery procedures

**Test:**
```bash
python tests/edge-cases.py --test-all
# Each test should:
# 1. Trigger edge case
# 2. Verify error handling
# 3. Confirm recovery
# 4. Log results
```

**Pass Criteria:**
- All edge cases handled gracefully (no crashes)
- Error messages clear and actionable
- System recoverable (auto-restart or clear error state)
- No data loss (memories preserved)
- Redis persistence works (survives restart)
- Fallback modes work (e.g., chat works if library fails)
- All edge cases documented

**CHECKPOINT:** `checkpoints/checkpoint-5.10-edge-cases.md`

---

### **5.11: Production Deployment Configuration**
**Files:** `docker-compose.prod.yml`, `scripts/prod-deploy.sh`, `docs/production-guide.md`

**New chunk - production readiness**

**Task:**
- Create production docker-compose with:
  - Resource limits (VRAM, RAM, CPU)
  - Restart policies
  - Health checks for all services
  - Volume persistence
  - Log rotation
  - Security hardening (no root, minimal images)
- Deployment script with pre-flight checks
- Production configuration (environment variables)
- Monitoring setup (optional: Prometheus/Grafana endpoints)
- Backup/restore scripts for Redis data

**Test:**
```bash
# Deploy to production mode
./scripts/prod-deploy.sh --validate

# Should:
# - Check system requirements
# - Validate models present
# - Start all services with health checks
# - Run smoke tests
# - Report status
```

**Pass Criteria:**
- All services start with health checks passing
- Resource limits enforced
- Persistence works (survives restart)
- Logs rotated (don't fill disk)
- Backup/restore tested
- Security audit passed (no critical vulnerabilities)
- Production guide complete

**CHECKPOINT:** `checkpoints/checkpoint-5.11-production-deploy.md`

---

### **5.12: Performance Optimization Pass**
**Files:** Various (performance improvements across codebase)

**New chunk - optimization sweep**

**Task:**
- Profile critical paths (memory worker, agent loop, vector search)
- Optimize bottlenecks:
  - Cache embeddings for repeated queries
  - Batch vector searches
  - Optimize Redis queries (pipelining)
  - Reduce LLM calls where possible
  - Add response streaming for long outputs
- Measure improvements (before/after benchmarks)
- Document optimizations in code comments

**Test:**
```bash
# Benchmark before optimization
python scripts/benchmark.py --profile

# Apply optimizations

# Benchmark after
python scripts/benchmark.py --profile
# Compare results
```

**Pass Criteria:**
- Average response time improved by >20%
- Memory usage reduced or stable
- VRAM usage optimized
- No functionality regressions
- Benchmarks documented
- Critical paths profiled

**CHECKPOINT:** `checkpoints/checkpoint-5.12-performance-optimization.md`

---

### **5.13: Final Documentation & Release**
**Files:** `README.md`, `docs/`, `CHANGELOG.md`, `checkpoints/RELEASE-v7.5.md`

**Original chunk 4.12 - final polish**

**Task:**
- Complete comprehensive documentation:
  - README with quick start
  - Installation guide (with troubleshooting)
  - Architecture overview (with diagrams)
  - API reference (all endpoints)
  - Configuration guide
  - Troubleshooting common issues
  - Known limitations
- Create CHANGELOG with all features
- Final release checkpoint
- Tag release in git (v7.5.0)

**Test:**
```bash
# Have someone else follow installation guide
# Should be able to install and run without help

# Verify all docs links work
# Check for completeness
```

**Pass Criteria:**
- Installation guide complete and tested
- All features documented with examples
- API reference accurate (matches actual endpoints)
- Troubleshooting covers common issues (from testing)
- Architecture diagram clear
- Known issues documented (CodeExecution prompting, etc.)
- CHANGELOG complete
- Release checkpoint comprehensive

**CHECKPOINT:** `checkpoints/RELEASE-v7.5.md`

---

## Phase 5 Summary

### Total Chunks: 13
- **Library Ingestion:** 2 chunks (5.1-5.2)
- **Voice Pipeline:** 1 chunk (5.3)
- **Specialized Agents:** 2 chunks (5.4-5.5)
- **Memory System:** 1 chunk (5.6)
- **Advanced Orchestration:** 1 chunk (5.7, optional)
- **Optimization & Testing:** 4 chunks (5.8-5.11)
- **Documentation:** 1 chunk (5.12)

### Total Project: 39/43 chunks (90.7%)
- Phase 1: 5/5 ✅
- Phase 2: 9/9 ✅
- Phase 3: 12/12 ✅ (with modifications)
- Phase 4: 8/10 ✅ (2 deferred as non-critical)
- **Phase 5: 0/13 ⏳ (NEW)**

### Estimated Timeline
- **Fast Track:** 2 weeks (skip 5.7 LangGraph, minimal testing)
- **Standard:** 3 weeks (all chunks, thorough testing)
- **Comprehensive:** 4 weeks (includes extra polish, documentation)

### Critical Path (Minimum Viable Phase 5)
1. **5.1-5.2:** Library ingestion (enables knowledge base)
2. **5.3:** Voice pipeline (completes modalities)
3. **5.10:** Edge case testing (production readiness)
4. **5.11:** Production deployment (deployment ready)
5. **5.13:** Documentation (usable by others)

**Minimum:** 5 chunks for production-ready system with library support

### Optional/Deferrable
- **5.4-5.5:** Specialized agents (nice to have, not critical)
- **5.6:** Cold storage (only needed if >1000 memories)
- **5.7:** LangGraph (adds complexity, skip unless needed)
- **5.8:** Tuning (current weights working, optimization later)
- **5.9:** Multi-modal stress test (have 4.8 + 4.10 already)
- **5.12:** Performance optimization (optimize later if needed)

---

## Recommendations

### Option 1: Critical Path Only (2 weeks)
Focus on making Archive-AI production-ready with core features:
- Library ingestion for knowledge base ✅ Must-have
- Voice pipeline for full modality support ✅ Must-have
- Edge case testing for robustness ✅ Must-have
- Production deployment configuration ✅ Must-have
- Documentation for usability ✅ Must-have

**Result:** Production-ready Archive-AI v7.5 with all core features

### Option 2: Full Phase 5 (3-4 weeks)
Complete all 13 chunks for comprehensive feature set:
- Everything in Option 1
- Specialized agents (research, code assistant)
- Cold storage for long-term memory
- LangGraph for advanced orchestration
- Full testing suite (multi-modal, edge cases)
- Performance optimization pass

**Result:** Feature-complete Archive-AI v7.5 with advanced capabilities

### Option 3: Hybrid Approach (2.5 weeks)
Critical path + selective advanced features:
- 5.1-5.3: Library + Voice (core features)
- 5.4: Research agent (high value)
- 5.10-5.11: Testing + Deployment
- 5.13: Documentation
- **Skip:** 5.5 (code agent), 5.6 (cold storage), 5.7 (LangGraph), 5.8-5.9 (optimization/stress)

**Result:** Production-ready with research capabilities

---

## What Do You Think?

Which approach sounds best?
1. **Critical Path** (5 chunks, 2 weeks) - Library, Voice, Testing, Deploy, Docs
2. **Full Phase 5** (13 chunks, 3-4 weeks) - Everything including specialized agents
3. **Hybrid** (8 chunks, 2.5 weeks) - Critical + Research Agent
4. **Custom** - Pick specific chunks you want

Or would you like to adjust the plan (add/remove/reorder chunks)?
