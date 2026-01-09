from pydantic import BaseModel
from typing import Optional, Dict, List, Any

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    service: str
    version: str

class DetailedHealthResponse(BaseModel):
    """Detailed health check response model"""
    status: str
    vorpal_url: str
    vorpal_model: str
    async_memory: Dict[str, Any]

class ServiceStatus(BaseModel):
    """Individual service status"""
    name: str
    status: str
    url: Optional[str] = None
