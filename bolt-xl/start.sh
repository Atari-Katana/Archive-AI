#!/bin/bash
#
# Bolt-XL Startup Script
# High-performance LLM inference engine
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Default configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARGO_DIR="${SCRIPT_DIR}"
MODEL="TinyLlama/TinyLlama-1.1B-Chat-v1.0"
PORT=3000
DEVICE="cuda"
GPU_MODE=""
LOG_FILE=""
BACKGROUND=false
VERBOSE=false

# Help message
show_help() {
    cat << EOF
${BOLD}${CYAN}🚀 Bolt-XL - High-Performance LLM Inference Engine${NC}

${BOLD}Usage:${NC}
    $(basename "$0") [OPTIONS]

${BOLD}Options:${NC}
    -m, --model <MODEL>     Model to load (HuggingFace ID or local path)
                            [default: TinyLlama/TinyLlama-1.1B-Chat-v1.0]

    -p, --port <PORT>       HTTP server port [default: 3000]

    -d, --device <DEVICE>   Device to run on [choices: cuda, cpu]
                            [default: cuda]

    -b, --background        Run server in background

    -l, --log <FILE>        Log output to file

    -v, --verbose           Enable verbose output

    --build                 Build before running

    --benchmark             Run benchmark after startup

    --help                  Show this help message

    --version               Show version information

${BOLD}Environment Variables:${NC}
    BOLT_USE_CPU            Force CPU mode (1 = CPU only)
    BOLT_LOG_LEVEL          Log level (debug, info, warn, error)
    HF_HOME                 HuggingFace cache directory
    CUDA_VISIBLE_DEVICES    GPU selection (e.g., "0,1" for multi-GPU)

${BOLD}Examples:${NC}
    # Run with default settings (GPU mode)
    $(basename "$0")

    # Run with specific model on port 8080
    $(basename "$0") -m Qwen/Qwen2.5-7B-Instruct -p 8080

    # CPU mode (no GPU required)
    $(basename "$0") -d cpu

    # Run in background with logging
    $(basename "$0") -b -l bolt-xl.log

    # Build and run with verbose output
    $(basename "$0") --build -v

    # Multi-GPU selection
    CUDA_VISIBLE_DEVICES=0,1 $(basename "$0") -m meta-llama/Llama-2-7b-hf

${BOLD}API Endpoints:${NC}
    - GET  http://localhost:3000/v1/models
    - POST http://localhost:3000/v1/chat/completions
    - Web UI: http://localhost:3000/

${BOLD}Quick API Test:${NC}
    curl http://localhost:3000/v1/models
    curl -X POST http://localhost:3000/v1/chat/completions \\
        -H "Content-Type: application/json" \\
        -d '{"messages": [{"role": "user", "content": "Hello!"}], "stream": false}'

${BOLD}Supported Models:${NC}
    - LLaMA/LLaMA-2/LLaMA-3 and fine-tunes
    - Qwen/Qwen2/Qwen2.5 series
    - TinyLlama
    - Gemma
    - Any HuggingFace Transformers-compatible model

${BOLD}For more information:${NC}
    See README.md or visit https://github.com/Atari-Katana/Bolt-XL

EOF
}

# Show version
show_version() {
    cat << EOF
${BOLD}Bolt-XL${NC} v0.1.0
High-performance LLM inference engine written in Rust

${BOLD}Features:${NC}
    - Continuous Batching
    - Paged KV Cache Attention
    - AWQ/Marlin Quantization Support
    - OpenAI-Compatible API
    - GPU (CUDA) and CPU Modes

${BOLD}Build Information:${NC}
    - Rust Edition: 2021
    - ML Framework: candle 0.8.4
    - HTTP Server: axum 0.7

© 2024 Bolt-XL Contributors
MIT License
EOF
}

# Print colored status
print_status() {
    local status="$1"
    local message="$2"
    local color="$3"
    
    case "$status" in
        ok)     echo -e "${GREEN}[✓]${NC} $message" ;;
        info)   echo -e "${BLUE}[ℹ]${NC} $message" ;;
        warn)   echo -e "${YELLOW}[!]${NC} $message" ;;
        error)  echo -e "${RED}[✗]${NC} $message" ;;
        start)  echo -e "${CYAN}[→]${NC} $message" ;;
        *)      echo -e "$message" ;;
    esac
}

