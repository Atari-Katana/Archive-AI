from fastapi import APIRouter, HTTPException, Request
from schemas.chat import ChatRequest, ChatResponse, VerifyRequest, VerifyResponse, VerificationQA
from services.chat_service import chat_service
from services.rate_limiter import rate_limiter
from verification import ChainOfVerification
from stream_handler import stream_handler
from config import config
import httpx

router = APIRouter(tags=["core"])

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request) -> ChatResponse:
    """
    Direct LLM conversation with Bifrost semantic routing.
    """
    # Rate limiting check
    client_ip = http_request.client.host if http_request.client else "unknown"
    if not rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Maximum 30 requests per minute."
        )

    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    return await chat_service.process_chat(request.message)

@router.post("/verify", response_model=VerifyResponse)
async def verify(request: VerifyRequest, http_request: Request) -> VerifyResponse:
    """
    Chat with Chain of Verification
    """
    # Rate limiting check
    client_ip = http_request.client.host if http_request.client else "unknown"
    if not rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Maximum 30 requests per minute."
        )

    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Capture input to Redis Stream (non-blocking)
    await stream_handler.capture_input(request.message)

    try:
        # Run chain of verification
        async with httpx.AsyncClient(timeout=config.REQUEST_TIMEOUT) as client:
            async with ChainOfVerification(http_client=client) as cov:
                result = await cov.verify(request.message)

        # Convert to response model
        verification_qa = [
            VerificationQA(
                question=qa["question"],
                answer=qa["answer"]
            )
            for qa in result["verification_qa"]
        ]

        return VerifyResponse(
            initial_response=result["initial_response"],
            verification_questions=result["verification_questions"],
            verification_qa=verification_qa,
            final_response=result["final_response"],
            revised=result["revised"],
            engine=f"vorpal/{config.VORPAL_MODEL}"
        )

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Vorpal engine error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Verification error: {str(e)}"
        )
