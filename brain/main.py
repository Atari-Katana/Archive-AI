"""
Archive-Brain Core (Chunks 2.3 + 3.1 + 3.2)
Orchestrator with async memory worker, Chain of Verification, and ReAct agents.
"""

import asyncio
import time
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from config import config
from stream_handler import stream_handler
from workers.memory_worker import memory_worker
from verification import ChainOfVerification
from agents import ReActAgent, ToolRegistry, AgentStep, get_basic_tools, get_advanced_tools
from memory.vector_store import vector_store


app = FastAPI(
    title="Archive-Brain API",
    version="0.4.0",
    description="""
## Archive-AI Brain API

The central orchestrator for Archive-AI, providing intelligent conversation,
chain-of-verification, ReAct agents, and memory management.

### Features

* **Chat**: Direct LLM conversation with Vorpal engine (Qwen 2.5-3B)
* **Chain of Verification**: Reduce hallucinations with 4-stage verification
* **ReAct Agents**: Reasoning + Acting agents with tool use
* **Memory System**: Surprise-based memory storage with semantic search
* **Vector Store**: 384-dim embeddings with HNSW indexing

### Architecture

- **LLM Engine**: Vorpal (vLLM + Qwen 2.5-3B-Instruct)
- **Memory**: Redis Stack (Streams + Vector Store)
- **Embedding**: sentence-transformers/all-MiniLM-L6-v2
- **Agent Tools**: 11 tools (6 basic + 5 advanced)
    """,
    contact={
        "name": "Archive-AI Project",
        "url": "https://github.com/archive-ai"
    },
    license_info={
        "name": "MIT",
    },
    openapi_tags=[
        {
            "name": "core",
            "description": "Core chat and verification endpoints"
        },
        {
            "name": "agents",
            "description": "ReAct agents with tool use"
        },
        {
            "name": "memory",
            "description": "Memory storage and semantic search"
        },
        {
            "name": "health",
            "description": "System health and status"
        }
    ]
)

# Configure CORS to allow browser access from web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8888", "http://127.0.0.1:8888"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Background task handle
worker_task = None
# Startup time for uptime calculation
startup_time = time.time()


@app.on_event("startup")
async def startup():
    """Initialize connections and start background workers"""
    global worker_task

    await stream_handler.connect()

    # Initialize vector store with configured Redis URL
    vector_store.redis_url = config.REDIS_URL
    vector_store.connect()
    vector_store.create_index()

    # Start memory worker if async memory is enabled
    if config.ASYNC_MEMORY:
        await memory_worker.connect()
        worker_task = asyncio.create_task(memory_worker.run())
        print("[Brain] Memory worker started")

    # Start archival worker if enabled (Chunk 5.6)
    if config.ARCHIVE_ENABLED:
        from workers.archiver import archiver
        await archiver.start()
        print("[Brain] Memory archival worker started")


@app.on_event("shutdown")
async def shutdown():
    """Close connections and stop background workers"""
    # Stop memory worker
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

    await memory_worker.close()
    await stream_handler.close()
    vector_store.close()


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str


class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    engine: str = "vorpal"


class VerifyRequest(BaseModel):
    """Verification request model"""
    message: str
    use_verification: bool = True


class VerificationQA(BaseModel):
    """Verification Q&A pair"""
    question: str
    answer: str


class VerifyResponse(BaseModel):
    """Verification response model"""
    initial_response: str
    verification_questions: List[str]
    verification_qa: List[VerificationQA]
    final_response: str
    revised: bool


class AgentRequest(BaseModel):
    """ReAct agent request model"""
    question: str
    max_steps: int = 10


class AgentStepResponse(BaseModel):
    """Agent reasoning step"""
    step_number: int
    thought: str
    action: Optional[str] = None
    action_input: Optional[str] = None
    observation: Optional[str] = None


class AgentResponse(BaseModel):
    """ReAct agent response model"""
    answer: str
    steps: List[AgentStepResponse]
    total_steps: int
    success: bool
    error: Optional[str] = None


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


