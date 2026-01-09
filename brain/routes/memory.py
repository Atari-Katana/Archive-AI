from fastapi import APIRouter, HTTPException
from typing import List, Dict
from schemas.memory import MemoryListResponse, MemoryItem, MemorySearchRequest
from memory.vector_store import vector_store

router = APIRouter(prefix="/memories", tags=["memory"])

@router.get("/", response_model=MemoryListResponse)
async def list_memories(limit: int = 50, offset: int = 0):
    """
    List all stored memories
    """
    try:
        # Ensure Redis connection is active
        vector_store.ensure_connected()

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

    except RuntimeError as e:
        # Redis connection issue
        raise HTTPException(
            status_code=503,
            detail=f"Memory service unavailable: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing memories: {str(e)}"
        )


@router.post("/search", response_model=MemoryListResponse)
async def search_memories(request: MemorySearchRequest):
    """
    Semantic memory search
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        # Ensure Redis connection is active
        vector_store.ensure_connected()

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

    except RuntimeError as e:
        # Redis connection issue
        raise HTTPException(
            status_code=503,
            detail=f"Memory service unavailable: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching memories: {str(e)}"
        )


@router.get("/{memory_id}")
async def get_memory(memory_id: str) -> MemoryItem:
    """
    Get specific memory by ID
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


@router.delete("/{memory_id}")
async def delete_memory(memory_id: str) -> Dict[str, str]:
    """
    Delete memory by ID
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
