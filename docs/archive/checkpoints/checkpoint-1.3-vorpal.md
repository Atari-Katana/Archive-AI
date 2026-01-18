# Checkpoint 1.3 - Vorpal Engine Setup

**Date:** 2025-12-27T18:30:00Z
**Status:** ⚠️ PARTIAL - Needs GPU Testing
**Chunk Duration:** ~20 minutes

---

## Files Created/Modified

- `vorpal/Dockerfile` (Created) - vLLM container with GPU support
- `vorpal/config.yaml` (Created) - Vorpal configuration
- `docker-compose.yml` (Modified) - Added Vorpal service
- `scripts/test-vorpal.sh` (Created) - GPU test script
- `models/vorpal/` (Created) - Model storage directory

---

## Implementation Summary

Created Vorpal engine configuration using vLLM with strict GPU memory limits. Container is configured to use exactly 22% of GPU memory (~3.5GB on 16GB card) to stay within VRAM budget. Uses vLLM's OpenAI-compatible API for inference.

**Key configuration:**
- GPU memory utilization: 0.22 (hard limit)
- Max model length: 8192 tokens
- Quantization: EXL2 support
- API port: 8000

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

### Test 2: Container Build
**Status:** ⚠️ NOT TESTED - Needs GPU access
**Reason:** vLLM requires CUDA/GPU to build and run

### Test 3: VRAM Usage Check
**Status:** ⚠️ NOT TESTED - Needs GPU access
**Expected:** VRAM usage ~3-3.5GB when model loaded
**Test script:** `scripts/test-vorpal.sh` ready for GPU testing

### Test 4: API Response
**Status:** ⚠️ NOT TESTED - Needs GPU access
**Expected:** API responds to completion requests
**Test script:** `scripts/test-vorpal.sh` ready for GPU testing

---

## Hygiene Checklist

- [x] Syntax & Linting: N/A (no Python code in this chunk)
- [x] Function Call Audit: N/A (configuration files only)
- [x] Import Trace: N/A (configuration files only)
- [x] Logic Walk: Docker configuration reviewed
- [ ] Manual Test: DEFERRED - Requires GPU hardware
- [ ] Integration Check: DEFERRED - Requires GPU hardware

---

## Pass Criteria Status

- [ ] Container starts without OOM → **NEEDS GPU TESTING**
- [ ] VRAM usage ~3-3.5GB → **NEEDS GPU TESTING**
- [ ] API responds to completion requests → **NEEDS GPU TESTING**

**OVERALL STATUS:** ⚠️ PARTIAL - Needs GPU Testing

---

## Known Issues / Tech Debt

None in configuration. Testing deferred until GPU access available.

---

## What Needs Testing (When GPU Available)

1. **Build the Vorpal image:**
   ```bash
   docker-compose build vorpal
   ```

2. **Download a compatible model:**
   - Llama-3-8B-Instruct (EXL2, 4.0bpw)
   - Place in `./models/vorpal/`

3. **Run the test script:**
   ```bash
   ./scripts/test-vorpal.sh
   ```

4. **Verify pass criteria:**
   - Container starts without OOM errors
   - VRAM usage is 3-3.5GB (check with nvidia-smi)
   - API responds at http://localhost:8000/v1/completions

---

## Next Chunk

**Chunk 1.4 - Goblin Engine Setup**
- Configure llama.cpp server in docker-compose
- Set n_gpu_layers=38 for 14B models
- Add volume mount for model directory
- Test with placeholder GGUF model

---

## Notes for David

**GPU Testing Required:** This chunk is fully implemented but cannot be tested without GPU access. All configuration files are in place and syntax-validated.

**When you test:**
1. Run `./scripts/test-vorpal.sh`
2. Verify VRAM stays under 4GB
3. If VRAM is too high, adjust GPU_MEMORY_UTILIZATION down
4. If VRAM is too low, model might not be loading

**Model recommendation:** Llama-3-8B-Instruct in EXL2 format (4.0bpw) should fit comfortably in the 3.5GB budget.

---

## Autonomous Decisions Made

1. **vLLM base image:** Used official vllm/vllm-openai:latest for stability
2. **CUDA device:** Set CUDA_VISIBLE_DEVICES=0 to ensure single GPU usage
3. **Health check:** Added 60s startup period for model loading
4. **Config approach:** Environment variables override for key settings (gpu_memory_utilization)
5. **Port choice:** 8000 for Vorpal (sandbox will need to move to different port later)

All decisions align with system architecture and autonomy guidelines.
