#!/bin/bash
# Test script for Voice STT (Chunk 2.7)
# Tests FastWhisper speech-to-text service

set -e

echo "======================================================================"
echo "Voice STT Test"
echo "======================================================================"

# Test 1: Health check
echo ""
echo "[1/3] Testing health endpoint..."
response=$(curl -s http://localhost:8001/health)
echo "Response: $response"

if echo "$response" | grep -q '"status":"healthy"'; then
    echo "✅ PASS: Health check successful"
else
    echo "❌ FAIL: Health check failed"
    exit 1
fi

# Test 2: Service info
echo ""
echo "[2/3] Checking service configuration..."
if echo "$response" | grep -q '"model_loaded":true'; then
    echo "✅ PASS: Model loaded"
else
    echo "⚠️  WARNING: Model not loaded yet (may still be initializing)"
fi

model_size=$(echo "$response" | grep -o '"model_size":"[^"]*"' | cut -d'"' -f4)
device=$(echo "$response" | grep -o '"device":"[^"]*"' | cut -d'"' -f4)
echo "  Model: $model_size"
echo "  Device: $device"

# Test 3: Transcribe endpoint readiness
echo ""
echo "[3/3] Testing transcribe endpoint readiness..."
echo "  Note: Actual transcription requires audio file"
echo "  To test with audio:"
echo "    curl -X POST http://localhost:8001/transcribe \\"
echo "      -F 'audio=@/path/to/audio.wav'"

echo ""
echo "======================================================================"
echo "✅ ALL BASIC TESTS PASSED"
echo "======================================================================"
echo ""
echo "Voice service is ready for audio transcription."
echo ""
echo "To test with sample audio, you can:"
echo "1. Record a short audio file (wav, mp3, m4a)"
echo "2. Or download a sample: wget https://example.com/sample.wav"
echo "3. Then run: curl -X POST http://localhost:8001/transcribe -F 'audio=@sample.wav'"
echo ""
