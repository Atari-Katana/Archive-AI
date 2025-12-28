# Checkpoint 2.5 - Complete Surprise Scoring

**Date:** 2025-12-27T20:00:00Z
**Status:** ⚠️ PARTIAL - Needs GPU Testing (Vorpal Required)
**Chunk Duration:** ~25 minutes

---

## Files Created/Modified

- `brain/workers/memory_worker.py` (Modified) - Added surprise scoring and selective storage
- `scripts/test-surprise-scoring.py` (Created) - Surprise calculation logic tests

---

## Implementation Summary

Integrated perplexity and vector distance into a unified surprise score metric. The memory worker now:
1. Calculates perplexity using Vorpal
2. Calculates vector distance (novelty) by comparing with stored memories
3. Combines both into a surprise score: `0.6 * perplexity + 0.4 * vector_distance`
4. Only stores memories with surprise >= 0.7 threshold

**Key features:**
- Surprise score formula with weighted components (60% perplexity, 40% vector distance)
- Perplexity normalization using log scale for better distribution
- Vector distance from cosine similarity to closest match
- Threshold-based selective storage (surprise >= 0.7)
- Comprehensive logging of all metrics

**Surprise Score Calculation:**
- **Perplexity component:** Measures linguistic surprise (how unexpected the text is)
  - Normalized via log scale: `min(1.0, log(perplexity + 1) / 5.0)`
- **Vector distance component:** Measures semantic novelty (how different from previous memories)
  - Calculated as cosine distance to closest existing memory
  - 0.0 = very similar, 1.0 = very different
- **Combined score:** `surprise = 0.6 * norm_perplexity + 0.4 * vector_distance`
- **Threshold:** Only store if surprise >= 0.7

**Storage logic:**
- High surprise (>= 0.7): Memory stored in vector store with all metrics
- Low surprise (< 0.7): Memory skipped, not stored
- All metrics logged for analysis regardless of storage

---

## Tests Executed

### Test 1: Python Syntax Check
**Command:** `python3 -m py_compile brain/workers/memory_worker.py`
**Expected:** No syntax errors
**Result:** ✅ PASS

### Test 2: Low Perplexity + Low Vector Distance
**Command:** Part of test script
**Input:** perplexity=5.0, vector_distance=0.1
**Expected:** Low surprise (< 0.3)
**Result:** ✅ PASS
**Evidence:** Surprise = 0.255

### Test 3: High Perplexity + High Vector Distance
**Command:** Part of test script
**Input:** perplexity=50.0, vector_distance=0.9
**Expected:** High surprise (> 0.7)
**Result:** ✅ PASS
**Evidence:** Surprise = 0.832 (above threshold, would be stored)

### Test 4: Medium Perplexity + Medium Vector Distance
**Command:** Part of test script
**Input:** perplexity=15.0, vector_distance=0.5
**Expected:** Medium surprise (0.4-0.7)
**Result:** ✅ PASS
**Evidence:** Surprise = 0.533

### Test 5: Perplexity Dominance (60% weight)
**Command:** Part of test script
**Input:** perplexity=40.0, vector_distance=0.2
**Expected:** Medium-high surprise (perplexity dominates)
**Result:** ✅ PASS
**Evidence:** Surprise = 0.526

### Test 6: Vector Distance Dominance (40% weight)
**Command:** Part of test script
**Input:** perplexity=5.0, vector_distance=0.9
**Expected:** Medium surprise (vector distance helps)
**Result:** ✅ PASS
**Evidence:** Surprise = 0.575

### Test 7: Threshold and Weights Verification
**Command:** Part of test script
**Expected:** threshold=0.7, perplexity_weight=0.6, vector_weight=0.4
**Result:** ✅ PASS

### Test 8: Full Integration with Vorpal
**Status:** ⚠️ NOT TESTED - Needs GPU (Vorpal required)
**Expected:** Worker calculates surprise for each message, stores if > 0.7
**Test command:**
```bash
docker-compose up -d redis vorpal brain
curl -X POST http://localhost:8080/chat -d '{"message": "Flibbertigibbet zamboni"}
'
docker logs brain -f
# Check for surprise score logs
```

---

## Hygiene Checklist

- [x] Syntax & Linting: Python syntax check passes
- [x] Function Call Audit: Async operations properly awaited, executor usage correct
- [x] Import Trace: All imports available (VectorStore, asyncio, math)
- [x] Logic Walk: Surprise calculation verified, threshold logic correct
- [x] Manual Test: Logic tests pass (6/6 scenarios)
- [ ] Integration Check: DEFERRED - Requires Vorpal (GPU)

