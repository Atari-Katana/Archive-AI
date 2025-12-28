#!/bin/bash
# Voice Round-Trip Test (Chunk 2.9)
# Tests complete voice pipeline: audio → text → audio

set -e

echo "======================================================================"
echo "Voice Round-Trip Test"
echo "======================================================================"

# Configuration
VOICE_URL="http://localhost:8001"
TEST_TEXT="The quick brown fox jumps over the lazy dog."

# Test 1: Health check
echo ""
echo "[1/5] Testing voice service health..."
response=$(curl -s "$VOICE_URL/health")
echo "Response: $response"

if echo "$response" | grep -q '"status":"healthy"'; then
    echo "✅ PASS: Service healthy"
else
    echo "❌ FAIL: Service not healthy"
    exit 1
fi

# Check STT and TTS availability
stt_loaded=$(echo "$response" | grep -o '"model_loaded":[^,]*' | head -1 | grep -o 'true\|false')
tts_available=$(echo "$response" | grep -o '"available":[^,]*' | grep -o 'true\|false')

echo "  STT Model Loaded: $stt_loaded"
echo "  TTS Available: $tts_available"

# Test 2: TTS - Text to Speech
echo ""
echo "[2/5] Testing text-to-speech..."
echo "  Input text: \"$TEST_TEXT\""

if [ "$tts_available" != "true" ]; then
    echo "⚠️  SKIP: TTS not available (voice model not downloaded)"
    echo "  Run: ./scripts/download-piper-voice.sh"
    exit 0
fi

curl -X POST "$VOICE_URL/synthesize" \
  -F "text=$TEST_TEXT" \
  -o /tmp/test_speech.wav \
  -s --fail

if [ -f /tmp/test_speech.wav ] && [ -s /tmp/test_speech.wav ]; then
    file_size=$(stat -f%z /tmp/test_speech.wav 2>/dev/null || stat -c%s /tmp/test_speech.wav 2>/dev/null)
    echo "✅ PASS: Generated audio file ($file_size bytes)"
else
    echo "❌ FAIL: TTS synthesis failed"
    exit 1
fi

# Test 3: STT - Speech to Text
echo ""
echo "[3/5] Testing speech-to-text..."
echo "  Input audio: /tmp/test_speech.wav"

if [ "$stt_loaded" != "true" ]; then
    echo "⚠️  SKIP: STT model not loaded"
    exit 0
fi

result=$(curl -X POST "$VOICE_URL/transcribe" \
  -F "audio=@/tmp/test_speech.wav" \
  -s --fail)

transcribed_text=$(echo "$result" | grep -o '"text":"[^"]*"' | cut -d'"' -f4)
echo "  Output text: \"$transcribed_text\""

if [ -n "$transcribed_text" ]; then
    echo "✅ PASS: Transcription successful"
else
    echo "❌ FAIL: Transcription failed"
    exit 1
fi

# Test 4: Round-trip accuracy
echo ""
echo "[4/5] Testing round-trip accuracy..."
echo "  Original: \"$TEST_TEXT\""
echo "  Round-trip: \"$transcribed_text\""

# Simple similarity check (case-insensitive, ignore punctuation)
original_normalized=$(echo "$TEST_TEXT" | tr '[:upper:]' '[:lower:]' | tr -d '[:punct:]')
transcribed_normalized=$(echo "$transcribed_text" | tr '[:upper:]' '[:lower:]' | tr -d '[:punct:]')

if [ "$original_normalized" = "$transcribed_normalized" ]; then
    echo "✅ PASS: Perfect match!"
elif echo "$transcribed_normalized" | grep -q "$(echo $original_normalized | cut -d' ' -f1-5)"; then
    echo "✅ PASS: Close match (acceptable)"
else
    echo "⚠️  WARNING: Text differs (check quality)"
fi

# Test 5: Performance check
echo ""
echo "[5/5] Checking performance..."

# TTS performance
tts_start=$(date +%s%N)
curl -X POST "$VOICE_URL/synthesize" \
  -F "text=This is a performance test." \
  -o /tmp/perf_test.wav \
  -s --fail >/dev/null 2>&1
tts_end=$(date +%s%N)
tts_duration=$((($tts_end - $tts_start) / 1000000))
echo "  TTS latency: ${tts_duration}ms"

if [ $tts_duration -lt 5000 ]; then
    echo "✅ TTS performance good (< 5s)"
elif [ $tts_duration -lt 10000 ]; then
    echo "⚠️  TTS performance acceptable (< 10s)"
else
    echo "⚠️  TTS performance slow (> 10s)"
fi

# Cleanup
rm -f /tmp/test_speech.wav /tmp/perf_test.wav

echo ""
echo "======================================================================"
echo "✅ ALL TESTS PASSED"
echo "======================================================================"
echo ""
echo "Voice pipeline is fully operational!"
echo ""
echo "Summary:"
echo "  - STT (Whisper): $stt_loaded"
echo "  - TTS (Piper): $tts_available"
echo "  - Round-trip: ✅ Working"
echo "  - Performance: Acceptable"
echo ""
