from pydantic import BaseModel, Field
from typing import List, Optional

class AgentStepResponse(BaseModel):
    """Agent reasoning step"""
    step_number: int
    thought: str
    action: Optional[str] = None
    action_input: Optional[str] = None
    observation: Optional[str] = None

class AgentRequest(BaseModel):
    """ReAct agent request model"""
    question: str
    max_steps: int = 10

class AgentResponse(BaseModel):
    """ReAct agent response model"""
    answer: str
    steps: List[AgentStepResponse]
    total_steps: int
    success: bool
    engine: str = "vorpal"
    error: Optional[str] = None

class RecursiveAgentRequest(BaseModel):
    """Request for Recursive Agent"""
    question: str = Field(..., description="Question to answer about the corpus")
    corpus: str = Field(..., description="The large text document to process")
    max_steps: int = Field(10, description="Maximum reasoning steps")

class CodeAssistRequest(BaseModel):
    """Code assistant request model (Phase 5.5)"""
    task: str
    max_attempts: int = 3
    timeout: int = 10

class CodeAssistResponse(BaseModel):
    """Code assistant response model"""
    task: str
    code: str
    explanation: str
    test_output: Optional[str] = None
    success: bool
    attempts: int
    engine: str = "vorpal"
    error: Optional[str] = None
