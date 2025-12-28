#!/bin/bash
# Goblin Engine Startup Script
# Starts llama.cpp server with configured GPU layers

set -e

echo "Starting Goblin Engine (llama.cpp server)..."

# Default model path (can be overridden by env var)
MODEL_PATH="${MODEL_PATH:-/models/model.gguf}"
N_GPU_LAYERS="${N_GPU_LAYERS:-38}"
CTX_SIZE="${CTX_SIZE:-8192}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8080}"

# Check if model exists
if [ ! -f "$MODEL_PATH" ]; then
    echo "ERROR: Model not found at $MODEL_PATH"
    echo "Please place a GGUF model in the models/goblin directory"
    echo "Expected: 14B Q4_K_M model (e.g., DeepSeek-R1-Distill-Qwen-14B)"
    exit 1
fi

echo "Model: $MODEL_PATH"
echo "GPU Layers: $N_GPU_LAYERS"
echo "Context Size: $CTX_SIZE"
echo "Host: $HOST:$PORT"

# Start llama.cpp server
# Note: Adjust n-gpu-layers if VRAM usage exceeds 10GB
/app/server \
    --model "$MODEL_PATH" \
    --host "$HOST" \
    --port "$PORT" \
    --ctx-size "$CTX_SIZE" \
    --n-gpu-layers "$N_GPU_LAYERS" \
    --threads 8 \
    --batch-size 512 \
    --ubatch-size 512 \
    --flash-attn \
    --cont-batching \
    --metrics
