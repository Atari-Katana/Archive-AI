import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from config import config
from schemas.personas import Persona, PersonaCreate, PersonaUpdate

class PersonasManager:
    def __init__(self):
        self.file_path = config.PERSONAS_FILE
        self.active_file_path = os.path.join("data", "active_persona.json")
        self._ensure_file()

    def _ensure_file(self):
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.active_file_path), exist_ok=True)

        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as f:
                json.dump([], f)
        
        if not os.path.exists(self.active_file_path):
             with open(self.active_file_path, 'w') as f:
                json.dump({"active_id": None}, f)

    def get_all(self) -> List[Persona]:
        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            return [Persona(**item) for item in data]
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def get_by_id(self, persona_id: str) -> Optional[Persona]:
        personas = self.get_all()
        for p in personas:
            if p.id == persona_id:
                return p
        return None

    def create(self, payload: PersonaCreate) -> Persona:
        personas = self.get_all()
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
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
        
        # Convert Pydantic model to dict
        personas.append(new_persona)
        self._save([p.model_dump() for p in personas])
        return new_persona

    def update(self, persona_id: str, payload: PersonaUpdate) -> Optional[Persona]:
        personas = self.get_all()
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        
        for i, p in enumerate(personas):
            if p.id == persona_id:
                # Update fields
                updated_data = p.model_dump()
                updated_data.update(updates)
                updated_data['last_modified'] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                
                new_persona = Persona(**updated_data)
                personas[i] = new_persona
                
                self._save([p.model_dump() for p in personas])
                return new_persona
        return None

    def delete(self, persona_id: str) -> bool:
        personas = self.get_all()
        initial_len = len(personas)
        personas = [p for p in personas if p.id != persona_id]
        
        if len(personas) < initial_len:
            self._save([p.model_dump() for p in personas])
            
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
    
    def save_asset(self, file_obj, filename: str) -> str:
        """Saves an asset file and returns the relative path"""
        file_path = os.path.join(config.PERSONAS_ASSET_DIR, filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file_obj, buffer)
            
        return f"assets/personas/{filename}"

# Global instance
personas_manager = PersonasManager()
