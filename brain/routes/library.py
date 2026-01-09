from fastapi import APIRouter, HTTPException
from schemas.library import LibrarySearchResponse, LibrarySearchRequest, LibraryChunk, LibraryStats
from tools.library_search import get_library_search_tool

router = APIRouter(prefix="/library", tags=["library"])

@router.post("/search", response_model=LibrarySearchResponse)
async def search_library(request: LibrarySearchRequest):
    """
    Search ingested library documents
    """
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


@router.get("/stats", response_model=LibraryStats)
async def get_library_stats():
    """
    Get library statistics
    """
    try:
        library_tool = get_library_search_tool()
        stats = library_tool.get_stats()

        return LibraryStats(**stats)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting library stats: {str(e)}"
        )
