"""
Archive-Brain Core (Refactored)
Orchestrator with async memory worker, Chain of Verification, and ReAct agents.
"""

import asyncio
import time
import logging
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import config
from stream_handler import stream_handler
from workers.memory_worker import memory_worker
from memory.vector_store import vector_store
from services.metrics_service import metrics_collector_service

# Import Routers
from routes.health import router as health_router
from routes.metrics import router as metrics_router
from routes.config import router as config_router
from routes.chat import router as chat_router
from routes.agent import router as agent_router
from routes.agent import router_root as agent_root_router
from routes.memory import router as memory_router
from routes.library import router as library_router
from routes.research import router as research_router
from routes.voice import router as voice_router
from routes.admin import router as admin_router
from routes.personas import router as personas_router

# Configure logging
def setup_logging():
    os.makedirs(config.LOG_DIR, exist_ok=True)
    logfile = os.path.join(config.LOG_DIR, "brain.log")
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(logfile, encoding="utf-8")
        ],
        force=True,
    )

setup_logging()
logger = logging.getLogger("brain")

app = FastAPI(
    title="Archive-Brain API",
    version="0.4.0",
    description="""
## Archive-AI Brain API

The central orchestrator for Archive-AI.
    """,
    contact={
        "name": "Archive-AI Project",
        "url": "https://github.com/archive-ai"
    },
    license_info={
        "name": "MIT",
    }
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(health_router)
app.include_router(metrics_router) # Handles /metrics (dash) and /metrics/ (history)
app.include_router(config_router)
app.include_router(chat_router)
app.include_router(agent_router)
app.include_router(agent_root_router) # Handles /code_assist
app.include_router(memory_router)
app.include_router(library_router)
app.include_router(research_router)
app.include_router(voice_router)
app.include_router(admin_router)
app.include_router(personas_router)

# Mount static files
ui_path = Path(__file__).parent / "ui"
if ui_path.exists():
    app.mount("/ui", StaticFiles(directory=str(ui_path), html=True), name="static")

# Background task handle
worker_task = None

@app.on_event("startup")
async def startup():
    """Initialize connections and start background workers"""
    global worker_task

    await stream_handler.connect()

    # Initialize vector store
    vector_store.redis_url = config.REDIS_URL
    vector_store.connect()
    try:
        vector_store.create_index()
    except Exception as e:
        logger.warning(f"Index creation warning: {e}")

    # Start memory worker
    if config.ASYNC_MEMORY:
        await memory_worker.connect()
        worker_task = asyncio.create_task(memory_worker.run())
        logger.info("Memory worker started")

    # Start archival worker if enabled
    if config.ARCHIVE_ENABLED:
        from workers.archiver import archiver
        await archiver.start()
        logger.info("Memory archival worker started")

    # Start metrics collection
    asyncio.create_task(metrics_collector_service.start_collection())
    logger.info("Metrics collector started")

@app.on_event("shutdown")
async def shutdown():
    """Close connections and stop background workers"""
    global worker_task
    
    # Stop memory worker
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
    
    metrics_collector_service.stop_collection()

    await memory_worker.close()
    await stream_handler.close()
    if vector_store.client:
        vector_store.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)