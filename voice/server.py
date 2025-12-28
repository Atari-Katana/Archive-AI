"""
Voice Service - Faster-Whisper STT + F5-TTS
Speech-to-text using faster-whisper (CPU/GPU optimized).
Text-to-speech using F5-TTS (modern neural TTS).
Archive-AI v7.5 - Chunk 5.3
"""

import os
import tempfile
import logging
from pathlib import Path
from typing import Optional

import torch
import torchaudio
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from faster_whisper import WhisperModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="Archive-Voice", version="1.0.0")

# STT Model configuration
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")  # tiny, base, small, medium, large
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")  # cpu or cuda
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")  # int8, float16, float32

# TTS Configuration
TTS_DEVICE = os.getenv("TTS_DEVICE", "cpu")  # cpu or cuda
TTS_MODEL_CACHE = os.getenv("TTS_MODEL_CACHE", "/models/cache")

# Global model instances
whisper_model: Optional[WhisperModel] = None
f5_tts_model = None
f5_tts_available: bool = False


@app.on_event("startup")
async def startup():
    """Load models on startup"""
    global whisper_model, f5_tts_model, f5_tts_available

    # Load Whisper model for STT
    logger.info(f"[Voice] Loading Whisper model: {WHISPER_MODEL}")
    logger.info(f"[Voice] Device: {WHISPER_DEVICE}, Compute type: {WHISPER_COMPUTE_TYPE}")

    try:
        whisper_model = WhisperModel(
            WHISPER_MODEL,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE
        )
        logger.info("[Voice] ✅ Whisper model loaded successfully")
    except Exception as e:
        logger.error(f"[Voice] ❌ Failed to load Whisper model: {e}")
        raise

    # Load F5-TTS model
    logger.info(f"[Voice] Loading F5-TTS model (device: {TTS_DEVICE})")
    try:
        from f5_tts.api import F5TTS

        # Initialize F5-TTS with correct API for v1.1.15
        f5_tts_model = F5TTS(
            ckpt_file="",  # Will use default checkpoint
            vocab_file="",  # Will use default vocab
            device=TTS_DEVICE
        )
        f5_tts_available = True
        logger.info("[Voice] ✅ F5-TTS model loaded successfully")
    except Exception as e:
        logger.warning(f"[Voice] ⚠️ F5-TTS not available (STT-only mode): {e}")
        f5_tts_available = False


class TranscriptionResponse(BaseModel):
    """Transcription response model"""
    text: str
    language: Optional[str] = None
    duration: Optional[float] = None


class SynthesisRequest(BaseModel):
    """TTS synthesis request model"""
    text: str
    reference_audio: Optional[str] = None  # Path to reference audio for voice cloning
    reference_text: Optional[str] = None  # Transcript of reference audio


@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "healthy",
        "service": "archive-voice",
        "stt": {
            "model": WHISPER_MODEL,
            "device": WHISPER_DEVICE
        },
        "tts": {
            "available": f5_tts_available,
            "device": TTS_DEVICE if f5_tts_available else None
        }
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "stt": {
            "model_loaded": whisper_model is not None,
            "model_size": WHISPER_MODEL,
            "device": WHISPER_DEVICE,
            "compute_type": WHISPER_COMPUTE_TYPE
        },
        "tts": {
            "available": f5_tts_available,
            "model": "F5-TTS" if f5_tts_available else None,
            "device": TTS_DEVICE if f5_tts_available else None
        }
    }


@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(
    audio: UploadFile = File(...),
    language: Optional[str] = None
) -> TranscriptionResponse:
    """
    Transcribe audio file to text using Faster-Whisper.

    Args:
        audio: Audio file (wav, mp3, m4a, flac, ogg, etc.)
        language: Optional language code (e.g., 'en', 'es', 'fr')

    Returns:
        Transcription with detected language and duration
    """
    if whisper_model is None:
        raise HTTPException(status_code=503, detail="Whisper model not loaded")

    # Validate file type
    content_type = audio.content_type or ""
    if not (content_type.startswith("audio/") or
            audio.filename.endswith((".wav", ".mp3", ".m4a", ".ogg", ".flac", ".opus"))):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Must be audio file."
        )

    tmp_path = None
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(audio.filename).suffix) as tmp:
            content = await audio.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Transcribe audio
        segments, info = whisper_model.transcribe(
            tmp_path,
            language=language,
            beam_size=5,
            vad_filter=True,  # Voice activity detection
            vad_parameters=dict(min_silence_duration_ms=500)
        )

        # Combine all segments
        transcript_text = " ".join([segment.text.strip() for segment in segments])

        return TranscriptionResponse(
            text=transcript_text.strip(),
            language=info.language,
            duration=info.duration
        )

    except Exception as e:
        logger.error(f"[Voice] Transcription error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Transcription error: {str(e)}"
        )

    finally:
        # Clean up temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception as e:
                logger.warning(f"[Voice] Failed to delete temp file {tmp_path}: {e}")


