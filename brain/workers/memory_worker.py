"""
Memory Worker (Chunk 2.5)
Background worker that processes inputs from Redis Stream.
Calculates surprise score (perplexity + vector distance).
Stores surprising memories in vector store.
"""

import asyncio
import httpx
import redis.asyncio as redis_async
from typing import Optional
import math

from config import config
from memory.vector_store import VectorStore


class MemoryWorker:
    """Background worker for async memory processing"""

    # Surprise score threshold for memory storage
    SURPRISE_THRESHOLD = 0.7
    # Weights for surprise score calculation
    PERPLEXITY_WEIGHT = 0.6
    VECTOR_DISTANCE_WEIGHT = 0.4

    def __init__(self):
        self.redis_client: Optional[redis_async.Redis] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self.vector_store: Optional[VectorStore] = None
        self.running = False
        self.last_id = "0"  # Start from beginning of stream

    async def connect(self):
        """Initialize connections"""
        self.redis_client = await redis_async.from_url(
            config.REDIS_URL,
            decode_responses=True
        )
        self.http_client = httpx.AsyncClient(timeout=30.0)

        # Initialize vector store (sync operation run in executor)
        self.vector_store = VectorStore(redis_url=config.REDIS_URL)
        await asyncio.get_event_loop().run_in_executor(
            None,
            self.vector_store.connect
        )
        await asyncio.get_event_loop().run_in_executor(
            None,
            self.vector_store.create_index
        )

    async def close(self):
        """Close connections"""
        self.running = False
        if self.redis_client:
            await self.redis_client.close()
        if self.http_client:
            await self.http_client.close()
        if self.vector_store:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.vector_store.close
            )

    async def calculate_perplexity(self, text: str) -> Optional[float]:
        """
        Calculate perplexity of text using Vorpal.

        Args:
            text: Input text to evaluate

        Returns:
            Perplexity score (lower = more predictable)
        """
        try:
            # Request logprobs from Vorpal
            payload = {
                "model": "Qwen/Qwen2.5-3B-Instruct",
                "prompt": text,
                "max_tokens": 1,  # We just need logprobs, not generation
                "logprobs": 1,
                "echo": True  # Return logprobs for input tokens
            }

            response = await self.http_client.post(
                f"{config.VORPAL_URL}/v1/completions",
                json=payload
            )

            if response.status_code != 200:
                print(f"Vorpal error: {response.status_code}")
                return None

            result = response.json()

            # Extract logprobs from response
            choices = result.get("choices", [])
            if not choices:
                return None

            logprobs_data = choices[0].get("logprobs", {})
            token_logprobs = logprobs_data.get("token_logprobs", [])

            if not token_logprobs:
                return None

            # Calculate perplexity from average log probability
            # Perplexity = exp(-average_log_prob)
            valid_logprobs = [lp for lp in token_logprobs if lp is not None]
            if not valid_logprobs:
                return None

            avg_logprob = sum(valid_logprobs) / len(valid_logprobs)
            perplexity = math.exp(-avg_logprob)

            return perplexity

        except Exception as e:
            print(f"Perplexity calculation error: {e}")
            return None

    async def calculate_vector_distance(self, text: str) -> float:
        """
        Calculate vector distance (novelty) by comparing with recent memories.

        Args:
            text: Input text to evaluate

        Returns:
            Vector distance score (0.0 = very similar, 1.0 = very different)
        """
        try:
            # Search for similar memories
            similar = await asyncio.get_event_loop().run_in_executor(
                None,
                self.vector_store.search_similar,
                text,
                1,  # Get closest match only
                None  # No session filter
            )

            if not similar:
                # No existing memories, maximum novelty
                return 1.0

            # Get similarity score of closest match
            # Similarity scores from cosine distance are [0, 1]
            # where lower is more similar
            similarity = similar[0]["similarity_score"]

            # Convert to distance (higher = more novel)
            # If similarity is low (close match), distance is low
            # If similarity is high (far match), distance is high
            vector_distance = similarity

            return vector_distance

        except Exception as e:
            print(f"Vector distance calculation error: {e}")
            # Default to medium novelty on error
            return 0.5

    def calculate_surprise_score(
        self,
        perplexity: float,
        vector_distance: float
    ) -> float:
        """
        Calculate surprise score from perplexity and vector distance.

        Formula: surprise = 0.6 * perplexity + 0.4 * vector_distance

        Args:
            perplexity: Perplexity score (normalized to [0, 1])
            vector_distance: Vector distance score (0.0 = similar, 1.0 = novel)

        Returns:
            Surprise score (0.0 = not surprising, 1.0 = very surprising)
        """
        # Normalize perplexity to [0, 1] range
        # Typical perplexity values: 1-100+
        # Use log scale for better distribution
        normalized_perplexity = min(1.0, math.log(perplexity + 1) / 5.0)

        # Calculate weighted surprise score
        surprise = (
            self.PERPLEXITY_WEIGHT * normalized_perplexity +
            self.VECTOR_DISTANCE_WEIGHT * vector_distance
        )

        return surprise

    async def process_entry(self, entry_id: str, entry_data: dict):
        """
        Process a single stream entry.
        Calculates surprise score and stores if > threshold.

        Args:
            entry_id: Redis stream entry ID
            entry_data: Entry data dict
        """
        message = entry_data.get("message", "")
        timestamp = entry_data.get("timestamp", "")

        if not message:
            return

        # Calculate perplexity
        perplexity = await self.calculate_perplexity(message)
        if perplexity is None:
            print(f"[MemoryWorker] Failed to calculate perplexity "
                  f"for: {message[:50]}...")
            return

        # Calculate vector distance (novelty)
        vector_distance = await self.calculate_vector_distance(message)

        # Calculate surprise score
        surprise_score = self.calculate_surprise_score(
            perplexity,
            vector_distance
        )

        # Log results
        print(f"[MemoryWorker] Message: {message[:50]}...")
        print(f"[MemoryWorker] Perplexity: {perplexity:.2f}")
        print(f"[MemoryWorker] Vector Distance: {vector_distance:.3f}")
        print(f"[MemoryWorker] Surprise Score: {surprise_score:.3f}")

        # Store memory if surprising enough
        if surprise_score >= self.SURPRISE_THRESHOLD:
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.vector_store.store_memory,
                    message,
                    perplexity,
                    surprise_score,
                    "default",  # session_id
                    {"timestamp": timestamp, "entry_id": entry_id}
                )
                print(f"[MemoryWorker] ✅ STORED (surprise >= {self.SURPRISE_THRESHOLD})")
            except Exception as e:
                print(f"[MemoryWorker] Storage error: {e}")
        else:
            print(f"[MemoryWorker] ❌ SKIPPED (surprise < {self.SURPRISE_THRESHOLD})")

        print("-" * 60)

    async def run(self):
        """Main worker loop - reads from stream and processes entries"""
        self.running = True
        print("[MemoryWorker] Starting background worker...")

        while self.running:
            try:
                # Read new entries from stream (blocking with timeout)
                entries = await self.redis_client.xread(
                    {config.REDIS_STREAM_KEY: self.last_id},
                    count=10,
                    block=1000  # Block for 1 second
                )

                if not entries:
                    # No new entries, continue loop
                    continue

                # Process each entry
                for stream_key, stream_entries in entries:
                    for entry_id, entry_data in stream_entries:
                        await self.process_entry(entry_id, entry_data)
                        self.last_id = entry_id

            except asyncio.CancelledError:
                print("[MemoryWorker] Worker cancelled, shutting down...")
                break
            except Exception as e:
                print(f"[MemoryWorker] Error in worker loop: {e}")
                await asyncio.sleep(1)  # Prevent tight error loop

        print("[MemoryWorker] Background worker stopped")


# Global instance
memory_worker = MemoryWorker()