class LibrarySearchRequest(BaseModel):
    """Library search request model (Phase 5.2)"""
    query: str
    top_k: int = 5
    filter_file_type: Optional[str] = None


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


class ResearchRequest(BaseModel):
    """Research assistant request model (Phase 5.4)"""
    question: str
    use_library: bool = True
    use_memory: bool = True
    top_k: int = 5


class ResearchSource(BaseModel):
    """Research source model"""
    type: str  # "library" or "memory"
    filename: Optional[str] = None
    text: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[int] = None
    similarity: float


class ResearchResponse(BaseModel):
    """Research assistant response model"""
    question: str
    answer: str
    sources: List[ResearchSource]
    library_chunks_consulted: int
    memories_consulted: int
    total_sources: int
    success: bool
    error: Optional[str] = None


class MultiResearchRequest(BaseModel):
    """Multi-question research request"""
    questions: List[str]
    synthesize: bool = True


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
    error: Optional[str] = None


class SystemMetrics(BaseModel):
    """System resource metrics"""
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    memory_used_mb: Optional[float] = None
    memory_total_mb: Optional[float] = None


class MemoryStats(BaseModel):
    """Memory storage statistics"""
    total_memories: int
    storage_threshold: float
    embedding_dim: int
    index_type: str


class ServiceStatus(BaseModel):
    """Individual service status"""
    name: str
    status: str
    url: Optional[str] = None


class MetricsResponse(BaseModel):
    """Complete system metrics response"""
    uptime_seconds: float
    system: Optional[SystemMetrics] = None
    memory_stats: MemoryStats
    services: List[ServiceStatus]
    version: str


@app.get("/", tags=["health"])
async def root():
    """
    Root endpoint - Basic health check

    Returns the service name, version, and status.
    """
    return {
        "status": "healthy",
        "service": "archive-brain",
        "version": "0.4.0"
    }


@app.get("/health", tags=["health"])
async def health():
    """
    Detailed health check

    Returns comprehensive health information including:
    - Service status
    - Vorpal engine URL
    - Async memory worker status
    """
    return {
        "status": "healthy",
        "vorpal_url": config.VORPAL_URL,
        "async_memory": config.ASYNC_MEMORY
    }