@app.post("/synthesize")
async def synthesize(text: str = Form(...)) -> FileResponse:
    """
    Synthesize speech from text using F5-TTS.

    Args:
        text: Text to convert to speech

    Returns:
        WAV audio file
    """
    if not f5_tts_available or f5_tts_model is None:
        raise HTTPException(
            status_code=503,
            detail="TTS not available. F5-TTS model not loaded."
        )

    if not text or not text.strip():
        raise HTTPException(
            status_code=400,
            detail="Text cannot be empty"
        )

    output_path = None
    try:
        # Create temporary output file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            output_path = tmp.name

        # Synthesize speech with F5-TTS
        logger.info(f"[Voice] Synthesizing: '{text[:50]}...'")

        # Generate speech (F5-TTS returns audio tensor)
        audio_tensor, sample_rate = f5_tts_model.infer(
            gen_text=text,
            # Using default voice (can add ref_audio/ref_text for voice cloning)
        )

        # Save to WAV file
        torchaudio.save(
            output_path,
            audio_tensor.cpu(),
            sample_rate,
            format="wav"
        )

        logger.info(f"[Voice] ✅ Synthesis complete: {output_path}")

        # Return audio file
        return FileResponse(
            output_path,
            media_type="audio/wav",
            filename="speech.wav",
            headers={"Content-Disposition": "attachment; filename=speech.wav"}
        )

    except Exception as e:
        logger.error(f"[Voice] TTS synthesis error: {e}")

        # Clean up on error
        if output_path and os.path.exists(output_path):
            try:
                os.unlink(output_path)
            except Exception:
                pass

        raise HTTPException(
            status_code=500,
            detail=f"TTS synthesis error: {str(e)}"
        )


@app.post("/synthesize_with_reference")
async def synthesize_with_reference(
    text: str = Form(...),
    reference_audio: UploadFile = File(None),
    reference_text: str = Form(None)
) -> FileResponse:
    """
    Synthesize speech with voice cloning from reference audio.

    Args:
        text: Text to convert to speech
        reference_audio: Reference audio file for voice cloning (optional)
        reference_text: Transcript of reference audio (optional)

    Returns:
        WAV audio file with cloned voice
    """
    if not f5_tts_available or f5_tts_model is None:
        raise HTTPException(
            status_code=503,
            detail="TTS not available. F5-TTS model not loaded."
        )

    if not text or not text.strip():
        raise HTTPException(
            status_code=400,
            detail="Text cannot be empty"
        )

    ref_audio_path = None
    output_path = None

    try:
        # Save reference audio if provided
        if reference_audio:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                content = await reference_audio.read()
                tmp.write(content)
                ref_audio_path = tmp.name

        # Create temporary output file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            output_path = tmp.name

        # Synthesize with voice cloning
        logger.info(f"[Voice] Synthesizing with reference: '{text[:50]}...'")

        audio_tensor, sample_rate = f5_tts_model.infer(
            gen_text=text,
            ref_file=ref_audio_path,
            ref_text=reference_text
        )

        # Save to WAV file
        torchaudio.save(
            output_path,
            audio_tensor.cpu(),
            sample_rate,
            format="wav"
        )

        logger.info(f"[Voice] ✅ Voice cloning synthesis complete")

        return FileResponse(
            output_path,
            media_type="audio/wav",
            filename="speech_cloned.wav",
            headers={"Content-Disposition": "attachment; filename=speech_cloned.wav"}
        )

    except Exception as e:
        logger.error(f"[Voice] Voice cloning error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Voice cloning error: {str(e)}"
        )

    finally:
        # Clean up temp files
        if ref_audio_path and os.path.exists(ref_audio_path):
            try:
                os.unlink(ref_audio_path)
            except Exception:
                pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
