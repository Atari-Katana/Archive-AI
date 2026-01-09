from pydantic import BaseModel
from typing import List, Optional

class LibraryChunk(BaseModel):
    """Library chunk response model"""
    text: str
    filename: str
    file_type: str
    chunk_index: int
    total_chunks: int
    tokens: int
    timestamp: int
    similarity_score: float
    similarity_pct: float

class LibrarySearchRequest(BaseModel):
    """Library search request model (Phase 5.2)"""
    query: str
    top_k: int = 5
    filter_file_type: Optional[str] = None

class LibrarySearchResponse(BaseModel):
    """Library search response model"""
    chunks: List[LibraryChunk]
    total: int
    query: str

class LibraryStats(BaseModel):
    """Library statistics model"""
    total_chunks: int
    unique_files: int
    files: List[str]

class ResearchSource(BaseModel):
    """Research source model"""
    type: str  # "library" or "memory"
    filename: Optional[str] = None
    text: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[int] = None
    similarity: float

class ResearchRequest(BaseModel):
    """Research assistant request model (Phase 5.4)"""
    question: str
    use_library: bool = True
    use_memory: bool = True
    top_k: int = 5

class ResearchResponse(BaseModel):
    """Research assistant response model"""
    question: str
    answer: str
    sources: List[ResearchSource]
    library_chunks_consulted: int
    memories_consulted: int
    total_sources: int
    success: bool
    engine: str = "vorpal"
    error: Optional[str] = None

class MultiResearchRequest(BaseModel):
    """Multi-question research request"""
    questions: List[str]
    synthesize: bool = True
