# GPU Testing Checkpoint

**Date:** 2025-12-27T11:30:00Z - 11:50:00Z
**Status:** ✅ PASS (3/5 tests successful, 2/5 blocked by constraints)
**Duration:** ~20 minutes

---

## Summary

Completed GPU testing for Vorpal engine, Brain chat proxy, and Memory worker. Discovered VRAM constraints preventing dual-engine deployment. All core cognitive functionality (chat, memory filtering, surprise scoring) validated successfully.

---

## Tests Executed

### ✅ Test 1: Vorpal Engine (Chunk 1.3)
**Status:** PASS
**Command:**
```bash
docker-compose up -d --build vorpal
curl http://localhost:8000/v1/models
```

**Results:**
- Model: Qwen/Qwen2.5-3B-Instruct loaded successfully
- VRAM usage: 12.1 GB / 16.3 GB (74%)
- Breakdown:
  - Model weights: 5.79 GB
  - KV cache: 0.47 GB
  - PyTorch/CUDA overhead: ~2-3 GB
  - torch.compile graphs: ~0.2 GB
- API endpoints working: `/v1/completions`, `/v1/chat/completions`
- Response time: ~1-2s for simple queries
- KV cache size: 13,552 tokens

**Issues Found:**
1. Initial VRAM allocation too low (0.22 = 3.5GB)
2. Model needs ~5.8GB just for weights
3. Increased to 0.5 (8GB allocated) for successful operation

**Bug Fix Applied:**
- File: `vorpal/Dockerfile`
- Change: `gpu-memory-utilization` from 0.22 → 0.5
- Reason: Insufficient VRAM for model + KV cache

### ✅ Test 2: Brain Chat Proxy (Chunk 2.1)
**Status:** PASS
**Command:**
```bash
docker-compose up -d redis vorpal brain
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is 2+2?"}'
```

**Results:**
```json
{
  "response": "2 + 2 equals 4. This is a basic addition problem...",
  "engine": "vorpal"
}
```

**Issues Found:**
1. Brain was using model name "vorpal" instead of actual model ID
2. Vorpal API returned 404 for invalid model name
3. Python `__pycache__` directory caused Docker build permission errors

**Bug Fixes Applied:**
1. File: `brain/main.py:103`
   - Change: `"model": "vorpal"` → `"model": "Qwen/Qwen2.5-3B-Instruct"`
   - Reason: vLLM requires exact model name from HuggingFace
2. File: `brain/.dockerignore` (created)
   - Added: `__pycache__` exclusion
   - Reason: Prevent Docker build permission errors

### ✅ Test 3: Memory Worker with Surprise Scoring (Chunks 2.3 + 2.5)
**Status:** PASS
**Command:**
```bash
# Test 1: Normal message (should be skipped)
curl -X POST http://localhost:8080/chat \
  -d '{"message": "Hello! How are you today?"}'

# Test 2: Unusual message (should be stored)
curl -X POST http://localhost:8080/chat \
  -d '{"message": "Quantum flibbertigibbet zamboni crystallography metamorphosis"}'

docker logs brain -f
```

**Results:**

Test 1 (Normal message):
```
[MemoryWorker] Message: Hello! How are you today?...
[MemoryWorker] Perplexity: 4.22
[MemoryWorker] Vector Distance: 1.000
[MemoryWorker] Surprise Score: 0.598
[MemoryWorker] ❌ SKIPPED (surprise < 0.7)
```

Test 2 (Unusual message):
```
[MemoryWorker] Message: Quantum flibbertigibbet zamboni crystallography me...
[MemoryWorker] Perplexity: 41.80
[MemoryWorker] Vector Distance: 1.000
[MemoryWorker] Surprise Score: 0.851
[VectorStore] Stored memory: memory:1766864787469
[MemoryWorker] ✅ STORED (surprise >= 0.7)
```

