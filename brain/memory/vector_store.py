"""
Vector Store for Memory Storage (Chunk 2.4)
Uses RedisVL for vector storage and sentence-transformers for embeddings.
"""

import time
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

import redis
from sentence_transformers import SentenceTransformer
import numpy as np


class VectorStore:
    """Vector store for memory storage using RedisVL"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.client: Optional[redis.Redis] = None
        self.model: Optional[SentenceTransformer] = None
        self.index_name = "memory_index"
        self.prefix = "memory:"
        self.embedding_dim = 384  # all-MiniLM-L6-v2 dimension

    def connect(self):
        """Initialize Redis connection and sentence transformer model"""
        self.client = redis.from_url(
            self.redis_url,
            decode_responses=False  # Binary mode for vectors
        )

        # Load sentence-transformers model (CPU)
        print("[VectorStore] Loading sentence-transformers model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        print("[VectorStore] Model loaded")

    def create_index(self):
        """
        Create RediSearch index for memory storage.
        Idempotent - skips if index already exists.
        """
        try:
            # Check if index exists
            try:
                self.client.ft(self.index_name).info()
                print(f"[VectorStore] Index '{self.index_name}' already exists")
                return
            except redis.exceptions.ResponseError:
                # Index doesn't exist, create it
                pass

            # Create index using FT.CREATE command
            # Schema: message (TEXT), embedding (VECTOR), perplexity (NUMERIC),
            #         surprise_score (NUMERIC), timestamp (NUMERIC),
            #         session_id (TAG), metadata (TEXT)
            self.client.execute_command(
                "FT.CREATE", self.index_name,
                "ON", "HASH",
                "PREFIX", "1", self.prefix,
                "SCHEMA",
                "message", "TEXT",
                "embedding", "VECTOR", "HNSW", "6",
                "TYPE", "FLOAT32",
                "DIM", str(self.embedding_dim),
                "DISTANCE_METRIC", "COSINE",
                "perplexity", "NUMERIC", "SORTABLE",
                "surprise_score", "NUMERIC", "SORTABLE",
                "timestamp", "NUMERIC", "SORTABLE",
                "session_id", "TAG",
                "metadata", "TEXT"
            )

            print(f"[VectorStore] Created index '{self.index_name}'")

        except Exception as e:
            print(f"[VectorStore] Error creating index: {e}")
            raise

    def close(self):
        """Close Redis connection"""
        if self.client:
            self.client.close()

    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding vector for text using sentence-transformers.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector (384 dimensions)
        """
        if not self.model:
            raise RuntimeError("Model not loaded. Call connect() first.")

        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding

    def store_memory(
        self,
        message: str,
        perplexity: float,
        surprise_score: Optional[float] = None,
        session_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store a memory with vector embedding.

        Args:
            message: The text message to store
            perplexity: Perplexity score for the message
            surprise_score: Optional surprise score (perplexity + vector distance)
            session_id: Session identifier
            metadata: Optional metadata dict

        Returns:
            Redis key of stored memory
        """
        # Generate embedding
        embedding = self.generate_embedding(message)

        # Create memory key
        timestamp = time.time()
        memory_key = f"{self.prefix}{int(timestamp * 1000)}"

        # Prepare memory data
        memory_data = {
            "message": message,
            "embedding": embedding.astype(np.float32).tobytes(),
            "perplexity": perplexity,
            "surprise_score": surprise_score if surprise_score else 0.0,
            "timestamp": timestamp,
            "session_id": session_id,
            "metadata": json.dumps(metadata) if metadata else "{}"
        }

        # Store in Redis
        self.client.hset(memory_key, mapping=memory_data)

        print(f"[VectorStore] Stored memory: {memory_key}")
        return memory_key

    def search_similar(
        self,
        query_text: str,
        top_k: int = 5,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar memories using vector similarity.

        Args:
            query_text: Text to search for
            top_k: Number of results to return
            session_id: Optional session filter

        Returns:
            List of similar memories with scores
        """
        # Generate query embedding
        query_embedding = self.generate_embedding(query_text)
        query_bytes = query_embedding.astype(np.float32).tobytes()

        # Build KNN query
        if session_id:
            # Escape special characters in tag value
            escaped_session = session_id.replace("_", "\\_")
            base_query = f"(@session_id:{{{escaped_session}}})=>[KNN {top_k} @embedding $vec AS score]"
        else:
            base_query = f"*=>[KNN {top_k} @embedding $vec AS score]"

        # Execute search using FT.SEARCH
        try:
            results = self.client.execute_command(
                "FT.SEARCH", self.index_name,
                base_query,
                "PARAMS", "2", "vec", query_bytes,
                "RETURN", "6", "message", "perplexity",
                "surprise_score", "timestamp", "session_id", "score",
                "SORTBY", "score",
                "DIALECT", "2",
                "LIMIT", "0", str(top_k)
            )
        except Exception as e:
            print(f"[VectorStore] Search error: {e}")
            return []

        # Parse results
        # Format: [count, key1, fields1, key2, fields2, ...]
        memories = []
        if not results or results[0] == 0:
            return memories

        # Skip the count, iterate over key-fields pairs
        for i in range(1, len(results), 2):
            key = results[i]
            fields = results[i + 1]

            # Decode key if bytes
            if isinstance(key, bytes):
                key = key.decode()

            # Convert field list to dict
            field_dict = {}
            for j in range(0, len(fields), 2):
                field_name = fields[j]
                field_value = fields[j + 1]

                # Decode bytes to strings
                if isinstance(field_name, bytes):
                    field_name = field_name.decode()
                if isinstance(field_value, bytes):
                    field_value = field_value.decode()

                field_dict[field_name] = field_value

            memories.append({
                "id": key,
                "message": field_dict.get("message", ""),
                "perplexity": float(field_dict.get("perplexity", 0)),
                "surprise_score": float(field_dict.get("surprise_score", 0)),
                "timestamp": float(field_dict.get("timestamp", 0)),
                "session_id": field_dict.get("session_id", ""),
                "similarity_score": float(field_dict.get("score", 1.0))
            })

        return memories


# Global instance
vector_store = VectorStore()