# Check system requirements
check_requirements() {
    print_status "info" "Checking system requirements..."
    
    # Check Rust
    if ! command -v cargo &> /dev/null; then
        print_status "error" "Rust/Cargo not found. Please install Rust first."
        print_status "info" "Install: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
        exit 1
    fi
    
    # Check CUDA if GPU mode
    if [[ "$DEVICE" == "cuda" ]]; then
        if ! command -v nvidia-smi &> /dev/null; then
            print_status "warn" "NVIDIA GPU not detected. Falling back to CPU mode."
            DEVICE="cpu"
        fi
        
        # Check CUDA toolkit
        if ! command -v nvcc &> /dev/null; then
            print_status "warn" "CUDA toolkit not found. Some optimizations may be disabled."
        fi
    fi
    
    print_status "ok" "System requirements check passed"
}

# Build the project
build_project() {
    print_status "start" "Building Bolt-XL..."
    
    cd "$CARGO_DIR"
    
    # Set build flags
    local build_cmd="cargo build --release"
    
    if [[ "$DEVICE" == "cpu" ]]; then
        export BOLT_USE_CPU=1
        build_cmd="$build_cmd --no-default-features --features cpu"
    fi
    
    if [[ "$VERBOSE" == "true" ]]; then
        build_cmd="$build_cmd -v"
    fi
    
    # Run build
    if $build_cmd; then
        print_status "ok" "Build successful"
    else
        print_status "error" "Build failed"
        exit 1
    fi
}

# Check if binary exists
check_binary() {
    local binary="$CARGO_DIR/target/release/bolt-xl"
    
    if [[ ! -f "$binary" ]]; then
        print_status "warn" "Binary not found. Building..."
        build_project
    fi
    
    if [[ ! -x "$binary" ]]; then
        chmod +x "$binary"
    fi
}

# Run the server
run_server() {
    print_status "start" "Starting Bolt-XL server..."
    print_status "info" "Model: $MODEL"
    print_status "info" "Device: $DEVICE"
    print_status "info" "Port: $PORT"
    
    # Build if needed
    check_binary
    
    # Prepare command
    local cmd="$CARGO_DIR/target/release/bolt-xl"
    local args=("$MODEL")
    
    if [[ "$PORT" != "3000" ]]; then
        args+=("--port" "$PORT")
    fi
    
    if [[ "$DEVICE" == "cpu" ]]; then
        args+=("--device" "cpu")
    fi
    
    # Set environment variables
    if [[ "$DEVICE" == "cpu" ]]; then
        export BOLT_USE_CPU=1
    fi
    
    # Logging
    if [[ -n "$LOG_FILE" ]]; then
        local log_dir=$(dirname "$LOG_FILE")
        if [[ ! -d "$log_dir" ]]; then
            mkdir -p "$log_dir"
        fi
        cmd="$cmd > \"$LOG_FILE\" 2>&1 &"
    elif [[ "$BACKGROUND" == "false" ]]; then
        # Add some visual separation
        echo ""
        echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════${NC}"
        echo -e "${BOLD}${CYAN}  🚀 Bolt-XL Server Starting${NC}"
        echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════${NC}"
        echo ""
    fi
    
    # Run the server
    cd "$CARGO_DIR"
    
    if [[ "$BACKGROUND" == "true" ]]; then
        eval "$cmd" "$args"
        local pid=$!
        print_status "ok" "Server started in background (PID: $pid)"
        print_status "info" "Log file: $LOG_FILE"
        print_status "info" "API: http://localhost:$PORT/v1/chat/completions"
        print_status "info" "Web UI: http://localhost:$PORT/"
        echo "$pid" > /tmp/bolt-xl.pid
    else
        eval "$cmd" "$args"
    fi
}

