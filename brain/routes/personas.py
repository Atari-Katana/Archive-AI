from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List
from services.persona_manager import personas_manager, Persona, PersonaCreate, PersonaUpdate
from schemas.personas import ActivePersonaResponse

router = APIRouter(prefix="/personas", tags=["personas"])

@router.get("/", response_model=List[Persona])
async def list_personas():
    return personas_manager.get_all()

@router.post("/", response_model=Persona)
async def create_persona(payload: PersonaCreate):
    return personas_manager.create(payload)

@router.put("/{persona_id}", response_model=Persona)
async def update_persona(persona_id: str, payload: PersonaUpdate):
    updated = personas_manager.update(persona_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Persona not found")
    return updated

@router.delete("/{persona_id}")
async def delete_persona(persona_id: str):
    success = personas_manager.delete(persona_id)
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
    import os
    import uuid
    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{ext}"
    
    try:
        path = personas_manager.save_asset(file.file, filename)
        return {"path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

@router.post("/activate/{persona_id}")
async def activate_persona(persona_id: str):
    persona = personas_manager.get_by_id(persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    
    personas_manager.set_active_id(persona_id)
    return {"status": "activated", "persona": persona}

@router.post("/deactivate")
async def deactivate_persona():
    personas_manager.set_active_id(None)
    return {"status": "deactivated"}

@router.get("/active", response_model=ActivePersonaResponse)
async def get_active_persona():
    active_id = personas_manager.get_active_id()
    persona = personas_manager.get_by_id(active_id) if active_id else None
    return ActivePersonaResponse(active_persona_id=active_id, persona=persona)
