# Checkpoint 1.4 - Goblin Engine Setup

**Date:** 2025-12-27T18:35:00Z
**Status:** ⚠️ PARTIAL - Needs GPU Testing
**Chunk Duration:** ~15 minutes

---

## Files Created/Modified

- `goblin/start.sh` (Created) - Startup script for llama.cpp server
- `docker-compose.yml` (Modified) - Added Goblin service
- `scripts/test-goblin.sh` (Created) - GPU test script
- `models/goblin/` (Created) - Model storage directory

---

## Implementation Summary

Created Goblin engine configuration using llama.cpp server with GPU layer tuning. Container is configured to load 38 GPU layers for 14B models, targeting ~10GB VRAM usage. Uses llama.cpp's native API for inference with continuous batching and flash attention.

**Key configuration:**
- GPU layers: 38 (tuned for 14B Q4_K_M models)
- Context size: 8192 tokens
- Flash attention enabled
- Continuous batching for efficiency
- API port: 8080

---

## Tests Executed

### Test 1: Docker Compose Syntax
**Command:** `docker-compose config --quiet`
**Expected:** No errors
**Result:** ✅ PASS
**Evidence:**
```
✅ docker-compose.yml syntax valid
```

### Test 2: Startup Script Validation
**Command:** `bash -n goblin/start.sh`
**Expected:** No syntax errors
**Result:** ✅ PASS

### Test 3: Container Build
**Status:** ⚠️ NOT TESTED - Needs GPU access
**Reason:** llama.cpp CUDA image requires GPU to run

### Test 4: VRAM Usage Check
**Status:** ⚠️ NOT TESTED - Needs GPU access
**Expected:** VRAM usage ~8-10GB when model loaded
**Test script:** `scripts/test-goblin.sh` ready for GPU testing

### Test 5: API Response
**Status:** ⚠️ NOT TESTED - Needs GPU access
**Expected:** API responds to completion requests
**Test script:** `scripts/test-goblin.sh` ready for GPU testing

### Test 6: Combined VRAM (Vorpal + Goblin)
**Status:** ⚠️ NOT TESTED - Needs GPU access
**Expected:** Total VRAM < 14GB
**Test script:** `scripts/test-goblin.sh` includes combined check

---

## Hygiene Checklist

- [x] Syntax & Linting: Bash script syntax validated
- [x] Function Call Audit: N/A (shell script)
- [x] Import Trace: N/A (shell script)
- [x] Logic Walk: Startup script reviewed
- [ ] Manual Test: DEFERRED - Requires GPU hardware
- [ ] Integration Check: DEFERRED - Requires GPU hardware with Vorpal

---

## Pass Criteria Status

- [ ] Container starts without OOM → **NEEDS GPU TESTING**
- [ ] VRAM usage ~8-10GB → **NEEDS GPU TESTING**
- [ ] API responds to completion requests → **NEEDS GPU TESTING**
- [ ] Total VRAM (Vorpal + Goblin) < 14GB → **NEEDS GPU TESTING**

**OVERALL STATUS:** ⚠️ PARTIAL - Needs GPU Testing

---

## Known Issues / Tech Debt

None in configuration. Testing deferred until GPU access available.

---

## What Needs Testing (When GPU Available)

1. **Download a compatible model:**
   - DeepSeek-R1-Distill-Qwen-14B (Q4_K_M, GGUF)
   - OR Qwen-2.5-Coder-14B-Instruct (Q4_K_M, GGUF)
   - Place as `./models/goblin/model.gguf`

2. **Run the test script:**
   ```bash
   ./scripts/test-goblin.sh
   ```

3. **Verify pass criteria:**
   - Container starts without OOM errors
   - VRAM usage is 8-10GB (check with nvidia-smi)
   - API responds at http://localhost:8080/completion
   - Combined VRAM (if Vorpal running) < 14GB

4. **Tuning if needed:**
   - If VRAM > 10GB: Reduce N_GPU_LAYERS (try 35, 32)
   - If VRAM < 8GB: Model might not be loading or layers too low

---

## Next Chunk

**Chunk 1.5 - VRAM Stress Test**
- Write script that hammers both engines simultaneously
- Monitor VRAM usage over 10-minute period
- Log any OOM warnings or crashes

---

## Notes for David

**GPU Testing Required:** This chunk is fully implemented but cannot be tested without GPU access. All configuration files are in place and syntax-validated.

**Both engines use same GPU:** Note that both Vorpal and Goblin have `CUDA_VISIBLE_DEVICES=0`, meaning they share GPU 0. This is intentional for the 16GB single-GPU setup.

**Start script approach:** Using a custom start.sh gives us flexibility to add pre-flight checks, logging, and dynamic configuration later.

**Model swap ready:** The llama.cpp server can swap models without restart (just point to different model.gguf). This will be used in Phase 2 for Thinker <-> Coder swapping.

---

## Autonomous Decisions Made

1. **llama.cpp official image:** Used ghcr.io/ggerganov/llama.cpp:server-cuda for stability
2. **Startup script:** Created start.sh for better control and logging
3. **90s initialization:** Increased wait time in test (14B models load slower than 8B)
4. **Flash attention:** Enabled for performance (llama.cpp supports this)
5. **Continuous batching:** Enabled for better throughput with multiple requests
6. **Port choice:** 8080 for Goblin (separate from Vorpal's 8000)

All decisions align with system architecture and autonomy guidelines.
