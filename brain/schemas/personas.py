from pydantic import BaseModel
from typing import Optional

class Persona(BaseModel):
    id: str
    name: str
    personality: str
    history: Optional[str] = None
    avatar_path: Optional[str] = None
    voice_sample_path: Optional[str] = None
    created_at: str
    last_modified: str

class PersonaCreate(BaseModel):
    name: str
    personality: str
    history: Optional[str] = None
    avatar_path: Optional[str] = None
    voice_sample_path: Optional[str] = None

class PersonaUpdate(BaseModel):
    name: Optional[str] = None
    personality: Optional[str] = None
    history: Optional[str] = None
    avatar_path: Optional[str] = None
    voice_sample_path: Optional[str] = None

class ActivePersonaResponse(BaseModel):
    active_persona_id: Optional[str] = None
    persona: Optional[Persona] = None
