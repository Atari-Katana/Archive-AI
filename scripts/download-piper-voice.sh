#!/bin/bash
# Download Piper TTS voice model
# Default: en_US-lessac-medium (good quality, CPU-friendly)

set -e

MODELS_DIR="./models/piper"
VOICE="en_US-lessac-medium"
BASE_URL="https://github.com/rhasspy/piper/releases/download/v1.2.0"

echo "======================================================================"
echo "Piper TTS Voice Model Download"
echo "======================================================================"

# Create models directory
mkdir -p "$MODELS_DIR"

# Download voice model (.onnx file)
echo ""
echo "Downloading $VOICE voice model..."
wget -O "$MODELS_DIR/${VOICE}.onnx" \
  "$BASE_URL/${VOICE}.onnx" \
  --quiet --show-progress

# Download voice model config (.json file)
echo ""
echo "Downloading $VOICE voice config..."
wget -O "$MODELS_DIR/${VOICE}.onnx.json" \
  "$BASE_URL/${VOICE}.onnx.json" \
  --quiet --show-progress

echo ""
echo "======================================================================"
echo "✅ Piper voice model downloaded successfully"
echo "======================================================================"
echo ""
echo "Model: $VOICE"
echo "Location: $MODELS_DIR"
echo "Files:"
echo "  - ${VOICE}.onnx"
echo "  - ${VOICE}.onnx.json"
echo ""
echo "The voice service will use this model for text-to-speech."
echo ""
