# Vorpal Engine Dockerfile
# vLLM-based inference with strict VRAM limits

FROM vllm/vllm-openai:latest

# Set working directory
WORKDIR /app

# Copy configuration
COPY config.yaml /app/config.yaml

# Environment variables
ENV VLLM_ATTENTION_BACKEND=FLASH_ATTN
ENV CUDA_VISIBLE_DEVICES=0

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start vLLM server
# Using Qwen2.5-3B-Instruct (needs ~6.4GB VRAM total)
# Entrypoint is already "vllm serve", just provide model and options
CMD ["Qwen/Qwen2.5-3B-Instruct", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--gpu-memory-utilization", "0.5", \
     "--max-model-len", "8192"]
