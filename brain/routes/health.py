from fastapi import APIRouter
from schemas.common import HealthResponse, DetailedHealthResponse
from services.system_service import system_service
from workers.memory_worker import memory_worker
from config import config

router = APIRouter(tags=["health"])

@router.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint - Basic health check"""
    return {
        "status": "healthy",
        "service": "archive-brain",
        "version": "0.4.0"
    }

@router.get("/health", response_model=DetailedHealthResponse)
async def health():
    """Detailed health check"""
    memory_status = {
        "enabled": config.ASYNC_MEMORY,
        "start_from_latest": config.MEMORY_START_FROM_LATEST,
        "last_id": memory_worker.last_id
    }

    # Include stream length when possible
    if config.ASYNC_MEMORY and memory_worker.redis_client:
        try:
            memory_status["stream_length"] = await memory_worker.redis_client.xlen(
                config.REDIS_STREAM_KEY
            )
        except Exception as e:
            memory_status["stream_length_error"] = str(e)

    return {
        "status": "healthy",
        "vorpal_url": config.VORPAL_URL,
        "vorpal_model": config.VORPAL_MODEL,
        "async_memory": memory_status
    }
