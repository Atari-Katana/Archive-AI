from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from schemas.voice import VoiceTranscriptionResponse, VoiceSynthesisRequest
from services.persona_manager import personas_manager
from config import config
import httpx
import logging
import os

logger = logging.getLogger("brain.voice")
router = APIRouter(prefix="/voice", tags=["voice"])

@router.post("/transcribe", response_model=VoiceTranscriptionResponse)
async def transcribe_audio(request: Request):
    """
    Transcribe audio to text using Faster-Whisper.
    """
    if not config.ENABLE_VOICE:
        raise HTTPException(status_code=503, detail="Voice features disabled")

    try:
        form_data = await request.form()
        audio_file = form_data.get("audio")
        if not audio_file:
            raise HTTPException(status_code=400, detail="No audio file provided")

        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {"audio": (audio_file.filename, await audio_file.read(), audio_file.content_type)}
            response = await client.post(f"{config.VOICE_URL}/transcribe", files=files)
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            
            return response.json()

    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/synthesize")
async def synthesize_speech(request: VoiceSynthesisRequest):
    """
    Synthesize speech from text using XTTS-v2.
    """
    if not config.ENABLE_VOICE:
        raise HTTPException(status_code=503, detail="Voice features disabled")
    
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        active_persona = personas_manager.get_active_persona()
        files = None
        data = {"text": request.text}
        
        # Check for persona voice sample
        if active_persona and active_persona.voice_sample_path:
            full_path = os.path.join("ui", active_persona.voice_sample_path)
            if os.path.exists(full_path):
                with open(full_path, "rb") as f:
                    # 'reference_audio' field name matches the new Voice API
                    files = {"reference_audio": (os.path.basename(full_path), f.read(), "audio/wav")}

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Single endpoint /synthesize handles both cases now
            response = await client.post(
                f"{config.VOICE_URL}/synthesize",
                data=data,
                files=files
            )

            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)

            return Response(
                content=response.content,
                media_type="audio/wav",
                headers={"Content-Disposition": "attachment; filename=speech.wav"}
            )

    except Exception as e:
        logger.error(f"Synthesis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))