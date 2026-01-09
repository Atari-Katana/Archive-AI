from pydantic import BaseModel
from typing import Optional

class VoiceTranscriptionResponse(BaseModel):
    """Voice transcription response model"""
    text: str
    language: Optional[str] = None
    duration: Optional[float] = None

class VoiceSynthesisRequest(BaseModel):
    """Voice synthesis request model"""
    text: str
