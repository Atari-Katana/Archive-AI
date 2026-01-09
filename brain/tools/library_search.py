"""
Library Search Tool
Searches ingested library documents using vector similarity.
Archive-AI v7.5 - Phase 5.2
"""

import logging
from typing import List, Dict, Any, Optional

from redisvl.index import SearchIndex
from redisvl.query import VectorQuery
from redisvl.query.filter import Tag
from redisvl.utils.vectorize import HFTextVectorizer
import redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LibrarySearchTool:
    """Tool for searching the ingested library"""

    def __init__(
        self,
        redis_url: str = "redis://redis:6379",
        index_name: str = "library_index",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        """
        Initialize library search tool.

        Args:
            redis_url: Redis connection URL
            index_name: Name of library index
            embedding_model: Model for generating query embeddings
        """
        self.redis_url = redis_url
        self.index_name = index_name

        # Initialize Redis client (no decode_responses for binary vector data)
        self.redis_client = redis.from_url(redis_url, decode_responses=False)

        # Initialize HFTextVectorizer (same as librarian uses)
        logger.info(f"Loading vectorizer for library search: {embedding_model}")
        self.vectorizer = HFTextVectorizer(model=embedding_model)

        # Connect to existing index
        self._connect_index()

        logger.info(f"LibrarySearchTool initialized")

    def _connect_index(self):
        """Connect to existing library index"""
        try:
            # Define schema (must match librarian's schema)
            schema = {
                "index": {
                    "name": self.index_name,
                    "prefix": "library:",
                    "storage_type": "hash",
                },
                "fields": [
                    {"name": "text", "type": "text"},
                    {
                        "name": "embedding",
                        "type": "vector",
                        "attrs": {
                            "dims": 384,  # all-MiniLM-L6-v2 dimension
                            "algorithm": "hnsw",
                            "distance_metric": "cosine"
                        }
                    },
                    {"name": "filename", "type": "text"},
                    {"name": "file_type", "type": "tag"},
                    {"name": "chunk_index", "type": "numeric"},
                    {"name": "total_chunks", "type": "numeric"},
                    {"name": "tokens", "type": "numeric"},
                    {"name": "timestamp", "type": "numeric"},
                    {"name": "doc_type", "type": "tag"}
                ]
            }

            self.index = SearchIndex.from_dict(schema)
            self.index.set_client(self.redis_client)

            logger.info(f"Connected to library index: {self.index_name}")

        except Exception as e:
            logger.error(f"Failed to connect to library index: {str(e)}")
            raise

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_file_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search library for relevant chunks.

        Args:
            query: Search query text
            top_k: Number of results to return (default: 5)
            filter_file_type: Optional filter by file type (pdf, txt, md)

        Returns:
            List of matching chunks with similarity scores
        """
        try:
            # Generate query embedding (as list for VectorQuery)
            query_embedding = self.vectorizer.embed(query)

            # Build vector query
            vector_query = VectorQuery(
                vector=query_embedding,
                vector_field_name="embedding",
                return_fields=[
                    "text", "filename", "file_type",
                    "chunk_index", "total_chunks", "tokens", "timestamp"
                ],
                num_results=top_k
            )

            # Add file type filter if specified
            if filter_file_type:
                vector_query.set_filter(Tag("file_type") == filter_file_type)

            # Execute search
            results = self.index.query(vector_query)

            # Format results
            formatted_results = []
            for result in results:
                # Convert vector_distance to similarity percentage
                # (lower distance = higher similarity)
                distance = float(result.get("vector_distance", 1.0))
                similarity_pct = max(0, (1.0 - distance) * 100)

                formatted_results.append({
                    "text": result.get("text", ""),
                    "filename": result.get("filename", ""),
                    "file_type": result.get("file_type", ""),
                    "chunk_index": int(result.get("chunk_index", 0)),
                    "total_chunks": int(result.get("total_chunks", 0)),
                    "tokens": int(result.get("tokens", 0)),
                    "timestamp": int(result.get("timestamp", 0)),
                    "similarity_score": distance,
                    "similarity_pct": similarity_pct
                })

            logger.info(f"Library search: '{query[:30]}...' → {len(formatted_results)} results")
            return formatted_results

        except Exception as e:
            logger.error(f"Error searching library: {str(e)}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the library.

        Returns:
            Dictionary with stats (total chunks, unique files, etc.)
        """
        try:
            # Count total library chunks
            cursor, keys = self.redis_client.scan(match="library:*", count=1000)
            total_count = len(keys)

            while cursor != 0:
                cursor, batch = self.redis_client.scan(cursor, match="library:*", count=1000)
                total_count += len(batch)

            # Get unique filenames
            filenames = set()
            for key in self.redis_client.scan_iter(match="library:*", count=100):
                filename = self.redis_client.hget(key, "filename")
                if filename:
                    if isinstance(filename, bytes):
                        filename = filename.decode('utf-8')
                    filenames.add(filename)

            return {
                "total_chunks": total_count,
                "unique_files": len(filenames),
                "files": list(filenames)
            }

        except Exception as e:
            logger.error(f"Error getting library stats: {str(e)}")
            return {"error": str(e)}


# Initialize global instance (lazy)
_library_search_tool: Optional[LibrarySearchTool] = None


def get_library_search_tool() -> LibrarySearchTool:
    """Get or create the global library search tool instance"""
    global _library_search_tool

    if _library_search_tool is None:
        _library_search_tool = LibrarySearchTool()

    return _library_search_tool
