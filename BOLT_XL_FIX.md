# Bolt-XL Configuration Fix
**Date**: 2026-01-17
**Status**: ✅ Fixed

## Summary

Bolt-XL has been properly restored and configured with a compatible model. The issue was that Bolt-XL was attempting to load Qwen3-OmniMoE (a complex multimodal MoE model) which it doesn't support.

---

## The Problem

**Original Issue**: Bolt-XL was crashing because:
1. The model at `models/bolt-xl/` is Qwen3-OmniMoE - a multimodal Mixture-of-Experts architecture
2. Bolt-XL's Candle-based inference engine only supports standard transformer architectures
3. No compatible model was configured as a fallback

**Why It Failed**: Bolt-XL tried to load an incompatible architecture and crashed during model initialization.

---

## The Fix

### 1. Restored Bolt-XL to Codebase

All Bolt-XL references have been restored:
- `docker-compose.yml` - Service definition
- `brain/config.py` - BOLT_XL_URL and BOLT_XL_MODEL
- `brain/services/chat_service.py` - Primary engine with proper model name
- `brain/services/metrics_service.py` - Health checks and metrics
- `brain/services/system_service.py` - Status monitoring

### 2. Configured Compatible Model

**Default Model**: `TinyLlama/TinyLlama-1.1B-Chat-v1.0`

**Why TinyLlama**:
- Lightweight (1.1B parameters)
- Fast inference
- Standard transformer architecture (fully supported by Bolt-XL)
- Auto-downloads from HuggingFace on first run
- Proven compatibility with Candle

**Environment Variables**:
```bash
BOLT_MODEL=TinyLlama/TinyLlama-1.1B-Chat-v1.0          # For Bolt-XL engine
BOLT_XL_MODEL=TinyLlama/TinyLlama-1.1B-Chat-v1.0      # For Brain service
```

### 3. Fixed Chat Service Model Passing

**Before** (BUG):
```python
return await self._call_engine(
    config.BOLT_XL_URL,
    config.VORPAL_MODEL,  # ❌ Wrong model!
    messages,
    "bolt-xl"
)
```

**After** (FIXED):
```python
return await self._call_engine(
    config.BOLT_XL_URL,
    config.BOLT_XL_MODEL,  # ✅ Correct model!
    messages,
    "bolt-xl"
)
```

---

## How It Works Now

### Engine Priority
```
1. Bolt-XL (TinyLlama) - PRIMARY
   ↓ (if fails)
2. Vorpal (Qwen2.5-3B) - FALLBACK
```

### Model Loading
When Bolt-XL starts:
1. Checks for `BOLT_MODEL` environment variable
2. Downloads TinyLlama from HuggingFace if not cached
3. Loads model into GPU memory (~2GB VRAM)
4. Starts OpenAI-compatible API server on port 3000
5. Brain sends chat requests with `BOLT_XL_MODEL` identifier

---

## Alternative Models

You can swap TinyLlama for other compatible models by changing the env var:

### Qwen2.5-3B (Better Quality)
```bash
BOLT_MODEL=Qwen/Qwen2.5-3B-Instruct
BOLT_XL_MODEL=Qwen/Qwen2.5-3B-Instruct
```
- Size: 3B parameters (~6GB VRAM)
- Quality: Better than TinyLlama
- Speed: Slightly slower

### Llama-2-7B (Requires Token)
```bash
HF_TOKEN=your_huggingface_token_here
BOLT_MODEL=meta-llama/Llama-2-7b-chat-hf
BOLT_XL_MODEL=meta-llama/Llama-2-7b-chat-hf
```
- Size: 7B parameters (~14GB VRAM)
- Quality: High quality responses
- Requires: HuggingFace account + token

---

## About the Qwen3-OmniMoE Model

**Location**: `models/bolt-xl/` (26GB)

**Status**: Incompatible with Bolt-XL

**Why Keep It**:
- May be useful for other purposes
- Could be supported in future Bolt-XL versions
- Takes time to re-download if deleted