@app.get("/metrics", response_model=MetricsResponse, tags=["health"])
async def get_metrics() -> MetricsResponse:
    """
    System metrics and statistics

    Comprehensive system monitoring including:
    - **Uptime**: Service uptime in seconds
    - **System Resources**: CPU and memory usage (if psutil available)
    - **Memory Statistics**: Total stored memories, storage threshold, embedding info
    - **Service Status**: Status of Brain, Vorpal, Redis, and Sandbox services

    **Example Response:**
    ```json
    {
        "uptime_seconds": 3600.5,
        "system": {
            "cpu_percent": 15.2,
            "memory_percent": 45.8,
            "memory_used_mb": 2048.5,
            "memory_total_mb": 4096.0
        },
        "memory_stats": {
            "total_memories": 107,
            "storage_threshold": 0.7,
            "embedding_dim": 384,
            "index_type": "HNSW"
        },
        "services": [
            {"name": "Brain", "status": "healthy", "url": "internal"},
            {"name": "Vorpal", "status": "healthy", "url": "http://vorpal:8000"},
            {"name": "Redis", "status": "healthy", "url": "redis://redis:6379"},
            {"name": "Sandbox", "status": "unknown", "url": "http://sandbox:8000"}
        ],
        "version": "0.4.0"
    }
    ```

    Returns:
        MetricsResponse with complete system metrics
    """
    # Calculate uptime
    uptime = time.time() - startup_time

    # Get system metrics if psutil is available
    system_metrics = None
    if PSUTIL_AVAILABLE:
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            system_metrics = SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                memory_total_mb=memory.total / (1024 * 1024)
            )
        except Exception:
            pass  # If psutil fails, just skip system metrics

    # Get memory statistics
    try:
        # Count total memories
        cursor = 0
        total_count = 0
        while True:
            cursor, keys = vector_store.client.scan(
                cursor=cursor,
                match=f"{vector_store.prefix}*",
                count=100
            )
            total_count += len(keys)
            if cursor == 0:
                break

        memory_stats = MemoryStats(
            total_memories=total_count,
            storage_threshold=0.7,
            embedding_dim=384,
            index_type="HNSW"
        )
    except Exception:
        # If Redis is down, return zeros
        memory_stats = MemoryStats(
            total_memories=0,
            storage_threshold=0.7,
            embedding_dim=384,
            index_type="HNSW"
        )

    # Check service statuses
    services = []

    # Brain (self) - always healthy if responding
    services.append(ServiceStatus(
        name="Brain",
        status="healthy",
        url="internal"
    ))

    # Vorpal engine
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{config.VORPAL_URL}/health")
            vorpal_status = "healthy" if response.status_code == 200 else "degraded"
    except Exception:
        vorpal_status = "unhealthy"

    services.append(ServiceStatus(
        name="Vorpal",
        status=vorpal_status,
        url=config.VORPAL_URL
    ))

    # Redis
    try:
        vector_store.client.ping()
        redis_status = "healthy"
    except Exception:
        redis_status = "unhealthy"

    services.append(ServiceStatus(
        name="Redis",
        status=redis_status,
        url=config.REDIS_URL
    ))

    # Sandbox
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{config.SANDBOX_URL}/health")
            sandbox_status = "healthy" if response.status_code == 200 else "degraded"
    except Exception:
        sandbox_status = "unknown"

    services.append(ServiceStatus(
        name="Sandbox",
        status=sandbox_status,
        url=config.SANDBOX_URL
    ))

    return MetricsResponse(
        uptime_seconds=uptime,
        system=system_metrics,
        memory_stats=memory_stats,
        services=services,
        version="0.4.0"
    )


