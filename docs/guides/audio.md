# Audio System Guide

Archive-AI’s audio subsystem combines Faster-Whisper (STT) and Coqui XTTS-v2 for immersive voice I/O.

## Architecture
- `voice/server.py` starts FastAPI endpoints at `/health`, `/transcribe`, and `/synthesize`.
- The Brain proxies user requests via `brain/routes/voice.py` to keep voice features gated by `ENABLE_VOICE`.
- STT uses the Whisper model under `models/whisper`, while XTTS loads `models/xtts` (speaker statistics + models) for synthesis.

## Configuration
- Spread across `.env`:
  - `WHISPER_MODEL`, `WHISPER_DEVICE`, `WHISPER_COMPUTE_TYPE` control the STT engine.
  - `TTS_DEVICE` determines whether XTTS runs on GPU; leave default `cuda` for smooth audio.
  - Use `VOICE_PORT` and `VOICE_URL` to expose the service port (default `8005`).
- The UI config drawer exposes toggles that mirror `/config` settings (Enable Voice I/O, Async Memory, etc.).

## Running STT/TTS
1. **STT**: send audio (wav/mp3/flac) to `POST http://localhost:8080/voice/transcribe` via multipart form. The Brain forwards to the voice container, which returns `{ "text": "..." }`.
2. **TTS**: send text to `POST http://localhost:8080/voice/synthesize` with optional `reference_audio` (for persona cloning). The API proxies to XTTS. The response is `audio/wav`.
3. **Persona voice**: `brain/agents/persona_manager.py` can associate a `voice_sample_path` with each persona; the persona editor handles uploading the audio clip through `/personas/upload`.

## Troubleshooting
- If STT/TTS fail, check `docker-compose logs voice` for errors (model path, CUDA errors).
- Ensure the `voice` container mounts `./models/whisper` and `./models/xtts` (see `docker-compose.yml`). Missing files cause initialization errors.
- For GPU training, verify `NVIDIA_VISIBLE_DEVICES=0` and `runtime: nvidia` in `docker-compose.yml`.

## Custom Voices
1. Record or synthesize a 6-second clip and upload it via the Persona Studio modal in the UI or via the `/personas/upload` endpoint (type `audio`).
2. Associate the clip with a persona when creating/editing through the Persona Studio (the backend stores it under `ui/personas`).
3. XTTS clones are triggered by the Brain’s voice route, which sends the `reference_audio` file (if present) along with the new text to `/voice/synthesize`.
4. To swap TTS models, replace the files inside `models/xtts` and restart the `voice` container.
