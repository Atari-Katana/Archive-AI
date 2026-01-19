# Persona System Guide

Archive-AI supports persona-driven chat experiences, including portrait + voice assets.

## Core components
- `brain/services/persona_manager.py` (and its Python + Rust counterparts) track persona metadata: name, instructions, portrait path, and voice sample path.
- The UI exposes a Persona dropdown, portrait badge, and voice-intro button (`ui/index.html`).
- Personas are persisted via the Brain’s `/personas` APIs and stored inside `ui/personas/` for reuse.

## Creating a Persona
1. Open the Persona Studio modal (gear icon in the UI) and fill in the `Name` + `Personality / Instructions` fields.
2. Upload a portrait image via the file uploader; it appears in the dropdown badge after saving.
3. Record a 6-second voice clip in the modal; it’s sent to `/personas/upload` with `type=audio`.
4. Saving the persona calls `POST /personas/` with the new metadata; once saved, it becomes selectable and its voice clip can be played with the headphone button.

## Custom voices
- Each persona can have a dedicated WAV clip used as a reference for XTTS voice cloning.
- In `voice/server.py`, the `/synthesize` endpoint accepts `reference_audio` to guide XTTS’s speaker adaptation.
- For new voice samples, place the file under `ui/personas/<persona>` and update the database entry (or re-upload via the UI). The Brain will automatically send it to XTTS when synthesizing.

## Advanced usage
- Use `scripts/test_persona_flow.py` (if present) to automate persona creation and voice playback.
- The `/personas/activate/{id}` endpoint switches the active persona; the Brain uses this when hitting `/voice/synthesize`.
- To alter persona behavior, edit their recorded instructions or update the `Personality` text; these instructions are prepended to the agent prompt.