@app.post("/chat", response_model=ChatResponse, tags=["core"])
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Direct LLM conversation

    Send a message to the Vorpal engine (Qwen 2.5-3B) and receive a response.
    Messages are captured in Redis streams and may be stored in the vector
    store if they have high surprise scores (>= 0.7).

    **Example Request:**
    ```json
    {
        "message": "What is the capital of France?"
    }
    ```

    **Example Response:**
    ```json
    {
        "response": "The capital of France is Paris.",
        "engine": "vorpal"
    }
    ```

    Args:
        request: ChatRequest with user message

    Returns:
        ChatResponse with Vorpal's reply
    """
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Capture input to Redis Stream (non-blocking, fire and forget)
    await stream_handler.capture_input(request.message)

    try:
        # Proxy request to Vorpal (vLLM OpenAI-compatible API)
        async with httpx.AsyncClient(timeout=config.REQUEST_TIMEOUT) as client:
            vorpal_payload = {
                "model": "Qwen/Qwen2.5-3B-Instruct",
                "prompt": request.message,
                "max_tokens": 256,
                "temperature": 0.7
            }

            response = await client.post(
                f"{config.VORPAL_URL}/v1/completions",
                json=vorpal_payload
            )
            response.raise_for_status()
            result = response.json()

            # Extract completion text from vLLM response
            completion_text = result.get("choices", [{}])[0].get(
                "text",
                ""
            ).strip()

            return ChatResponse(
                response=completion_text,
                engine="vorpal"
            )

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Vorpal engine error: {str(e)}"
        )


@app.post("/verify", response_model=VerifyResponse, tags=["core"])
async def verify(request: VerifyRequest) -> VerifyResponse:
    """
    Chat with Chain of Verification

    Reduce hallucinations using a 4-stage verification process:
    1. **Generate** initial response
    2. **Plan** verification questions
    3. **Execute** independent verification
    4. **Revise** if inconsistencies found

    **Example Request:**
    ```json
    {
        "message": "What is the largest planet in our solar system?"
    }
    ```

    **Example Response:**
    ```json
    {
        "initial_response": "The largest planet is Jupiter...",
        "verification_questions": ["Is Jupiter the largest?", ...],
        "verification_qa": [...],
        "final_response": "Corrected: Jupiter's diameter is...",
        "revised": true
    }
    ```

    Args:
        request: VerifyRequest with user message

    Returns:
        VerifyResponse with verification details and final response
    """
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
            revised=result["revised"]
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


@app.post("/agent", response_model=AgentResponse, tags=["agents"])
async def agent_solve(request: AgentRequest) -> AgentResponse:
    """
    Basic ReAct agent (6 tools)

    Solve problems using Reasoning + Acting pattern with basic tools:
    - **Calculator**: Safe math operations
    - **StringLength**: Count string characters
    - **WordCount**: Count words in text
    - **ReverseString**: Reverse text
    - **ToUppercase**: Convert to uppercase
    - **ExtractNumbers**: Extract numbers from text

    **Example Request:**
    ```json
    {
        "question": "Calculate 15 * 27",
        "max_steps": 5
    }
    ```

    **Example Response:**
    ```json
    {
        "answer": "405",
        "steps": [
            {
                "step_number": 1,
                "thought": "I need to use Calculator...",
                "action": "Calculator",
                "action_input": "15 * 27",
                "observation": "Result: 405.0"
            }
        ],
        "total_steps": 2,
        "success": true
    }
    ```

    Args:
        request: AgentRequest with question and max_steps

    Returns:
        AgentResponse with answer and reasoning trace
    """
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Capture input to Redis Stream (non-blocking)
    await stream_handler.capture_input(request.question)

    try:
        # Build tool registry (basic tools only)
        registry = ToolRegistry()
        basic_tools = get_basic_tools()

        for tool_name, (description, func) in basic_tools.items():
            registry.register(tool_name, description, func)

        # Run ReAct agent
        async with httpx.AsyncClient(timeout=config.REQUEST_TIMEOUT) as client:
            async with ReActAgent(registry, http_client=client) as agent:
                # Override max steps if specified
                if request.max_steps:
                    agent.MAX_STEPS = request.max_steps

                result = await agent.solve(request.question)

        # Convert steps to response model
        steps_response = [
            AgentStepResponse(
                step_number=step.step_number,
                thought=step.thought,
                action=step.action,
                action_input=step.action_input,
                observation=step.observation
            )
            for step in result.steps
        ]

        return AgentResponse(
            answer=result.answer,
            steps=steps_response,
            total_steps=result.total_steps,
            success=result.success,
            error=result.error
        )

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Vorpal engine error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {str(e)}"
        )


@app.post("/agent/advanced", response_model=AgentResponse, tags=["agents"])
async def agent_solve_advanced(request: AgentRequest) -> AgentResponse:
    """
    Advanced ReAct agent (11 tools)

    All basic tools PLUS advanced capabilities:
    - **MemorySearch**: Semantic search of stored memories
    - **CodeExecution**: Execute Python in sandbox
    - **DateTime**: Current date/time information
    - **JSON**: Parse and validate JSON data
    - **WebSearch**: Search the web (placeholder)

    **Example Request:**
    ```json
    {
        "question": "Search my memories for 'sales data' then tell me the current time",
        "max_steps": 5
    }
    ```

    **Example Response:**
    ```json
    {
        "answer": "No sales data found. Current time is 2025-12-28 02:30:45",
        "steps": [
            {
                "step_number": 1,
                "action": "MemorySearch",
                "action_input": "sales data",
                "observation": "No relevant memories found"
            },
            {
                "step_number": 2,
                "action": "DateTime",
                "action_input": "now",
                "observation": "Current date and time: 2025-12-28 02:30:45"
            }
        ],
        "total_steps": 3,
        "success": true
    }
    ```

    Args:
        request: AgentRequest with question and max_steps

    Returns:
        AgentResponse with answer and reasoning trace
    """
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Capture input to Redis Stream (non-blocking)
    await stream_handler.capture_input(request.question)

    try:
        # Build tool registry (basic + advanced tools)
        registry = ToolRegistry()

        # Register basic tools
        basic_tools = get_basic_tools()
        for tool_name, (description, func) in basic_tools.items():
            registry.register(tool_name, description, func)

        # Register advanced tools
        advanced_tools = get_advanced_tools()
        for tool_name, (description, func) in advanced_tools.items():
            registry.register(tool_name, description, func)

        # Run ReAct agent
        async with httpx.AsyncClient(timeout=config.REQUEST_TIMEOUT) as client:
            async with ReActAgent(registry, http_client=client) as agent:
                # Override max steps if specified
                if request.max_steps:
                    agent.MAX_STEPS = request.max_steps

                result = await agent.solve(request.question)

        # Convert steps to response model
        steps_response = [
            AgentStepResponse(
                step_number=step.step_number,
                thought=step.thought,
                action=step.action,
                action_input=step.action_input,
                observation=step.observation
            )
            for step in result.steps
        ]

        return AgentResponse(
            answer=result.answer,
            steps=steps_response,
            total_steps=result.total_steps,
            success=result.success,
            error=result.error
        )

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Vorpal engine error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {str(e)}"
        )


@app.get("/memories", response_model=MemoryListResponse, tags=["memory"])
async def list_memories(limit: int = 50, offset: int = 0) -> MemoryListResponse:
    """
    List all stored memories

    Retrieve memories with pagination, sorted by timestamp (newest first).
    Only memories with surprise score >= 0.7 are stored.

    **Query Parameters:**
    - `limit`: Max memories to return (default: 50, max: 100)
    - `offset`: Number to skip for pagination (default: 0)

    **Example Request:**
    ```
    GET /memories?limit=10&offset=0
    ```

    **Example Response:**
    ```json
    {
        "memories": [
            {
                "id": "memory:1766891131373",
                "message": "Search my memories for...",
                "perplexity": 95.66,
                "surprise_score": 0.949,
                "timestamp": 1766891131.37,
                "session_id": "default"
            }
        ],
        "total": 107
    }
    ```

    Args:
        limit: Maximum number of memories to return (default: 50)
        offset: Number of memories to skip (default: 0)

    Returns:
        MemoryListResponse with memories and total count
    """
    try:
        # Get all memory keys using SCAN
        cursor = 0
        all_keys = []

        while True:
            cursor, keys = vector_store.client.scan(
                cursor=cursor,
                match=f"{vector_store.prefix}*",
                count=100
            )
            all_keys.extend([k.decode() if isinstance(k, bytes) else k for k in keys])

            if cursor == 0:
                break

        # Sort by timestamp (newest first) - extract timestamp from key
        all_keys.sort(key=lambda k: int(k.split(':')[1]), reverse=True)

        # Apply pagination
        paginated_keys = all_keys[offset:offset + limit]

        # Fetch memory data
        memories = []
        for key in paginated_keys:
            data = vector_store.client.hgetall(key)

            # Decode bytes to strings
            decoded_data = {}
            for k, v in data.items():
                k_str = k.decode() if isinstance(k, bytes) else k

                # Skip binary embedding field
                if k_str == 'embedding':
                    continue

                v_str = v.decode() if isinstance(v, bytes) else v
                decoded_data[k_str] = v_str

            memories.append(MemoryItem(
                id=key,
                message=decoded_data.get('message', ''),
                perplexity=float(decoded_data.get('perplexity', 0)),
                surprise_score=float(decoded_data.get('surprise_score', 0)),
                timestamp=float(decoded_data.get('timestamp', 0)),
                session_id=decoded_data.get('session_id', 'default')
            ))

        return MemoryListResponse(
            memories=memories,
            total=len(all_keys)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing memories: {str(e)}"
        )


@app.post("/memories/search", response_model=MemoryListResponse, tags=["memory"])
async def search_memories(request: MemorySearchRequest) -> MemoryListResponse:
    """
    Semantic memory search

    Search memories using vector similarity (384-dim embeddings).
    Results are ranked by cosine similarity (lower score = more similar).

    **Example Request:**
    ```json
    {
        "query": "sales data",
        "top_k": 5,
        "session_id": null
    }
    ```

    **Example Response:**
    ```json
    {
        "memories": [
            {
                "id": "memory:1766888331119",
                "message": "Search my memories for 'sales data'...",
                "perplexity": 95.66,
                "surprise_score": 0.949,
                "timestamp": 1766888331.12,
                "session_id": "default",
                "similarity_score": 0.302
            }
        ],
        "total": 3
    }
    ```

    **Similarity Scores:**
    - 0.0 = Identical
    - 0.3 = Very similar
    - 0.5 = Moderately similar
    - 0.7+ = Less similar

    Args:
        request: MemorySearchRequest with query text and options

    Returns:
        MemoryListResponse with similar memories ranked by relevance
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        # Search using vector similarity
        results = vector_store.search_similar(
            query_text=request.query,
            top_k=request.top_k,
            session_id=request.session_id
        )

        # Convert to response model
        memories = [
            MemoryItem(
                id=mem['id'],
                message=mem['message'],
                perplexity=mem['perplexity'],
                surprise_score=mem['surprise_score'],
                timestamp=mem['timestamp'],
                session_id=mem['session_id'],
                similarity_score=mem['similarity_score']
            )
            for mem in results
        ]

        return MemoryListResponse(
            memories=memories,
            total=len(memories)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching memories: {str(e)}"
        )


