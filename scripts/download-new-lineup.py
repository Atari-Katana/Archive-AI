import os
import sys
from huggingface_hub import hf_hub_download, snapshot_download

MODELS_DIR = os.path.expanduser("~/Archive-AI/models")

def download_vorpal():
    print("Downloading Vorpal Model (Llama 3.2 3B Instruct GGUF)...")
    dest = os.path.join(MODELS_DIR, "vorpal")
    os.makedirs(dest, exist_ok=True)
    hf_hub_download(
        repo_id="bartowski/Llama-3.2-3B-Instruct-GGUF",
        filename="Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        local_dir=dest
    )

def download_bolt():
    print("Downloading Bolt-XL Model (Qwen3-Omni-30B-A3B-Instruct-AWQ)...")
    dest = os.path.join(MODELS_DIR, "bolt-xl")
    os.makedirs(dest, exist_ok=True)
    snapshot_download(
        repo_id="cyankiwi/Qwen3-Omni-30B-A3B-Instruct-AWQ-4bit",
        local_dir=dest,
        ignore_patterns=["*.msgpack", "*.h5"]
    )

def download_whisper():
    print("Downloading Whisper Model (small)...")
    dest = os.path.join(MODELS_DIR, "whisper")
    os.makedirs(dest, exist_ok=True)
    snapshot_download(
        repo_id="Systran/faster-whisper-small",
        local_dir=dest
    )

def download_xtts():
    print("Downloading XTTS-v2 Model...")
    dest = os.path.join(MODELS_DIR, "xtts")
    os.makedirs(dest, exist_ok=True)
    snapshot_download(
        repo_id="coqui/XTTS-v2",
        local_dir=dest
    )

if __name__ == "__main__":
    if len(sys.argv) < 2:
        download_vorpal()
        download_bolt()
        download_whisper()
        download_xtts()
    else:
        cmd = sys.argv[1]
        if cmd == "vorpal": download_vorpal()
        elif cmd == "bolt": download_bolt()
        elif cmd == "whisper": download_whisper()
        elif cmd == "xtts": download_xtts()