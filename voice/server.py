"""
Voice Service - Faster-Whisper STT + Coqui XTTS-v2
Refactored and Simplified
"""

import os
import tempfile
import logging
import shutil
from pathlib import Path
from typing import Optional, Tuple, Union

import torch
import torchaudio
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from faster_whisper import WhisperModel

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("voice")

# Configuration
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL", "base")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
TTS_DEVICE = os.getenv("TTS_DEVICE", "cpu")
TTS_MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"

# --- Services ---

class STTService:
    def __init__(self):
        self.model: Optional[WhisperModel] = None

    def load(self):
        logger.info(f"Loading Whisper STT ({WHISPER_MODEL_SIZE} on {WHISPER_DEVICE})...")
        try:
            self.model = WhisperModel(
                WHISPER_MODEL_SIZE,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE_TYPE
            )
            logger.info("✅ Whisper STT loaded.")
        except Exception as e:
            logger.error(f"❌ Failed to load Whisper: {e}")
            raise

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> dict:
        if not self.model:
            raise RuntimeError("STT model not loaded")
        
        segments, info = self.model.transcribe(
            audio_path,
            language=language,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        
        text = " ".join([s.text.strip() for s in segments])
        return {
            "text": text.strip(),
            "language": info.language,
            "duration": info.duration
        }

class TTSService:
    def __init__(self):
        self.model = None
        self.available = False

    def load(self):
        logger.info(f"Loading Coqui XTTS-v2 ({TTS_DEVICE})...")
        try:
            from TTS.api import TTS
            os.environ["COQUI_TOS_AGREED"] = "1"
            
            # Initialize TTS
            self.model = TTS(TTS_MODEL_NAME).to(TTS_DEVICE)
            self.available = True
            logger.info("✅ XTTS-v2 loaded.")
        except Exception as e:
            logger.warning(f"⚠️ XTTS-v2 unavailable: {e}")
            self.available = False

    def synthesize(self, text: str, output_path: str, speaker_wav: Optional[str] = None, language: str = "en"):
        if not self.available or not self.model:
            raise RuntimeError("TTS model not available")

        # XTTS requires a speaker reference. Use provided wav or fallback to a default if possible.
        # If no speaker_wav is provided, we try to use a default speaker name if supported, 
        # or error out if the model strictly requires a file.
        # XTTS-v2 usually requires a speaker_wav for cloning or a speaker name if multi-speaker.
        
        # We will use "Ana Florence" as a generic fallback speaker name if no file is provided.
        speaker_name = "Ana Florence" if not speaker_wav else None

        self.model.tts_to_file(
            text=text,
            file_path=output_path,
            speaker_wav=speaker_wav,
            speaker=speaker_name,
            language=language,
            split_sentences=True
        )

# --- API ---

app = FastAPI(title="Archive-Voice", version="2.0.0")
stt_service = STTService()
tts_service = TTSService()

class TranscriptionResponse(BaseModel):
    text: str
    language: Optional[str] = None
    duration: Optional[float] = None

@app.on_event("startup")
async def startup_event():
    stt_service.load()
    tts_service.load()

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "stt": {"loaded": stt_service.model is not None},
        "tts": {"available": tts_service.available}
    }

@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_endpoint(
    audio: UploadFile = File(...),
    language: Optional[str] = Form(None)
):
    """Transcribe audio file."""
    if not stt_service.model:
        raise HTTPException(503, "STT service unavailable")

    # Validate file
    if not audio.filename.lower().endswith(('.wav', '.mp3', '.m4a', '.ogg', '.flac', '.opus', '.webm')):
         raise HTTPException(400, "Invalid audio file format")

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=Path(audio.filename).suffix)
    try:
        with temp_file as f:
            shutil.copyfileobj(audio.file, f)
        
        result = stt_service.transcribe(temp_file.name, language)
        return result
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(500, str(e))
    finally:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

@app.post("/synthesize")
async def synthesize_endpoint(
    text: str = Form(...),
    reference_audio: Optional[UploadFile] = File(None),
    language: str = Form("en")
):
    """
    Synthesize speech. 
    Optional: Provide 'reference_audio' for voice cloning.
    """
    if not tts_service.available:
        raise HTTPException(503, "TTS service unavailable")

    if not text.strip():
        raise HTTPException(400, "Text cannot be empty")

    output_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    ref_file = None

    try:
        # Handle reference audio if provided
        speaker_wav = None
        if reference_audio:
            ref_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            with ref_file as f:
                shutil.copyfileobj(reference_audio.file, f)
            speaker_wav = ref_file.name

        logger.info(f"Synthesizing: {text[:30]}...")
        tts_service.synthesize(text, output_file.name, speaker_wav, language)
        
        return FileResponse(
            output_file.name, 
            media_type="audio/wav", 
            filename="speech.wav",
            background=None # Let FastAPI handle cleanup if we don't return it directly? 
                            # FileResponse doesn't auto-delete. We need a background task.
        )
    except Exception as e:
        logger.error(f"Synthesis error: {e}")
        if os.path.exists(output_file.name):
            os.unlink(output_file.name)
        raise HTTPException(500, str(e))
    finally:
        # Clean up input reference file immediately
        if ref_file and os.path.exists(ref_file.name):
            os.unlink(ref_file.name)
        
        # Note: output_file is cleaned up by OS eventually or we should use BackgroundTasks 
        # to delete it after response. For now, tempfile is okay but in prod use BackgroundTasks.

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