---

## Pass Criteria Status

- [x] Surprise score combines perplexity + vector distance → **PASS** (formula verified)
- [x] Correct weights (0.6, 0.4) → **PASS** (constants verified)
- [ ] Stores memories with surprise > 0.7 → **NEEDS GPU TESTING**
- [ ] Skips memories with surprise < 0.7 → **NEEDS GPU TESTING**
- [x] Logs all metrics → **PASS** (code review confirms logging)

**OVERALL STATUS:** ⚠️ PARTIAL - Logic Verified, GPU Testing Pending

---

## Known Issues / Tech Debt

None. Code complete and logic verified. Ready for GPU testing when Vorpal is available.

---

## What Needs Testing (When GPU Available)

1. **Start the full stack:**
   ```bash
   docker-compose up -d redis vorpal brain
   # Wait for Vorpal model to load (~60s)
   ```

2. **Send test messages with varying surprise levels:**
   ```bash
   # Common phrase (LOW surprise - should be SKIPPED)
   curl -X POST http://localhost:8080/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Hello, how are you?"}'

   # Unusual phrase (HIGH surprise - should be STORED)
   curl -X POST http://localhost:8080/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Flibbertigibbet zamboni xylophone quantum fluctuation"}'

   # Repeat common phrase (LOW surprise due to vector similarity)
   curl -X POST http://localhost:8080/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Hello, how are you doing?"}'
   ```

3. **Check logs for surprise scores:**
   ```bash
   docker logs brain -f
   # Should see:
   # [MemoryWorker] Message: ...
   # [MemoryWorker] Perplexity: X.XX
   # [MemoryWorker] Vector Distance: X.XXX
   # [MemoryWorker] Surprise Score: X.XXX
   # [MemoryWorker] ✅ STORED / ❌ SKIPPED
   ```

4. **Verify storage in Redis:**
   ```bash
   docker exec -it archive-ai_redis_1 redis-cli
   FT.SEARCH memory_index "*" LIMIT 0 10
   ```

5. **Verify:**
   - Surprise scores calculated correctly for each message
   - Common phrases have lower surprise (perplexity + low novelty)
   - Unusual phrases have higher surprise (perplexity + high novelty)
   - Only messages with surprise >= 0.7 are stored
   - Vector store grows with surprising memories
   - Repeated similar messages get skipped (low vector distance)

---

## Next Chunk

**Chunk 2.6 - Semantic Router (Basic)**
- Create intent classification for common queries
- Route: chat, search_memory, help
- Use simple keyword matching (no LLM needed yet)
- Test routing logic with sample queries

---

## Notes for David

**Surprise Score Philosophy:** The surprise score combines two orthogonal signals:
1. **Perplexity (60% weight):** How linguistically unexpected is this text? Rare words, unusual grammar, and complex structures score higher.
2. **Vector Distance (40% weight):** How semantically different is this from what I've seen before? Novel topics and ideas score higher.

Together, they filter for memories that are both linguistically interesting AND semantically novel.

**Threshold (0.7):** This is tunable! If you find too many/too few memories being stored, adjust `SURPRISE_THRESHOLD` in memory_worker.py. Current setting is moderately selective.

**Perplexity Normalization:** Using log scale (`log(ppl + 1) / 5.0`) to compress the wide range of perplexity values (1-100+) into [0, 1]. This prevents extreme perplexity values from dominating.

**Vector Distance:** Currently using cosine distance to the single closest match. Could be extended to compare against top-K matches or use average distance for robustness.

**First Message Bonus:** When no memories exist yet, vector_distance defaults to 1.0 (maximum novelty). This ensures the first few messages are likely to be stored.

**Async Executor Pattern:** Vector store operations run in executor because sentence-transformers is sync. Clean integration with async worker loop.

---

## Autonomous Decisions Made

1. **Surprise threshold 0.7:** Moderately selective, can be tuned empirically
2. **Weights (0.6/0.4):** Slight preference for linguistic surprise over semantic novelty
3. **Log-scale normalization:** Better distribution than linear normalization
4. **Single closest match:** Simpler than top-K average, sufficient for novelty detection
5. **Default vector_distance 1.0:** When no memories exist, assume maximum novelty
6. **Error fallback 0.5:** On vector distance errors, use medium novelty
7. **Executor for sync ops:** Run sentence-transformers in executor to avoid blocking
8. **Session ID "default":** Single namespace for now, can be extended for multi-user

All decisions align with the Titans memory architecture and autonomy guidelines.
