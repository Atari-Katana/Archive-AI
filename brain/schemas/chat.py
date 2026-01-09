from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    """Chat request model"""
    message: str

class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    engine: str = "vorpal"

class VerificationQA(BaseModel):
    """Verification Q&A pair"""
    question: str
    answer: str

class VerifyRequest(BaseModel):
    """Verification request model"""
    message: str
    use_verification: bool = True

class VerifyResponse(BaseModel):
    """Verification response model"""
    initial_response: str
    verification_questions: List[str]
    verification_qa: List[VerificationQA]
    final_response: str
    revised: bool
    engine: str = "vorpal"