@app.get("/memories/{memory_id}", tags=["memory"])
async def get_memory(memory_id: str) -> MemoryItem:
    """
    Get specific memory by ID

    Retrieve detailed information about a single memory.

    **Path Parameters:**
    - `memory_id`: Full memory key (e.g., 'memory:1766891131373')
      or just the timestamp (e.g., '1766891131373')

    **Example Request:**
    ```
    GET /memories/memory:1766891131373
    ```

    **Example Response:**
    ```json
    {
        "id": "memory:1766891131373",
        "message": "Search my memories for any information about 'sales data'...",
        "perplexity": 95.66,
        "surprise_score": 0.949,
        "timestamp": 1766891131.37,
        "session_id": "default"
    }
    ```

    Args:
        memory_id: Memory key (e.g., 'memory:1234567890')

    Returns:
        MemoryItem with memory details

    Raises:
        404: Memory not found
    """
    try:
        # Ensure memory_id has correct prefix
        if not memory_id.startswith(vector_store.prefix):
            memory_id = f"{vector_store.prefix}{memory_id}"

        # Check if memory exists
        if not vector_store.client.exists(memory_id):
            raise HTTPException(status_code=404, detail="Memory not found")

        # Fetch memory data
        data = vector_store.client.hgetall(memory_id)

        # Decode bytes to strings
        decoded_data = {}
        for k, v in data.items():
            k_str = k.decode() if isinstance(k, bytes) else k

            # Skip binary embedding field
            if k_str == 'embedding':
                continue

            v_str = v.decode() if isinstance(v, bytes) else v
            decoded_data[k_str] = v_str

        return MemoryItem(
            id=memory_id,
            message=decoded_data.get('message', ''),
            perplexity=float(decoded_data.get('perplexity', 0)),
            surprise_score=float(decoded_data.get('surprise_score', 0)),
            timestamp=float(decoded_data.get('timestamp', 0)),
            session_id=decoded_data.get('session_id', 'default')
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching memory: {str(e)}"
        )