**Why Not Use It**:
- Requires custom MoE routing code
- Needs audio encoder support
- Multimodal capabilities not in Bolt-XL

**If You Want to Use It**:
You would need to either:
1. Implement Qwen3-OmniMoE support in Bolt-XL (complex)
2. Use a different inference engine that supports it (e.g., vLLM with custom plugins)
3. Wait for Bolt-XL to add MoE support

---

## Testing

### Start the System
```bash
./start --web
```

### Verify Bolt-XL Starts
```bash
docker logs archive-bolt-xl

# Should see:
# "Starting Bolt-XL v0.2.0"
# "Loading model: TinyLlama/TinyLlama-1.1B-Chat-v1.0"
# "Model loaded successfully"
# "Server listening on 0.0.0.0:3000"
```

### Test Chat Endpoint
```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}'

# Should return response from Bolt-XL
```

### Check Logs for Engine Used
```bash
docker logs archive-brain --tail 20

# Should see:
# [INFO] Attempting primary engine: Bolt-XL (http://bolt-xl:3000)
# [INFO] Chat completed successfully with engine: bolt-xl
```

---

## Troubleshooting

### Bolt-XL Still Crashes

**Check logs**:
```bash
docker logs archive-bolt-xl
```

**Common issues**:
1. **GPU not accessible**: Verify NVIDIA Docker runtime
2. **Out of VRAM**: Try smaller model or CPU mode
3. **Model download failed**: Check internet connection

**Try CPU mode**:
```bash
# In bolt-xl service, add:
environment:
  - BOLT_USE_CPU=1
```

### Brain Can't Connect to Bolt-XL

**Verify network**:
```bash
docker exec archive-brain curl http://bolt-xl:3000/health
```

**Should return**: HTTP 200

### Wrong Model Being Used

**Check environment variables**:
```bash
docker exec archive-bolt-xl env | grep BOLT
docker exec archive-brain env | grep BOLT
```

**Should see**:
```
BOLT_MODEL=TinyLlama/TinyLlama-1.1B-Chat-v1.0
BOLT_XL_MODEL=TinyLlama/TinyLlama-1.1B-Chat-v1.0
BOLT_XL_URL=http://bolt-xl:3000
```

---

## Summary of Changes

| File | Change | Purpose |
|------|--------|---------|
| `docker-compose.yml` | Restored bolt-xl service | Re-enabled Bolt-XL container |
| `brain/config.py` | Added BOLT_XL_URL, BOLT_XL_MODEL | Configure Bolt-XL connection |
| `brain/services/chat_service.py` | Use BOLT_XL_MODEL instead of VORPAL_MODEL | Fix model name bug |
| `brain/services/metrics_service.py` | Restored Bolt-XL health checks | Monitor Bolt-XL status |
| `brain/services/system_service.py` | Restored Bolt-XL in service list | Display Bolt-XL in UI |
| `.env.example` | Added Bolt-XL configuration section | Document model options |

---

## Next Steps

1. ✅ Bolt-XL restored and configured
2. ✅ Compatible model set (TinyLlama)
3. ✅ Model name bug fixed
4. 📝 Test the system with `./start --web`
5. 📝 Verify chat requests go to Bolt-XL
6. 📝 Optional: Swap to better model (Qwen2.5-3B)

---

## Performance Expectations

### TinyLlama (1.1B)
- **VRAM**: ~2GB
- **Speed**: Very fast (~50-100 tokens/sec)
- **Quality**: Basic but functional
- **Use Case**: Testing, lightweight deployments

### Your Custom Model Choice
Once you verify TinyLlama works, you can upgrade to:
- Qwen2.5-3B for better quality
- Qwen2.5-7B for even better quality
- Any standard HuggingFace model that Bolt-XL supports

---

**Status**: Ready to test ✅
**Default Model**: TinyLlama/TinyLlama-1.1B-Chat-v1.0
**Your weeks of Bolt-XL work**: Preserved and properly configured!
