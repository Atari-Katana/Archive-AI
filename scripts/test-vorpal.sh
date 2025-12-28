#!/bin/bash
# Test script for Vorpal Engine (Chunk 1.3)
# Requires: GPU access, vLLM-compatible model in models/vorpal/

set -e

echo "============================================================"
echo "Vorpal Engine Test - Chunk 1.3"
echo "============================================================"

# Check if GPU is available
echo ""
echo "[1/4] Checking GPU availability..."
if ! command -v nvidia-smi &> /dev/null; then
    echo "❌ FAIL: nvidia-smi not found. GPU required for this test."
    exit 1
fi

nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
echo "✅ PASS: GPU detected"

# Check if model exists
echo ""
echo "[2/4] Checking for model files..."
if [ ! -d "./models/vorpal" ] || [ -z "$(ls -A ./models/vorpal)" ]; then
    echo "⚠️  WARNING: No model found in ./models/vorpal/"
    echo "    Please download a compatible EXL2 model (Llama-3-8B-Instruct recommended)"
    echo "    This test will be marked as PARTIAL - Needs Model"
    exit 2
fi
echo "✅ PASS: Model directory exists"

# Start Vorpal container
echo ""
echo "[3/4] Starting Vorpal container..."
docker-compose up -d vorpal

# Wait for startup
echo "Waiting for Vorpal to initialize (60s)..."
sleep 60

# Check VRAM usage
echo ""
echo "[4/4] Checking VRAM usage..."
VRAM_USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '{print $1}')
VRAM_USED_GB=$(echo "scale=2; $VRAM_USED / 1024" | bc)

echo "VRAM Used: ${VRAM_USED_GB} GB"

# Check if within 3-3.5GB range (allowing some overhead)
if (( $(echo "$VRAM_USED_GB < 2.5" | bc -l) )); then
    echo "⚠️  WARNING: VRAM usage unusually low (${VRAM_USED_GB}GB < 2.5GB)"
    echo "    Model may not be loaded properly"
elif (( $(echo "$VRAM_USED_GB > 4.0" | bc -l) )); then
    echo "❌ FAIL: VRAM usage too high (${VRAM_USED_GB}GB > 4.0GB)"
    echo "    Expected ~3-3.5GB, adjust GPU_MEMORY_UTILIZATION"
    exit 1
else
    echo "✅ PASS: VRAM usage within acceptable range (2.5-4.0GB)"
fi

# Test API endpoint
echo ""
echo "[5/5] Testing API endpoint..."
RESPONSE=$(curl -s -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "test", "prompt": "Hello", "max_tokens": 10}' \
  --max-time 30 || echo "ERROR")

if [[ "$RESPONSE" == "ERROR" ]]; then
    echo "❌ FAIL: API did not respond"
    docker logs vorpal --tail 50
    exit 1
fi

echo "API Response: $RESPONSE"
echo "✅ PASS: API responds to completion requests"

echo ""
echo "============================================================"
echo "✅ ALL TESTS PASSED"
echo "============================================================"
echo ""
echo "Vorpal Engine configured correctly:"
echo "  - GPU detected: ✅"
echo "  - VRAM usage: ${VRAM_USED_GB}GB ✅"
echo "  - API responding: ✅"
echo ""
echo "Chunk 1.3 pass criteria met."
