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
import traceback
import logging

from config import config
from memory.vector_store import VectorStore

logger = logging.getLogger(__name__)


class MemoryWorker:
    """Background worker for async memory processing"""

    # Surprise score threshold for memory storage
    SURPRISE_THRESHOLD = 0.7
    # Weights for surprise score calculation
    PERPLEXITY_WEIGHT = 0.6
    VECTOR_DISTANCE_WEIGHT = 0.4
    # Perplexity normalization constants
    PERPLEXITY_LOG_OFFSET = 1.0  # Offset to prevent log(0)
    PERPLEXITY_LOG_DIVISOR = 5.0  # Scale factor for normalization
    PERPLEXITY_FALLBACK = 1.0  # Neutral perplexity when calculation fails
    # Vector distance constants
    VECTOR_MAX_NOVELTY = 1.0  # Maximum novelty when no similar memories exist
    VECTOR_DEFAULT_NOVELTY = 0.5  # Default novelty on error
    VECTOR_SEARCH_LIMIT = 1  # Number of similar memories to search
    # Retry settings for perplexity calls
    PERPLEXITY_RETRIES = 3
    PERPLEXITY_RETRY_DELAY = 2.0  # seconds

    def __init__(self):
        self.redis_client: Optional[redis_async.Redis] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self.vector_store: Optional[VectorStore] = None
        self.running = False
        self.last_id: Optional[str] = None  # Populated during connect

    async def connect(self):
        """Initialize connections"""
        self.redis_client = await redis_async.from_url(
            config.REDIS_URL,
            decode_responses=True
        )
        # Give Vorpal plenty of time to load on cold start
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=10.0)
        )

        # Wait for Vorpal health before starting the worker loop
        await self.wait_for_vorpal_ready()

        # Load last processed stream ID (or start strategy)
        await self.load_last_id()

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
            await self.http_client.aclose()
        if self.vector_store:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.vector_store.close
            )

    async def load_last_id(self) -> None:
        """Load last processed stream ID and decide where to start."""
        if not self.redis_client:
            self.last_id = "0"
            return

        saved = await self.redis_client.get(config.MEMORY_LAST_ID_KEY)
        if saved:
            self.last_id = saved
            logger.info("Resuming from last_id=%s", self.last_id)
        elif config.MEMORY_START_FROM_LATEST:
            self.last_id = "$"
            logger.info("Starting from latest stream entry ($)")
        else:
            self.last_id = "0"
            logger.info("Starting from beginning of stream (0)")

    async def wait_for_vorpal_ready(self, timeout: int = 120) -> None:
        """Wait for Vorpal to be reachable before processing messages."""
        if not self.http_client:
            return

        deadline = asyncio.get_event_loop().time() + timeout
        attempt = 1

        while True:
            try:
                response = await self.http_client.get(
                    f"{config.VORPAL_URL}/health",
                    timeout=10.0
                )
                if response.status_code == 200:
                    logger.info("Vorpal is ready")
                    return

                logger.warning(
                    "Vorpal health check failed with status %s",
                    response.status_code
                )
            except Exception as exc:
                logger.warning(
                    "Vorpal health check attempt %s failed: %s",
                    attempt,
                    exc
                )

            if asyncio.get_event_loop().time() >= deadline:
                logger.warning("Vorpal readiness check timed out; continuing anyway")
                return

            attempt += 1
            await asyncio.sleep(2.0)

    async def calculate_perplexity(self, text: str) -> Optional[float]:
        """
        Calculate perplexity of text using Vorpal.

        Args:
            text: Input text to evaluate

        Returns:
            Perplexity score (lower = more predictable)
        """
        # Request logprobs from Vorpal
        payload = {
            "model": config.VORPAL_MODEL,
            "prompt": text,
            "max_tokens": 1,  # We just need logprobs, not generation
            "logprobs": 1,
            "echo": True  # Return logprobs for input tokens
        }

        for attempt in range(1, self.PERPLEXITY_RETRIES + 1):
            try:
                response = await self.http_client.post(
                    f"{config.VORPAL_URL}/v1/completions",
                    json=payload
                )

                if response.status_code != 200:
                    logger.warning(
                        "Vorpal error (attempt %s): %s",
                        attempt,
                        response.status_code
                    )
                    await asyncio.sleep(self.PERPLEXITY_RETRY_DELAY)
                    continue

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
                logger.exception(
                    "Perplexity calculation error (attempt %s): %s",
                    attempt,
                    e
                )

            if attempt < self.PERPLEXITY_RETRIES:
                await asyncio.sleep(self.PERPLEXITY_RETRY_DELAY)

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
                self.VECTOR_SEARCH_LIMIT,
                None  # No session filter
            )

            if not similar:
                # No existing memories, maximum novelty
                return self.VECTOR_MAX_NOVELTY

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
            logger.error("Vector distance calculation error: %s", e)
            # Default to medium novelty on error
            return self.VECTOR_DEFAULT_NOVELTY

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
        normalized_perplexity = min(
            1.0,
            math.log(perplexity + self.PERPLEXITY_LOG_OFFSET) / self.PERPLEXITY_LOG_DIVISOR
        )

        # Calculate weighted surprise score
        surprise = (
            self.PERPLEXITY_WEIGHT * normalized_perplexity +
            self.VECTOR_DISTANCE_WEIGHT * vector_distance
        )

        return surprise

    async def process_entry(self, entry_id: str, entry_data: dict) -> bool:
        """
        Process a single stream entry.
        Calculates surprise score and stores if > threshold.

        Args:
            entry_id: Redis stream entry ID
            entry_data: Entry data dict

        Returns:
            True if processing completed successfully (stored or skipped),
            False if storage failed and entry should be retried
        """
        message = entry_data.get("message", "")
        timestamp = entry_data.get("timestamp", "")

        if not message:
            return True  # Empty message, nothing to do

        # Calculate perplexity
        perplexity = await self.calculate_perplexity(message)
        perplexity_failed = False
        if perplexity is None:
            # CRITICAL: Perplexity calculation failed after all retries
            # Store with fallback value instead of dropping the memory entirely
            logger.error(
                "CRITICAL: Failed to calculate perplexity after %s retries for: %s... "
                "Using fallback perplexity=%s",
                self.PERPLEXITY_RETRIES,
                message[:50],
                self.PERPLEXITY_FALLBACK
            )
            perplexity = self.PERPLEXITY_FALLBACK
            perplexity_failed = True

        # Calculate vector distance (novelty)
        vector_distance = await self.calculate_vector_distance(message)

        # Calculate surprise score
        surprise_score = self.calculate_surprise_score(
            perplexity,
            vector_distance
        )

        # Log results
        logger.info(
            "Message: %s... perplexity=%.2f vector_distance=%.3f surprise=%.3f",
            message[:50],
            perplexity,
            vector_distance,
            surprise_score
        )

        # Store memory if surprising enough
        if surprise_score >= self.SURPRISE_THRESHOLD:
            try:
                # Include perplexity failure flag in metadata
                metadata = {
                    "timestamp": timestamp,
                    "entry_id": entry_id,
                    "perplexity_fallback": perplexity_failed
                }
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.vector_store.store_memory,
                    message,
                    perplexity,
                    surprise_score,
                    "default",  # session_id
                    metadata
                )
                logger.info("Stored memory (surprise >= %s)", self.SURPRISE_THRESHOLD)
                return True  # Storage successful
            except Exception as e:
                logger.exception("Storage error: %s", e)
                return False  # Storage failed, should retry
        else:
            logger.info("Skipped (surprise < %s)", self.SURPRISE_THRESHOLD)
            return True  # Intentionally skipped, mark as processed

    async def run(self):
        """Main worker loop - reads from stream and processes entries"""
        self.running = True
        logger.info("Starting background worker...")

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
                        try:
                            success = await self.process_entry(entry_id, entry_data)
                            if success:
                                # Only update last_id after successful processing
                                self.last_id = entry_id
                                if self.redis_client:
                                    await self.redis_client.set(
                                        config.MEMORY_LAST_ID_KEY,
                                        self.last_id
                                    )
                            else:
                                logger.error(
                                    "Processing failed for entry %s, will retry next iteration",
                                    entry_id
                                )
                                # Don't update last_id - will retry this entry next iteration
                                break
                        except Exception as e:
                            logger.error(
                                "Failed to process entry %s: %s. Stopping batch to prevent data loss.",
                                entry_id, e
                            )
                            # Don't update last_id - will retry this entry next iteration
                            break

            except asyncio.CancelledError:
                logger.info("Worker cancelled, shutting down...")
                break
            except Exception as e:
                logger.exception("Error in worker loop: %s", e)
                await asyncio.sleep(1)  # Prevent tight error loop

        logger.info("Background worker stopped")


# Global instance
memory_worker = MemoryWorker()