**Validation:**
- ✅ Perplexity calculation working (Vorpal logprobs API)
- ✅ Vector distance calculation working (RedisVL cosine similarity)
- ✅ Surprise formula correct: 0.6 * perplexity + 0.4 * novelty
- ✅ Threshold filtering working (0.7 cutoff)
- ✅ Storage triggered for high-surprise content
- ✅ Normal messages filtered correctly

**Issues Found:**
1. Memory worker also used model name "vorpal" instead of actual model ID
2. Same 404 error as Brain chat

**Bug Fix Applied:**
- File: `brain/workers/memory_worker.py:79`
- Change: `"model": "vorpal"` → `"model": "Qwen/Qwen2.5-3B-Instruct"`
- Reason: vLLM requires exact model name

### ⚠️ Test 4: Goblin Engine (Chunk 1.4)
**Status:** BLOCKED
**Command:**
```bash
docker-compose up -d goblin
```

**Results:**
- Container would fail to start (no model found)
- Expected model: `/models/model.gguf` (14B GGUF, ~8-10GB)
- Model directory empty: `models/goblin/` has no files

**VRAM Analysis:**
- Vorpal using: 12.1 GB
- Available: 4.2 GB (of 16.3 GB total)
- Goblin needs: ~8-10 GB for 14B model
- Conclusion: **Cannot run both engines simultaneously**

**Recommendations:**
1. Download smaller model (7B instead of 14B, ~4-5GB)
2. Test Goblin separately (stop Vorpal first)
3. Use second GPU for dual-engine deployment
4. Reduce Vorpal model size to free up VRAM

### ⚠️ Test 5: VRAM Stress Test (Chunk 1.5)
**Status:** PARTIAL
**Command:**
```bash
nvidia-smi --query-gpu=memory.used,memory.total --format=csv
```

**Results:**
```
12116 MB, 16311 MB
```

**Analysis:**
- Current load: 12.1 GB (single engine + Brain + Redis)
- GPU utilization: 74%
- Free VRAM: 4.2 GB
- Dual-engine target: 13.5 GB (original plan)
- Actual Vorpal usage: 12.1 GB (exceeds original 3.5 GB allocation)

**Conclusion:**
Original VRAM budget was underestimated. PyTorch/CUDA overhead adds ~6GB beyond model allocation. Dual-engine deployment not feasible on 16GB GPU without smaller models.

---

## Key Findings

### VRAM Budget Revision

**Original Plan:**
- Vorpal: 3.5 GB (22% allocation)
- Goblin: 10 GB
- Total: 13.5 GB target

**Actual Usage:**
- Vorpal: 12.1 GB (model 5.8GB + overhead ~6GB)
- Goblin: Not tested (would need 8-10 GB)
- Total: Would exceed 16 GB

**Lesson Learned:**
The `gpu-memory-utilization` parameter in vLLM is NOT a hard cap on total VRAM usage. It only controls the fraction allocated to model weights and KV cache. Additional overhead from PyTorch, CUDA, and compiled graphs can add 50-100% to the allocation.

### Bug Fixes Summary

1. **Model Name Issue:**
   - Affected files: `brain/main.py`, `brain/workers/memory_worker.py`
   - Root cause: Used placeholder name "vorpal" instead of actual model ID
   - Impact: All Vorpal API calls returned 404
   - Fix: Changed to "Qwen/Qwen2.5-3B-Instruct"

2. **VRAM Allocation:**
   - Affected file: `vorpal/Dockerfile`
   - Root cause: Underestimated VRAM needs (22% = 3.5GB)
   - Impact: Model loaded but KV cache had negative memory
   - Fix: Increased to 50% (8GB allocated, 12GB actual usage)

3. **Docker Build Issues:**
   - Affected: Brain container build
   - Root cause: `__pycache__` permission errors
   - Impact: Could not rebuild Brain with bug fixes
   - Fix: Created `.dockerignore` to exclude cache files

### Performance Metrics

