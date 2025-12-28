#!/bin/bash
# Test script for Goblin Engine (Chunk 1.4)
# Requires: GPU access, GGUF model in models/goblin/

set -e

echo "============================================================"
echo "Goblin Engine Test - Chunk 1.4"
echo "============================================================"

# Check if GPU is available
echo ""
echo "[1/5] Checking GPU availability..."
if ! command -v nvidia-smi &> /dev/null; then
    echo "❌ FAIL: nvidia-smi not found. GPU required for this test."
    exit 1
fi

nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
echo "✅ PASS: GPU detected"

# Check if model exists
echo ""
echo "[2/5] Checking for model files..."
if [ ! -f "./models/goblin/model.gguf" ]; then
    echo "⚠️  WARNING: No model found at ./models/goblin/model.gguf"
    echo "    Please download a compatible GGUF model (14B Q4_K_M recommended)"
    echo "    Examples: DeepSeek-R1-Distill-Qwen-14B, Qwen-2.5-Coder-14B"
    echo "    This test will be marked as PARTIAL - Needs Model"
    exit 2
fi
echo "✅ PASS: Model file exists"

# Make start script executable
chmod +x goblin/start.sh

# Start Goblin container
echo ""
echo "[3/5] Starting Goblin container..."
docker-compose up -d goblin

# Wait for startup
echo "Waiting for Goblin to initialize (90s - model loading takes time)..."
sleep 90

# Check VRAM usage
echo ""
echo "[4/5] Checking VRAM usage..."
VRAM_USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '{print $1}')
VRAM_USED_GB=$(echo "scale=2; $VRAM_USED / 1024" | bc)

echo "Total VRAM Used: ${VRAM_USED_GB} GB"

# Check if within 8-14GB range (Goblin alone should be ~8-10GB)
if (( $(echo "$VRAM_USED_GB < 7.0" | bc -l) )); then
    echo "⚠️  WARNING: VRAM usage unusually low (${VRAM_USED_GB}GB < 7.0GB)"
    echo "    Model may not be loaded properly or n_gpu_layers too low"
elif (( $(echo "$VRAM_USED_GB > 14.0" | bc -l) )); then
    echo "❌ FAIL: VRAM usage too high (${VRAM_USED_GB}GB > 14.0GB)"
    echo "    Expected ~8-10GB for Goblin, reduce n_gpu_layers"
    exit 1
else
    echo "✅ PASS: VRAM usage within acceptable range (7-14GB)"
fi

# Test API endpoint
echo ""
echo "[5/5] Testing API endpoint..."
RESPONSE=$(curl -s -X POST http://localhost:8080/completion \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Test", "n_predict": 10}' \
  --max-time 60 || echo "ERROR")

if [[ "$RESPONSE" == "ERROR" ]]; then
    echo "❌ FAIL: API did not respond"
    docker logs goblin --tail 100
    exit 1
fi

echo "API Response (truncated): ${RESPONSE:0:200}..."
echo "✅ PASS: API responds to completion requests"

# Combined VRAM check (if Vorpal also running)
if docker ps | grep -q vorpal; then
    echo ""
    echo "[BONUS] Checking combined VRAM (Vorpal + Goblin)..."
    TOTAL_VRAM=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '{print $1}')
    TOTAL_VRAM_GB=$(echo "scale=2; $TOTAL_VRAM / 1024" | bc)
    
    echo "Combined VRAM: ${TOTAL_VRAM_GB} GB"
    
    if (( $(echo "$TOTAL_VRAM_GB > 14.0" | bc -l) )); then
        echo "⚠️  WARNING: Combined VRAM > 14GB, leaving < 2GB buffer"
        echo "    Consider reducing n_gpu_layers for Goblin"
    else
        echo "✅ PASS: Combined VRAM within budget (< 14GB)"
    fi
fi

echo ""
echo "============================================================"
echo "✅ ALL TESTS PASSED"
echo "============================================================"
echo ""
echo "Goblin Engine configured correctly:"
echo "  - GPU detected: ✅"
echo "  - VRAM usage: ${VRAM_USED_GB}GB ✅"
echo "  - API responding: ✅"
echo ""
echo "Chunk 1.4 pass criteria met."
