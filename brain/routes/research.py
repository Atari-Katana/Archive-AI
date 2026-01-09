from fastapi import APIRouter, HTTPException
from typing import Dict
from schemas.library import ResearchResponse, ResearchRequest, MultiResearchRequest, ResearchSource
from agents.research_agent import research_query, multi_query_research
from config import config

router = APIRouter(prefix="/research", tags=["research"])

@router.post("/", response_model=ResearchResponse)
async def research_question(request: ResearchRequest):
    """
    Research a question using library and/or memory sources.
    """
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        result = await research_query(
            question=request.question,
            use_library=request.use_library,
            use_memory=request.use_memory,
            top_k=request.top_k
        )

        return ResearchResponse(
            question=request.question,
            answer=result.answer,
            sources=[ResearchSource(**s) for s in result.sources],
            library_chunks_consulted=result.library_chunks_consulted,
            memories_consulted=result.memories_consulted,
            total_sources=result.total_sources,
            success=result.success,
            engine=f"vorpal/{config.VORPAL_MODEL}",
            error=result.error
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Research error: {str(e)}"
        )


@router.post("/multi")
async def research_multiple_questions(request: MultiResearchRequest) -> Dict:
    """
    Research multiple related questions with optional synthesis.
    """
    if not request.questions or len(request.questions) == 0:
        raise HTTPException(status_code=400, detail="Questions list cannot be empty")

    if len(request.questions) > 10:
        raise HTTPException(
            status_code=400,
            detail=f"Too many questions ({len(request.questions)}). Maximum 10."
        )

    try:
        result = await multi_query_research(
            questions=request.questions,
            synthesize=request.synthesize
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Multi-research error: {str(e)}"
        )