# Stop the server
stop_server() {
    if [[ -f /tmp/bolt-xl.pid ]]; then
        local pid=$(cat /tmp/bolt-xl.pid)
        if kill -0 "$pid" 2>/dev/null; then
            print_status "info" "Stopping server (PID: $pid)..."
            kill "$pid" 2>/dev/null || true
            rm -f /tmp/bolt-xl.pid
            print_status "ok" "Server stopped"
        else
            print_status "warn" "Server not running (stale PID file)"
            rm -f /tmp/bolt-xl.pid
        fi
    else
        # Try to find and kill any running instance
        local pids=$(pgrep -f "bolt-xl.*release" 2>/dev/null || true)
        if [[ -n "$pids" ]]; then
            print_status "info" "Stopping running instances..."
            echo "$pids" | xargs kill 2>/dev/null || true
            print_status "ok" "Server stopped"
        else
            print_status "info" "No running server found"
        fi
    fi
}

# Print system info
show_system_info() {
    echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${CYAN}  System Information${NC}"
    echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Rust version
    echo -e "${BOLD}Rust:${NC}        $(cargo --version 2>/dev/null | head -1 || echo 'Not installed')"
    
    # CUDA version
    if command -v nvidia-smi &> /dev/null; then
        echo -e "${BOLD}CUDA:${NC}        $(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null || echo 'N/A')"
        echo -e "${BOLD}GPU:${NC}         $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo 'N/A')"
        echo -e "${BOLD}VRAM:${NC}        $(nvidia-smi --query-gpu=memory.total --format=csv,noheader 2>/dev/null | tr -d ' ' || echo 'N/A')"
    else
        echo -e "${YELLOW}No NVIDIA GPU detected${NC}"
    fi
    
    # CPU info
    echo -e "${BOLD}CPU:${NC}         $(nproc) cores"
    
    # Memory
    echo -e "${BOLD}Memory:${NC}      $(free -h 2>/dev/null | grep Mem | awk '{print $2}' || echo 'N/A')"
    
    echo ""
}

# Benchmark function
run_benchmark() {
    print_status "info" "Running simple inference benchmark..."
    
    check_binary
    
    cd "$CARGO_DIR"
    
    # Run benchmark example
    if [[ "$DEVICE" == "cpu" ]]; then
        BOLT_USE_CPU=1 cargo run --release --example cpu_benchmark -- "$MODEL" 2>&1
    else
        cargo run --release --example simple_inference_bench -- "$MODEL" 2>&1
    fi
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -m|--model)
                MODEL="$2"
                shift 2
                ;;
            -p|--port)
                PORT="$2"
                shift 2
                ;;
            -d|--device)
                DEVICE="$2"
                shift 2
                ;;
            -b|--background)
                BACKGROUND=true
                shift
                ;;
            -l|--log)
                LOG_FILE="$2"
                shift 2
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            --build)
                BUILD_FIRST=true
                shift
                ;;
            --benchmark)
                RUN_BENCHMARK=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            --version)
                show_version
                exit 0
                ;;
            --info)
                show_system_info
                exit 0
                ;;
            --stop)
                stop_server
                exit 0
                ;;
            --restart)
                stop_server
                sleep 1
                run_server
                exit 0
                ;;
            -*)
                print_status "error" "Unknown option: $1"
                show_help
                exit 1
                ;;
            *)
                MODEL="$1"
                shift
                ;;
        esac
    done
}

# Main function
main() {
    # Parse arguments
    parse_args "$@"
    
    # Show banner
    echo -e "${BOLD}${CYAN}"
    cat << 'EOF'
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║   🚀  Bolt-XL  -  High-Performance LLM Inference Engine      ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    
    # Check requirements
    check_requirements
    
    # Build if requested
    if [[ "$BUILD_FIRST" == "true" ]]; then
        build_project
    fi
    
    # Run system info if verbose
    if [[ "$VERBOSE" == "true" ]]; then
        show_system_info
    fi
    
    # Run benchmark if requested
    if [[ "$RUN_BENCHMARK" == "true" ]]; then
        run_benchmark
        exit 0
    fi
    
    # Run the server
    run_server
}

# Run main
main "$@"