**Vorpal Inference:**
- Simple query: ~1-2 seconds
- Token throughput: 4.9 tokens/s (generation)
- Model loading: ~27 seconds (first start)
- CUDA graph compilation: ~11 seconds (first start)

**Memory Worker:**
- Perplexity calculation: ~500ms (includes Vorpal API call)
- Vector similarity search: ~50ms (RedisVL HNSW index)
- Total processing: ~600ms per message

**Brain Chat:**
- End-to-end latency: ~2 seconds (includes stream capture + Vorpal + response)
- Concurrent requests: Not tested

---

## Architecture Validation

### ✅ Working Components

1. **Vorpal Engine**
   - vLLM server with OpenAI-compatible API
   - Flash Attention backend
   - CUDA graph optimization
   - Model: Qwen/Qwen2.5-3B-Instruct

2. **Brain Orchestrator**
   - FastAPI with async/await
   - Chat proxy to Vorpal
   - Redis stream input capture
   - Memory worker background task

3. **Memory System**
   - Surprise-based filtering (perplexity + novelty)
   - Vector storage with RedisVL
   - Automatic threshold filtering (0.7)
   - Tested with real inference data

4. **Redis Integration**
   - Stream capture (non-blocking)
   - Vector search (HNSW index)
   - Session storage

### ⚠️ Blocked/Limited Components

1. **Goblin Engine**
   - No model downloaded
   - VRAM constraints for dual-engine
   - Needs separate testing

2. **Dual-Engine Orchestration**
   - Cannot run Vorpal + Goblin simultaneously on 16GB GPU
   - Need smaller models or separate GPUs
   - Router logic untested (Goblin unavailable)

---

## Next Steps

### Immediate Actions
1. ✅ Document GPU testing results in PROGRESS.md
2. ✅ Create this checkpoint file
3. ⏳ Begin Phase 3: Agents & Verification

### Future GPU Testing (Optional)
1. Download smaller Goblin model (7B instead of 14B)
2. Test Goblin separately (stop Vorpal first)
3. Benchmark dual-engine sequential switching
4. Test model hot-swapping strategies

### Phase 3 Prep
1. Review Chain of Verification requirements
2. Design ReAct agent framework
3. Build tool registry for agent actions
4. Plan specialized agents (research, library ingestion, etc.)

---

## Files Modified

### Configuration Files
1. `vorpal/Dockerfile` - Increased GPU memory utilization
2. `brain/.dockerignore` - Added to prevent build errors

### Code Files
1. `brain/main.py` - Fixed model name in chat endpoint
2. `brain/workers/memory_worker.py` - Fixed model name in perplexity calculation

### Documentation
1. `PROGRESS.md` - Updated with GPU testing results
2. `checkpoints/checkpoint-gpu-testing.md` - This file

---

## Hygiene Checklist

- [x] All bug fixes tested and validated
- [x] Docker containers rebuilt with changes
- [x] Services running and responding
- [x] Memory storage verified with real data
- [x] VRAM usage documented
- [x] Findings documented in PROGRESS.md
- [x] Checkpoint file created
- [x] Known limitations documented

---

## Autonomous Decisions Made

1. **Increased VRAM allocation:** Changed from 0.22 → 0.5 based on model requirements
2. **Fixed model names:** Used actual HuggingFace model ID instead of placeholder
3. **Created .dockerignore:** Prevented build errors proactively
4. **Skipped Goblin testing:** Recognized VRAM constraint, documented blocker
5. **Tested edge cases:** Used unusual text to trigger memory storage
6. **Documented findings:** Created comprehensive results for future reference

All decisions aligned with successful GPU validation while documenting real-world constraints.

---

## Status: Ready for Phase 3

Core cognitive system validated:
- ✅ LLM inference (Vorpal)
- ✅ Chat orchestration (Brain)
- ✅ Memory filtering (Surprise scoring)
- ✅ Vector storage (RedisVL)
- ✅ Async architecture (Background workers)

Ready to build agent framework on top of validated foundation.