@app.delete("/memories/{memory_id}", tags=["memory"])
async def delete_memory(memory_id: str) -> Dict[str, str]:
    """
    Delete memory by ID

    Permanently remove a memory from the vector store.

    **Path Parameters:**
    - `memory_id`: Full memory key or timestamp

    **Example Request:**
    ```
    DELETE /memories/memory:1766891131373
    ```

    **Example Response:**
    ```json
    {
        "status": "deleted",
        "id": "memory:1766891131373"
    }
    ```

    Args:
        memory_id: Memory key (e.g., 'memory:1234567890')

    Returns:
        Success message with deleted memory ID

    Raises:
        404: Memory not found
    """
    try:
        # Ensure memory_id has correct prefix
        if not memory_id.startswith(vector_store.prefix):
            memory_id = f"{vector_store.prefix}{memory_id}"

        # Check if memory exists
        if not vector_store.client.exists(memory_id):
            raise HTTPException(status_code=404, detail="Memory not found")

        # Delete memory
        vector_store.client.delete(memory_id)

        return {"status": "deleted", "id": memory_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting memory: {str(e)}"
        )


# ==================== LIBRARY ENDPOINTS (Phase 5.2) ====================

@app.post("/library/search", response_model=LibrarySearchResponse, tags=["library"])
async def search_library(request: LibrarySearchRequest) -> LibrarySearchResponse:
    """
    Search ingested library documents

    Search processed library chunks using vector similarity.
    Results include text, filename, chunk position, and similarity scores.

    **Example Request:**
    ```json
    {
        "query": "machine learning algorithms",
        "top_k": 5,
        "filter_file_type": null
    }
    ```

    **Example Response:**
    ```json
    {
        "chunks": [
            {
                "text": "Machine learning algorithms can be...",
                "filename": "ml-guide.pdf",
                "file_type": "pdf",
                "chunk_index": 3,
                "total_chunks": 10,
                "tokens": 245,
                "timestamp": 1766892000,
                "similarity_score": 0.15,
                "similarity_pct": 85.0
            }
        ],
        "total": 5,
        "query": "machine learning algorithms"
    }
    ```

    Args:
        request: LibrarySearchRequest with query and filters

    Returns:
        LibrarySearchResponse with matching chunks
    """
    from tools.library_search import get_library_search_tool

    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        # Get library search tool
        library_tool = get_library_search_tool()

        # Execute search
        results = library_tool.search(
            query=request.query,
            top_k=request.top_k,
            filter_file_type=request.filter_file_type
        )

        # Format response
        chunks = [LibraryChunk(**chunk) for chunk in results]

        return LibrarySearchResponse(
            chunks=chunks,
            total=len(chunks),
            query=request.query
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching library: {str(e)}"
        )


