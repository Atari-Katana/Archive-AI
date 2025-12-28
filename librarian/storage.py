"""
Library Storage Module
Stores processed document chunks in RedisVL with embeddings.
Archive-AI v7.5 - Phase 5.2
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib

from redisvl.index import SearchIndex
from redisvl.query import VectorQuery
from redisvl.query.filter import Tag
from redisvl.utils.vectorize import HFTextVectorizer
import redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LibraryStorage:
    """Handles storage of library chunks in RedisVL"""

    def __init__(
        self,
        redis_url: str = "redis://redis:6379",
        index_name: str = "library_index",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        """
        Initialize library storage.

        Args:
            redis_url: Redis connection URL
            index_name: Name for the vector search index
            embedding_model: HuggingFace model for embeddings
        """
        self.redis_url = redis_url
        self.index_name = index_name
        self.embedding_model_name = embedding_model

        # Initialize Redis client with default encoding
        # RedisVL handles vector serialization internally
        self.redis_client = redis.from_url(
            redis_url,
            decode_responses=False,
            encoding='utf-8',
            encoding_errors='strict'
        )

        # Initialize HFTextVectorizer (RedisVL's built-in vectorizer)
        logger.info(f"Loading vectorizer: {embedding_model}")
        self.vectorizer = HFTextVectorizer(model=embedding_model)
        self.embedding_dim = self.vectorizer.dims

        logger.info(f"Embedding dimension: {self.embedding_dim}")

        # Initialize search index
        self._init_index()

        logger.info(f"LibraryStorage initialized: {index_name}")

    def _init_index(self):
        """Initialize or connect to RedisVL search index"""
        # Define index schema
        schema = {
            "index": {
                "name": self.index_name,
                "prefix": "library:",
                "storage_type": "hash",
            },
            "fields": [
                {
                    "name": "text",
                    "type": "text"
                },
                {
                    "name": "embedding",
                    "type": "vector",
                    "attrs": {
                        "dims": self.embedding_dim,
                        "algorithm": "hnsw",
                        "distance_metric": "cosine"
                    }
                },
                {
                    "name": "filename",
                    "type": "text"
                },
                {
                    "name": "file_type",
                    "type": "tag"
                },
                {
                    "name": "chunk_index",
                    "type": "numeric"
                },
                {
                    "name": "total_chunks",
                    "type": "numeric"
                },
                {
                    "name": "tokens",
                    "type": "numeric"
                },
                {
                    "name": "timestamp",
                    "type": "numeric"
                },
                {
                    "name": "doc_type",
                    "type": "tag"  # Always "library_book"
                }
            ]
        }

        try:
            # Try to create index
            self.index = SearchIndex.from_dict(schema)
            self.index.set_client(self.redis_client)
            self.index.create(overwrite=False)
            logger.info(f"Created new index: {self.index_name}")

        except Exception as e:
            # Index might already exist, try to connect
            logger.info(f"Connecting to existing index: {self.index_name}")
            self.index = SearchIndex.from_dict(schema)
            self.index.set_client(self.redis_client)

    def store_chunks(self, chunks: List[Dict[str, Any]], file_path: str):
        """
        Store document chunks with embeddings.

        Args:
            chunks: List of chunk dictionaries from DocumentProcessor
            file_path: Path to original file (for logging)
        """
        try:
            # Prepare all data and keys for batch loading
            all_data = []
            all_keys = []

            for chunk in chunks:
                # Generate embedding with RedisVL vectorizer (as bytes for Redis)
                text = chunk['text']
                embedding = self.vectorizer.embed(text, as_buffer=True)

                # Create unique ID (hash of text + filename + chunk_index)
                chunk_id = self._generate_chunk_id(
                    chunk['filename'],
                    chunk['chunk_index']
                )

                # Prepare data for storage
                data = {
                    "text": text,
                    "embedding": embedding,
                    "filename": chunk['filename'],
                    "file_type": chunk['file_type'],
                    "chunk_index": chunk['chunk_index'],
                    "total_chunks": chunk['total_chunks'],
                    "tokens": chunk['tokens'],
                    "timestamp": chunk['timestamp'],
                    "doc_type": "library_book"  # Tag for filtering
                }

                all_data.append(data)
                all_keys.append(f"library:{chunk_id}")

                logger.debug(
                    f"Prepared chunk {chunk['chunk_index']}/{chunk['total_chunks']} "
                    f"from {chunk['filename']}"
                )

            # Batch load all chunks at once
            self.index.load(all_data, keys=all_keys)

            stored_count = len(chunks)

            logger.info(
                f"✅ Stored {stored_count} chunks from {file_path.name if hasattr(file_path, 'name') else file_path}"
            )

        except Exception as e:
            logger.error(f"Error storing chunks from {file_path}: {str(e)}")
            raise

    def _generate_chunk_id(self, filename: str, chunk_index: int) -> str:
        """
        Generate unique ID for chunk.

        Args:
            filename: Source filename
            chunk_index: Index of chunk in document

        Returns:
            Unique hash-based ID
        """
        # Create deterministic ID based on filename and chunk index
        content = f"{filename}:{chunk_index}"
        return hashlib.md5(content.encode()).hexdigest()

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
            top_k: Number of results to return
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
                formatted_results.append({
                    "text": result.get("text", ""),
                    "filename": result.get("filename", ""),
                    "file_type": result.get("file_type", ""),
                    "chunk_index": int(result.get("chunk_index", 0)),
                    "total_chunks": int(result.get("total_chunks", 0)),
                    "tokens": int(result.get("tokens", 0)),
                    "timestamp": int(result.get("timestamp", 0)),
                    "similarity_score": float(result.get("vector_distance", 0.0))
                })

            logger.info(f"Found {len(formatted_results)} results for query: {query[:50]}...")
            return formatted_results

        except Exception as e:
            logger.error(f"Error searching library: {str(e)}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored library chunks.

        Returns:
            Dictionary with stats (total_chunks, file_count, etc.)
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
                    filenames.add(filename)

            return {
                "total_chunks": total_count,
                "unique_files": len(filenames),
                "index_name": self.index_name,
                "embedding_model": self.embedding_model_name
            }

        except Exception as e:
            logger.error(f"Error getting stats: {str(e)}")
            return {"error": str(e)}


# Standalone test
def test_storage():
    """Test the library storage system"""
    import tempfile
    from pathlib import Path
    from processor import DocumentProcessor

    print("\n🧪 Testing Library Storage")
    print("===========================\n")

    # Create test document
    test_text = """
    Archive-AI Library Storage Test

    This document tests the storage and search functionality.
    It should be processed, chunked, and stored in RedisVL.

    The storage system uses sentence-transformers for embeddings.
    Search queries should return semantically similar chunks.

    Vector search uses HNSW algorithm with cosine similarity.
    This provides fast approximate nearest neighbor search.
    """ * 3  # Repeat to create multiple chunks

    # Create temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(test_text)
        temp_path = Path(f.name)

    try:
        # Process document
        processor = DocumentProcessor(chunk_size=100, chunk_overlap=20)
        chunks = processor.process_document(str(temp_path))

        print(f"📄 Processed document: {len(chunks)} chunks\n")

        # Store chunks
        storage = LibraryStorage()
        storage.store_chunks(chunks, temp_path)

        print(f"💾 Stored {len(chunks)} chunks\n")

        # Test search
        queries = [
            "vector search algorithm",
            "document processing",
            "memory architecture"
        ]

        for query in queries:
            print(f"🔍 Query: '{query}'")
            results = storage.search(query, top_k=2)

            for i, result in enumerate(results, 1):
                print(f"  {i}. {result['filename']} (chunk {result['chunk_index']})")
                print(f"     Score: {result['similarity_score']:.4f}")
                print(f"     Text: {result['text'][:80]}...\n")

        # Get stats
        stats = storage.get_stats()
        print(f"📊 Stats: {stats}\n")

        print("✅ All tests passed!")

    finally:
        temp_path.unlink()


if __name__ == "__main__":
    test_storage()
