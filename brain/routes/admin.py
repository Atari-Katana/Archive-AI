from fastapi import APIRouter, HTTPException
from schemas.memory import ArchiveStatsResponse, ArchiveSearchResponse, ArchiveSearchRequest
from workers.archiver import archiver
from memory.cold_storage import ColdStorageManager

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/archive_old_memories")
async def trigger_manual_archival():
    """
    Manually trigger memory archival to disk (Chunk 5.6).
    """
    try:
        result = await archiver.run_manual_archival()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Archival error: {str(e)}"
        )


@router.get("/archive_stats", response_model=ArchiveStatsResponse)
async def get_archive_statistics():
    """
    Get statistics about archived memories (Chunk 5.6).
    """
    try:
        storage = ColdStorageManager()
        stats = storage.get_archive_stats()
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Stats error: {str(e)}"
        )


@router.post("/search_archive", response_model=ArchiveSearchResponse)
async def search_archived_memories(request: ArchiveSearchRequest):
    """
    Search archived memories on disk (Chunk 5.6).
    """
    # Validate query
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    if len(request.query) > 500:
        raise HTTPException(status_code=400, detail="Query too long (max 500 characters)")

    # Validate max_results
    if request.max_results < 1 or request.max_results > 100:
        raise HTTPException(
            status_code=400,
            detail="max_results must be between 1 and 100"
        )

    try:
        storage = ColdStorageManager()
        results = storage.search_archive(request.query, request.max_results)
        return {
            "query": request.query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Archive search error: {str(e)}"
        )