@app.get("/library/stats", response_model=LibraryStats, tags=["library"])
async def get_library_stats() -> LibraryStats:
    """
    Get library statistics

    Returns information about ingested library documents.

    **Example Response:**
    ```json
    {
        "total_chunks": 142,
        "unique_files": 8,
        "files": [
            "ml-guide.pdf",
            "python-basics.txt",
            "project-notes.md"
        ]
    }
    ```

    Returns:
        LibraryStats with chunk and file counts
    """
    from tools.library_search import get_library_search_tool

    try:
        library_tool = get_library_search_tool()
        stats = library_tool.get_stats()

        return LibraryStats(**stats)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting library stats: {str(e)}"
        )


# ============================================================================
# Research Assistant Endpoints (Phase 5.4)
# ============================================================================

@app.post("/research", response_model=ResearchResponse, tags=["research"])
async def research_question(request: ResearchRequest) -> ResearchResponse:
    """
    Research a question using library and/or memory sources.

    The research assistant searches both ingested library documents and
    conversation memories, then synthesizes an answer with citations.

    **Example Request:**
    ```json
    {
        "question": "What is vector search?",
        "use_library": true,
        "use_memory": true,
        "top_k": 5
    }
    ```

    **Example Response:**
    ```json
    {
        "question": "What is vector search?",
        "answer": "Vector search uses embeddings to find semantically similar content [Source 1]...",
        "sources": [...],
        "library_chunks_consulted": 3,
        "memories_consulted": 2,
        "total_sources": 5,
        "success": true
    }
    ```

    Args:
        request: ResearchRequest with question and search options

    Returns:
        ResearchResponse with synthesized answer and sources
    """
    from agents.research_agent import research_query

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
            error=result.error
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Research error: {str(e)}"
        )


