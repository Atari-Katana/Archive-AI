# Archive-AI Models Directory

This directory contains AI models used by Archive-AI. Most models auto-download on first use.

---

## Directory Structure

```
models/
├── vorpal/          # Vorpal (Speed Engine) - MANUAL DOWNLOAD REQUIRED
├── whisper/         # Faster-Whisper models - Auto-download
└── f5-tts/          # F5-TTS models - Auto-download
```

---

## Vorpal Model (Required - Manual Download)

**Model:** Llama-3-8B-Instruct (EXL2 4.0bpw)
**Location:** `./models/vorpal/`
**Size:** ~3GB
**VRAM:** ~3.0GB

### Download Instructions:

1. Visit: https://huggingface.co/turboderp
2. Download: Llama-3-8B-Instruct (EXL2 4.0bpw quantization)
3. Place in: `./models/vorpal/`

**Required files:**
- config.json
- tokenizer files
- model shards (*.safetensors or *.exl2)

---

## Whisper Models (Auto-download)

**Location:** `./models/whisper/`
**Engine:** Faster-Whisper
**Auto-download:** Yes (on first use)

### Available Models:

| Model | Size | Accuracy | Speed |
|-------|------|----------|-------|
| tiny | 39M | Low | Fast |
| base | 74M | Good | Fast |
| small | 244M | Better | Medium |
| medium | 769M | Very Good | Slow |
| large | 1550M | Best | Slowest |

**Default:** `base` (configured in .env)
**Configuration:** Set `WHISPER_MODEL=<model>` in .env

---

## F5-TTS Models (Auto-download)

**Location:** `./models/f5-tts/`
**Engine:** F5-TTS
**Auto-download:** Yes (on first use)

### Models:
- F5-TTS base model (~1.3GB)
- Vocos vocoder (~52MB)

**Configuration:** Set `TTS_DEVICE=cpu` or `TTS_DEVICE=cuda` in .env

---

## Storage Requirements

| Component | Size | Auto-download |
|-----------|------|---------------|
| Vorpal | ~3GB | No (manual) |
| Whisper (base) | ~150MB | Yes |
| F5-TTS | ~1.3GB | Yes |
| **Total** | **~4.5GB** | - |

**Note:** Whisper and F5-TTS models download automatically on first API call.

---

## Notes

- **Git Ignore:** Model files are excluded from git (too large for GitHub)
- **First Run:** Initial model download may take 5-10 minutes
- **GPU Required:** Vorpal requires NVIDIA GPU with 16GB VRAM
- **CPU Option:** Whisper and F5-TTS can run on CPU (slower)
- **Caching:** Downloaded models are cached in `models/` directory

---

## Troubleshooting

### Vorpal won't start
- **Cause:** Model not found in `./models/vorpal/`
- **Fix:** Download Llama-3-8B-Instruct (EXL2 4.0bpw) and place in directory

### Slow initial voice response
- **Cause:** Models downloading on first use
- **Fix:** Wait for download to complete (5-10 minutes)

### Out of disk space
- **Cause:** Models require ~5GB total
- **Fix:** Ensure 10GB+ free disk space before starting

---

For more information, see:
- [DEPLOYMENT.md](../DEPLOYMENT.md) - Model setup instructions
- [README.md](../README.md) - Quick start guide
