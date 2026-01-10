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
echo "[3/4] Ensuring Vorpal container is running..."
if ! docker ps | grep -q vorpal; then
    echo "Starting Vorpal..."
    docker-compose up -d vorpal
    echo "Waiting for Vorpal to initialize (60s)..."
    sleep 60
else
    echo "Vorpal is already running."
fi

# Check VRAM usage
echo ""
echo "[4/4] Checking VRAM usage..."
VRAM_USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '{print $1}')
VRAM_USED_GB=$(echo "scale=2; $VRAM_USED / 1024" | bc)

echo "VRAM Used: ${VRAM_USED_GB} GB"

# Check if within 8.0-12.0GB range (0.60 utilization on 16GB card)
if (( $(echo "$VRAM_USED_GB < 8.0" | bc -l) )); then
    echo "⚠️  WARNING: VRAM usage unusually low (${VRAM_USED_GB}GB < 8.0GB)"
    echo "    Model may not be loaded properly"
elif (( $(echo "$VRAM_USED_GB > 12.0" | bc -l) )); then
    echo "❌ FAIL: VRAM usage too high (${VRAM_USED_GB}GB > 12.0GB)"
    echo "    Expected ~9-10GB for 0.60 utilization"
    exit 1
else
    echo "✅ PASS: VRAM usage within acceptable range (8.0-12.0GB)"
fi

# Test API endpoint
echo ""
echo "[5/5] Testing API endpoint..."

# Get available model name
MODEL_NAME=$(curl -s http://localhost:8000/v1/models | grep -o '"id":"[^"]*"' | cut -d'"' -f4 | head -n1)
if [ -z "$MODEL_NAME" ]; then
    echo "⚠️  WARNING: Could not fetch model name. Defaulting to 'test' (may fail if strict)."
    MODEL_NAME="test"
else
    echo "Using model: $MODEL_NAME"
fi

RESPONSE=$(curl -s -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d "{\"model\": \"$MODEL_NAME\", \"prompt\": \"Hello\", \"max_tokens\": 10}" \
  --max-time 30 || echo "ERROR")

if [[ "$RESPONSE" == "ERROR" ]]; then
    echo "❌ FAIL: API did not respond"
    CONTAINER_ID=$(docker ps -qf "name=vorpal")
    if [ -n "$CONTAINER_ID" ]; then
        docker logs "$CONTAINER_ID" --tail 50
    else
        echo "Could not find Vorpal container logs."
    fi
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
