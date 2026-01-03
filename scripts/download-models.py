#!/usr/bin/env python3
"""
Automated model downloader with progress tracking.
Handles Goblin GGUF and Vorpal AWQ models with resume capability.
"""
import os
import sys
import hashlib
from pathlib import Path
from typing import Dict, Optional, Tuple

try:
    import requests
    from tqdm import tqdm
except ImportError:
    print("ERROR: Required packages not installed")
    print("Run: pip install requests tqdm")
    sys.exit(1)


# Model registry with URLs and checksums
MODELS: Dict[str, Dict[str, any]] = {
    "goblin-7b": {
        "name": "DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf",
        "url": "https://huggingface.co/unsloth/DeepSeek-R1-Distill-Qwen-7B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf",
        "path": "models/goblin",
        "size": 8_400_000_000,  # 8.4GB approximate
        "sha256": None,  # Optional: add checksum when available
        "description": "7B reasoning model (Q4_K_M quantization)",
    },
    "goblin-14b": {
        "name": "DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf",
        "url": "https://huggingface.co/unsloth/DeepSeek-R1-Distill-Qwen-14B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf",
        "path": "models/goblin",
        "size": 15_000_000_000,  # 15GB approximate
        "sha256": None,
        "description": "14B reasoning model (Q4_K_M quantization)",
    },
}


def format_bytes(bytes_num: int) -> str:
    """Format bytes into human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_num < 1024.0:
            return f"{bytes_num:.1f}{unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.1f}PB"


def download_file(url: str, dest_path: Path, expected_size: int) -> bool:
    """
    Download file with progress bar and resumption support.

    Args:
        url: URL to download from
        dest_path: Destination file path
        expected_size: Expected file size in bytes

    Returns:
        True if download successful, False otherwise
    """
    # Create parent directory
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if already downloaded
    if dest_path.exists():
        existing_size = dest_path.stat().st_size

        if existing_size == expected_size:
            print(f"✓ {dest_path.name} already downloaded ({format_bytes(existing_size)})")
            return True
        elif existing_size > expected_size:
            print(f"⚠ {dest_path.name} is larger than expected, re-downloading")
            dest_path.unlink()
            existing_size = 0
        else:
            print(f"⚠ {dest_path.name} incomplete ({format_bytes(existing_size)}/{format_bytes(expected_size)}), resuming")
    else:
        existing_size = 0

    # Set up request headers for resume
    headers = {}
    mode = 'wb'

    if existing_size > 0:
        headers['Range'] = f'bytes={existing_size}-'
        mode = 'ab'

    try:
        # Make request
        print(f"📥 Downloading {dest_path.name}...")
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()

        # Get total size
        content_length = response.headers.get('content-length')
        if content_length:
            total_size = int(content_length) + existing_size
        else:
            total_size = expected_size

        # Download with progress bar
        with open(dest_path, mode) as f:
            with tqdm(
                total=total_size,
                initial=existing_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                desc=dest_path.name,
                ncols=80
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))

        # Verify final size
        final_size = dest_path.stat().st_size
        if abs(final_size - expected_size) > 1024:  # Allow 1KB tolerance
            print(f"⚠ Size mismatch: expected {format_bytes(expected_size)}, got {format_bytes(final_size)}")
            return False

        return True

    except requests.exceptions.RequestException as e:
        print(f"✗ Download failed: {e}")
        return False
    except KeyboardInterrupt:
        print(f"\n⚠ Download interrupted. Run again to resume.")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def verify_checksum(file_path: Path, expected_sha256: Optional[str]) -> bool:
    """
    Verify file integrity with SHA256 checksum.

    Args:
        file_path: Path to file to verify
        expected_sha256: Expected SHA256 hash (hex string)

    Returns:
        True if checksum matches or no checksum provided, False otherwise
    """
    if not expected_sha256:
        print("⚠ No checksum provided, skipping verification")
        return True

    print(f"🔍 Verifying checksum...")

    try:
        sha256_hash = hashlib.sha256()

        with open(file_path, "rb") as f:
            # Read in chunks for large files
            for byte_block in iter(lambda: f.read(4096 * 1024), b""):  # 4MB chunks
                sha256_hash.update(byte_block)

        actual = sha256_hash.hexdigest()

        if actual != expected_sha256:
            print(f"✗ Checksum mismatch!")
            print(f"   Expected: {expected_sha256}")
            print(f"   Got:      {actual}")
            return False

        print(f"✓ Checksum verified: {actual}")
        return True

    except Exception as e:
        print(f"✗ Checksum verification failed: {e}")
        return False


def download_model(model_key: str, force: bool = False) -> bool:
    """
    Download a specific model.

    Args:
        model_key: Model identifier from MODELS dict
        force: If True, re-download even if file exists

    Returns:
        True if successful, False otherwise
    """
    if model_key not in MODELS:
        print(f"✗ Unknown model: {model_key}")
        print(f"   Available models: {', '.join(MODELS.keys())}")
        return False

    model = MODELS[model_key]
    dest_path = Path(model["path"]) / model["name"]

    # Check if already complete
    if dest_path.exists() and not force:
        existing_size = dest_path.stat().st_size
        if existing_size == model["size"]:
            print(f"✓ {model_key} already downloaded")
            return True

    print(f"\n{'='*60}")
    print(f"📦 Model: {model_key}")
    print(f"   Name: {model['name']}")
    print(f"   Description: {model['description']}")
    print(f"   Size: {format_bytes(model['size'])}")
    print(f"   Destination: {dest_path}")
    print(f"{'='*60}\n")

    # Download
    success = download_file(model["url"], dest_path, model["size"])

    if not success:
        return False

    # Verify checksum if provided
    if model.get("sha256"):
        success = verify_checksum(dest_path, model["sha256"])
        if not success:
            print(f"⚠ Checksum verification failed. File may be corrupted.")
            return False

    print(f"\n✓ {model_key} downloaded successfully!\n")
    return True


def list_models() -> None:
    """List all available models."""
    print("\n📋 Available Models:\n")
    print(f"{'Model ID':<15} {'Size':<10} {'Description'}")
    print("-" * 70)

    for key, model in MODELS.items():
        size_str = format_bytes(model['size'])
        desc = model.get('description', 'No description')
        print(f"{key:<15} {size_str:<10} {desc}")

    print()


def main() -> int:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Download Archive-AI model files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download default model for dual-engine mode
  %(prog)s

  # Download specific model
  %(prog)s --model goblin-7b

  # Re-download even if file exists
  %(prog)s --model goblin-7b --force

  # List available models
  %(prog)s --list
        """
    )

    parser.add_argument(
        '--model',
        choices=list(MODELS.keys()) + ['all'],
        default='goblin-7b',
        help='Model to download (default: goblin-7b for dual-engine mode)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Re-download even if file exists'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List available models and exit'
    )

    args = parser.parse_args()

    # List models
    if args.list:
        list_models()
        return 0

    # Determine which models to download
    if args.model == 'all':
        models_to_download = list(MODELS.keys())
        print("📦 Downloading all models...")
    else:
        models_to_download = [args.model]

    # Download models
    success_count = 0
    total_count = len(models_to_download)

    for model_key in models_to_download:
        if download_model(model_key, force=args.force):
            success_count += 1
        else:
            print(f"⚠ Failed to download {model_key}\n")

    # Summary
    print(f"\n{'='*60}")
    print(f"Downloaded {success_count}/{total_count} models")

    if success_count == total_count:
        print("✓ All models ready!")
        print(f"{'='*60}\n")
        return 0
    else:
        print("✗ Some downloads failed")
        print(f"{'='*60}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
