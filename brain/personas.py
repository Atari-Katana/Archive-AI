import json
import os
import shutil
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from config import config

router = APIRouter(prefix="/personas", tags=["personas"])

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

class PersonasManager:
    def __init__(self):
        self.file_path = config.PERSONAS_FILE
        self.active_file_path = os.path.join("data", "active_persona.json")
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as f:
                json.dump([], f)
        
        if not os.path.exists(self.active_file_path):
             with open(self.active_file_path, 'w') as f:
                json.dump({"active_id": None}, f)

    def get_all(self) -> List[Persona]:
        with open(self.file_path, 'r') as f:
            data = json.load(f)
        return [Persona(**item) for item in data]

    def get_by_id(self, persona_id: str) -> Optional[Persona]:
        personas = self.get_all()
        for p in personas:
            if p.id == persona_id:
                return p
        return None

    def create(self, persona: Persona) -> Persona:
        personas = self.get_all()
        # Convert Pydantic model to dict
        personas.append(persona.dict())
        self._save(personas)
        return persona

    def update(self, persona_id: str, updates: dict) -> Optional[Persona]:
        personas = self.get_all()
        for i, p in enumerate(personas):
            if p.id == persona_id:
                # Update fields
                updated_data = p.dict()
                updated_data.update(updates)
                updated_data['last_modified'] = datetime.utcnow().isoformat() + "Z"
                
                new_persona = Persona(**updated_data)
                personas[i] = new_persona
                
                # If this is the active persona, invalidating cache might be needed if we cached it
                # For now, we read from disk on chat so it's fine.
                
                self._save([p.dict() for p in personas])
                return new_persona
        return None

    def delete(self, persona_id: str) -> bool:
        personas = self.get_all()
        initial_len = len(personas)
        personas = [p for p in personas if p.id != persona_id]
        
        if len(personas) < initial_len:
            self._save([p.dict() for p in personas])
            
            # Check if active, if so, deactivate
            active = self.get_active_id()
            if active == persona_id:
                self.set_active_id(None)
            
            return True
        return False

    def _save(self, data: list):
        with open(self.file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def get_active_id(self) -> Optional[str]:
        try:
            with open(self.active_file_path, 'r') as f:
                data = json.load(f)
                return data.get("active_id")
        except:
            return None

    def set_active_id(self, persona_id: Optional[str]):
        with open(self.active_file_path, 'w') as f:
            json.dump({"active_id": persona_id}, f)

    def get_active_persona(self) -> Optional[Persona]:
        active_id = self.get_active_id()
        if active_id:
            return self.get_by_id(active_id)
        return None

manager = PersonasManager()

@router.get("/", response_model=List[Persona])
async def list_personas():
    return manager.get_all()

@router.post("/", response_model=Persona)
async def create_persona(payload: PersonaCreate):
    now = datetime.utcnow().isoformat() + "Z"
    new_persona = Persona(
        id=str(uuid.uuid4()),
        name=payload.name,
        personality=payload.personality,
        history=payload.history,
        avatar_path=payload.avatar_path,
        voice_sample_path=payload.voice_sample_path,
        created_at=now,
        last_modified=now
    )
    return manager.create(new_persona)

@router.put("/{persona_id}", response_model=Persona)
async def update_persona(persona_id: str, payload: PersonaUpdate):
    updates = {k: v for k, v in payload.dict().items() if v is not None}
    updated = manager.update(persona_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Persona not found")
    return updated

@router.delete("/{persona_id}")
async def delete_persona(persona_id: str):
    success = manager.delete(persona_id)
    if not success:
        raise HTTPException(status_code=404, detail="Persona not found")
    return {"status": "deleted"}

@router.post("/upload")
async def upload_asset(file: UploadFile = File(...), type: str = Form(...)):
    """
    Uploads an asset file (image or audio).
    Type must be 'image' or 'audio'.
    """
    if type not in ['image', 'audio']:
        raise HTTPException(status_code=400, detail="Invalid asset type")
    
    # Generate unique filename to avoid collisions
    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(config.PERSONAS_ASSET_DIR, filename)
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")
        
    # Return relative path for frontend usage
    # Assets are mounted at /ui/assets in main.py, but actually main.py mounts ui/ at /ui
    # So ui/assets/personas/file.png is accessed via /ui/assets/personas/file.png
    # The stored path should be relative or absolute web path? 
    # The requirement example says "./assets/personas/..."
    # Let's stick to a web-accessible relative path.
    
    return {"path": f"assets/personas/{filename}"}

@router.post("/activate/{persona_id}")
async def activate_persona(persona_id: str):
    persona = manager.get_by_id(persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    
    manager.set_active_id(persona_id)
    return {"status": "activated", "persona": persona}

@router.post("/deactivate")
async def deactivate_persona():
    manager.set_active_id(None)
    return {"status": "deactivated"}

@router.get("/active", response_model=ActivePersonaResponse)
async def get_active_persona():
    active_id = manager.get_active_id()
    persona = manager.get_by_id(active_id) if active_id else None
    return ActivePersonaResponse(active_id=active_id, persona=persona)