@app.post("/research/multi", tags=["research"])
async def research_multiple_questions(request: MultiResearchRequest) -> Dict:
    """
    Research multiple related questions with optional synthesis.

    Useful for exploring a topic from multiple angles.

    **Example Request:**
    ```json
    {
        "questions": [
            "What is HNSW?",
            "How does cosine similarity work?",
            "What are vector embeddings?"
        ],
        "synthesize": true
    }
    ```

    Args:
        request: MultiResearchRequest with questions list

    Returns:
        Dictionary with individual results and optional synthesis
    """
    from agents.research_agent import multi_query_research

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


@app.post("/code_assist", response_model=CodeAssistResponse, tags=["agents"])
async def assist_with_code(request: CodeAssistRequest) -> CodeAssistResponse:
    """
    Code assistance with automated testing and debugging.

    Generates Python code from natural language task description,
    tests it in the sandbox, and debugs if errors occur (max 3 attempts).

    Supports:
    - Python functions and scripts
    - Automated testing with sample inputs
    - Error detection and debugging
    - Clean code with explanations

    Example:
        POST /code_assist
        {
            "task": "Write a function to calculate fibonacci numbers recursively, then test it with n=10",
            "max_attempts": 3,
            "timeout": 10
        }
    """
    from agents.code_agent import code_assist

    if not request.task or not request.task.strip():
        raise HTTPException(status_code=400, detail="Task cannot be empty")

    # Validate parameters
    if request.max_attempts < 1 or request.max_attempts > 5:
        raise HTTPException(
            status_code=400,
            detail="max_attempts must be between 1 and 5"
        )

    if request.timeout < 1 or request.timeout > 30:
        raise HTTPException(
            status_code=400,
            detail="timeout must be between 1 and 30 seconds"
        )

    try:
        result = await code_assist(
            task=request.task,
            max_attempts=request.max_attempts,
            timeout=request.timeout
        )

        return CodeAssistResponse(
            task=result.task,
            code=result.code,
            explanation=result.explanation,
            test_output=result.test_output,
            success=result.success,
            attempts=result.attempts,
            error=result.error
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Code assistance error: {str(e)}"
        )


@app.post("/admin/archive_old_memories", tags=["admin"])
async def trigger_manual_archival():
    """
    Manually trigger memory archival to disk (Chunk 5.6).

    Archives memories older than configured threshold (default 30 days)
    and keeps only most recent memories in Redis (default 1000).

    Returns:
        Archival statistics including count archived, kept, and files created
    """
    from workers.archiver import archiver

    try:
        result = await archiver.run_manual_archival()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Archival error: {str(e)}"
        )


@app.get("/admin/archive_stats", tags=["admin"])
async def get_archive_statistics():
    """
    Get statistics about archived memories (Chunk 5.6).

    Returns:
        Dictionary with total files, total memories, date range, etc.
    """
    from memory.cold_storage import ColdStorageManager

    try:
        storage = ColdStorageManager()
        stats = storage.get_archive_stats()
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Stats error: {str(e)}"
        )


@app.post("/admin/search_archive", tags=["admin"])
async def search_archived_memories(query: str, max_results: int = 10):
    """
    Search archived memories on disk (Chunk 5.6).

    Slower than Redis search, but searches all archived memories.

    Args:
        query: Search query string
        max_results: Maximum number of results (default 10)

    Returns:
        List of matching memories from archive files
    """
    from memory.cold_storage import ColdStorageManager

    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    if max_results < 1 or max_results > 100:
        raise HTTPException(
            status_code=400,
            detail="max_results must be between 1 and 100"
        )

    try:
        storage = ColdStorageManager()
        results = storage.search_archive(query, max_results)
        return {
            "query": query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Archive search error: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
