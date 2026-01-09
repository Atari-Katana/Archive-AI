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
    Transcribe audio to text using Faster-Whisper STT (Chunk 5.3).
    """
    if not config.ENABLE_VOICE:
        raise HTTPException(
            status_code=503,
            detail="Voice features are disabled. Set ENABLE_VOICE=true to enable."
        )

    try:
        # Get the form data from the request
        form_data = await request.form()
        audio_file = form_data.get("audio")

        if not audio_file:
            raise HTTPException(status_code=400, detail="No audio file provided")

        # Forward to voice service
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Prepare multipart data for voice service
            files = {
                "audio": (audio_file.filename, await audio_file.read(), audio_file.content_type)
            }

            response = await client.post(
                f"{config.VOICE_URL}/transcribe",
                files=files
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Voice service error: {response.text}"
                )

            return response.json()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )


@router.post("/synthesize")
async def synthesize_speech(request: VoiceSynthesisRequest):
    """
    Synthesize speech from text using F5-TTS (Chunk 5.3).
    """
    if not config.ENABLE_VOICE:
        raise HTTPException(
            status_code=503,
            detail="Voice features are disabled. Set ENABLE_VOICE=true to enable."
        )
    
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        # Check active persona for voice sample
        active_persona = personas_manager.get_active_persona()
        files = None
        endpoint = "/synthesize"
        
        if active_persona and active_persona.voice_sample_path:
            # Construct file path (ui/assets/personas/...)
            full_path = os.path.join("ui", active_persona.voice_sample_path)
            if os.path.exists(full_path):
                # Read file
                # Note: We read into memory, be careful with large files
                with open(full_path, "rb") as f:
                    file_content = f.read()
                    files = {"reference_audio": (os.path.basename(full_path), file_content, "audio/wav")}
                endpoint = "/synthesize_with_reference"

        # Forward to voice service
        async with httpx.AsyncClient(timeout=60.0) as client:
            if files:
                response = await client.post(
                    f"{config.VOICE_URL}{endpoint}",
                    data={"text": request.text},
                    files=files
                )
            else:
                response = await client.post(
                    f"{config.VOICE_URL}/synthesize",
                    data={"text": request.text}
                )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Voice service error: {response.text}"
                )

            # Return the audio file
            return Response(
                content=response.content,
                media_type="audio/wav",
                headers={
                    "Content-Disposition": "attachment; filename=speech.wav"
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Speech synthesis error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Speech synthesis failed: {str(e)}"
        )