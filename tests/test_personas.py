import json
import os
import shutil
import unittest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Add project root and brain directory to sys.path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'brain'))

# Mock config
with patch('config.config') as mock_config:
    mock_config.PERSONAS_FILE = "tests/data/personas.json"
    mock_config.PERSONAS_ASSET_DIR = "tests/data/assets"
    mock_config.VORPAL_URL = "http://mock-vorpal"
    mock_config.BIFROST_URL = "http://mock-bifrost"
    mock_config.VOICE_URL = "http://mock-voice"
    mock_config.REQUEST_TIMEOUT = 10
    mock_config.MAX_TOKENS = 100
    mock_config.VORPAL_MODEL = "mock-model"
    mock_config.REDIS_URL = "redis://mock-redis:6379"
    mock_config.ASYNC_MEMORY = False
    mock_config.ARCHIVE_ENABLED = False
    mock_config.LOG_DIR = "tests/logs"
    mock_config.LOG_LEVEL = "INFO"
    
    # Import app after path setup
    from brain.main import app
    from brain.services.persona_manager import personas_manager

class TestPersonasSystem(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.test_dir = Path("tests/data")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        (self.test_dir / "assets").mkdir(exist_ok=True)
        
        # Reset manager paths for testing
        personas_manager.file_path = str(self.test_dir / "personas.json")
        personas_manager.active_file_path = str(self.test_dir / "active_persona.json")
        personas_manager._ensure_file()

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_create_persona(self):
        payload = {
            "name": "Test Persona",
            "personality": "You are a test bot.",
            "history": "Created for testing."
        }
        response = self.client.post("/personas/", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], payload["name"])
        self.assertIn("id", data)

    def test_list_personas(self):
        self.test_create_persona()
        response = self.client.get("/personas/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(len(data), 1)

    def test_update_persona(self):
        create_resp = self.client.post("/personas/", json={
            "name": "Original",
            "personality": "Original prompt"
        })
        persona_id = create_resp.json()["id"]
        
        update_payload = {"name": "Updated Name"}
        response = self.client.put(f"/personas/{persona_id}", json=update_payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Updated Name")

    def test_delete_persona(self):
        create_resp = self.client.post("/personas/", json={
            "name": "To Delete",
            "personality": "..."
        })
        persona_id = create_resp.json()["id"]
        
        response = self.client.delete(f"/personas/{persona_id}")
        self.assertEqual(response.status_code, 200)
        
        get_resp = self.client.get("/personas/")
        self.assertEqual(len(get_resp.json()), 0)

    def test_activate_persona(self):
        create_resp = self.client.post("/personas/", json={
            "name": "Active Bot",
            "personality": "I am active."
        })
        persona_id = create_resp.json()["id"]
        
        response = self.client.post(f"/personas/activate/{persona_id}")
        self.assertEqual(response.status_code, 200)
        
        active_resp = self.client.get("/personas/active")
        self.assertEqual(active_resp.json()["active_persona_id"], persona_id)

if __name__ == "__main__":
    unittest.main()
