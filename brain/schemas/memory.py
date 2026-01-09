from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class MemoryItem(BaseModel):
    """Memory item model"""
    id: str
    message: str
    perplexity: float
    surprise_score: float
    timestamp: float
    session_id: str
    similarity_score: Optional[float] = None

class MemoryListResponse(BaseModel):
    """Memory list response model"""
    memories: List[MemoryItem]
    total: int

class MemorySearchRequest(BaseModel):
    """Memory search request model"""
    query: str
    top_k: int = 10
    session_id: Optional[str] = None

class ArchiveStatsResponse(BaseModel):
    """Archive statistics response model"""
    total_archive_files: int
    total_archived_memories: int
    oldest_archive_date: Optional[str]
    newest_archive_date: Optional[str]
    archive_directory: str

class ArchiveSearchRequest(BaseModel):
    """Archive search request model (Admin endpoints)"""
    query: str
    max_results: int = 10

class ArchiveSearchResponse(BaseModel):
    """Archive search response model"""
    query: str
    results: List[Dict[str, Any]]
    count: int
