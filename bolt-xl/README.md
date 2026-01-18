# Bolt-XL 🚀

A high-performance LLM inference engine written in Rust, featuring continuous batching, KV cache paged attention, and support for both GPU (CUDA) and CPU execution modes.

## Features

- **Continuous Batching**: Maximizes GPU utilization by batching requests dynamically
- **Paged KV Cache**: Memory-efficient attention using paged memory management (like vLLM)
- **AWQ Quantization**: 4-bit weight-only quantization support for reduced memory usage
- **Marlin Kernel**: Optimized INT4/INT8 quantization kernels for Ampere+ GPUs
- **OpenAI-Compatible API**: Drop-in replacement for OpenAI-compatible clients
- **Web UI**: Built-in web interface for testing

## Requirements

- **Rust** 1.70+ 
- **CUDA Toolkit** 12.0+ (for GPU mode)
- **NVIDIA GPU** with compute capability 8.0+ (Ampere, Ada, or Hopper)
- **16GB+ RAM** (32GB+ recommended for larger models)

## Quick Start

### Building

```bash
cd bolt-xl

# GPU mode (default - requires CUDA)
cargo build --release

# CPU mode (fallback for systems without GPU)
BOLT_USE_CPU=1 cargo build --release
```

### Running

```bash
# GPU mode (default)
./target/release/bolt-xl

# With specific model
./target/release/bolt-xl TinyLlama/TinyLlama-1.1B-Chat-v1.0

# Custom port
./target/release/bolt-xl --port 8080

# CPU mode
./target/release/bolt-xl --device cpu

# See all options
./target/release/bolt-xl --help
```

## Command-Line Options

```
High-performance LLM inference engine

Usage: bolt-xl [OPTIONS] [MODEL]

Arguments:
  [MODEL]          Model to load (HuggingFace ID or local path) [default: TinyLlama/TinyLlama-1.1B-Chat-v1.0]

Options:
  -d, --device <DEVICE>  Device to run on [possible values: cpu, cuda]
  -p, --port <PORT>      HTTP server port [default: 3000]
  -h, --help             Print help
  -V, --version          Print version
```

## API Endpoints

### List Models

```bash
curl http://localhost:3000/v1/models
```

Response:
```json
{
  "object": "list",
  "data": [
    {
      "id": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
      "object": "model",
      "created": 0,
      "owned_by": "user"
    }
  ]
}
```

### Chat Completions (OpenAI-compatible)

```bash
curl -X POST http://localhost:3000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Explain quantum computing in simple terms"}
    ],
    "stream": false,
    "max_tokens": 100
  }'
```

Response:
```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "Quantum computing is a new type of computing..."
      },
      "finish_reason": "stop"
    }
  ]
}
```

### Streaming Completions

```bash
curl -X POST http://localhost:3000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Write a story about AI"}],
    "stream": true
  }'
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BOLT_USE_CPU` | Force CPU-only mode | (not set) |
| `HF_HOME` | HuggingFace cache directory | `~/.cache/huggingface/hub` |

## Supported Models

Bolt-XL works with any HuggingFace Transformers-compatible model:

- **LLaMA/LLaMA-2/LLaMA-3** and fine-tunes
- **Qwen/Qwen2/Qwen2.5** 
- **TinyLlama**
- **Gemma**

### Recommended Models

| Model | Size | Memory | Speed |
|-------|------|--------|-------|
| TinyLlama-1.1B | 1.1B | ~2GB VRAM | Fast |
| Qwen2.5-0.5B | 500M | ~1GB VRAM | Very Fast |
| Llama-3.2-3B | 3B | ~6GB VRAM | Medium |
| Llama-2-7B | 7B | ~14GB VRAM | Slower |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Bolt-XL Engine                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Scheduler │  │   Engine    │  │   Model Executor    │  │
│  │             │  │             │  │                     │  │
│  │ - Batching  │─►│ - Requests  │─►│ - Forward Pass      │  │
│  │ - KV Cache  │  │ - Sampling  │  │ - CUDA/CPU kernels  │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│         │               │                    │               │
│         ▼               ▼                    ▼               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Web Server (Axum)                       │   │
│  │   /v1/models  │  /v1/chat/completions  │  Web UI   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

- **Scheduler**: Implements continuous batching with paged KV cache
- **Model Executor**: Loads models from safetensors, handles forward passes
- **CUDA Kernels**: Custom AWQ dequantization, Marlin INT4, fused sampling
- **HTTP Server**: OpenAI-compatible REST API with SSE streaming

## Quantization Support

Bolt-XL supports multiple quantization formats:

### AWQ (Active Weight Quantization)
```bash
./target/release/bolt-xl Qwen/Qwen2.5-7B-Instruct-AWQ
```

### Marlin (Optimized INT4/INT8)
Automatically detected for compatible models on Ampere+ GPUs.

## Performance Tuning

### For Maximum Throughput

```bash
# Use largest batch size possible
# Run on dedicated GPU with no display
# Use model with smaller context window
```

### For Low Latency

```bash
# Use smaller models (TinyLlama, Qwen2.5-0.5B)
# Reduce max_batch_size in config
# Enable CPU offload for large models
```

## Web Interface

Open `http://localhost:3000` in your browser to access the built-in web UI for testing the API.

## Troubleshooting

### CUDA Out of Memory

```bash
# Use smaller model
./target/release/bolt-xl TinyLlama/TinyLlama-1.1B-Chat-v1.0

# Or CPU mode
./target/release/bolt-xl --device cpu
```

### Model Download Fails

```bash
# Clear HuggingFace cache
rm -rf ~/.cache/huggingface/hub

# Set custom cache directory
export HF_HOME=/path/to/cache
./target/release/bolt-xl
```

### GPU Not Detected

```bash
# Check CUDA installation
nvidia-smi

# Verify CUDA toolkit
nvcc --version

# Force CPU mode
./target/release/bolt-xl --device cpu
```

## Building from Source

```bash
# Clone repository
git clone https://github.com/Atari-Katana/Bolt-XL.git
cd Bolt-XL/bolt-xl

# Build with CUDA (default)
cargo build --release

# Build for CPU only
BOLT_USE_CPU=1 cargo build --release

# Run tests
cargo test
```

## Benchmarking

```bash
# Simple inference benchmark
cargo run --release --example simple_inference_bench

# CPU benchmark
cargo run --release --example cpu_benchmark

# Throughput benchmark
cargo bench
```

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and benchmarks
5. Submit a pull request

## Acknowledgments

- [candle](https://github.com/huggingface/candle) - Rust ML framework
- [vLLM](https://github.com/vllm-project/vllm) - Inspiration for paged attention
- [AWQ](https://github.com/mit-han-lab/awq) - Activation-aware quantization
- [Marlin](https://github.com/IST-DASLab/marlin) - Optimized INT4 kernels
