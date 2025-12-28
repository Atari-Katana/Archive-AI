"""
Redis Stream Handler (Chunk 2.2)
Non-blocking input capture to Redis Stream for async memory processing.
"""

import time
import redis.asyncio as redis_async
from typing import Dict, Any

from config import config


class StreamHandler:
    """Handles writing user inputs to Redis Stream"""

    def __init__(self):
        self.redis_client = None

    async def connect(self):
        """Initialize Redis connection"""
        self.redis_client = await redis_async.from_url(
            config.REDIS_URL,
            decode_responses=True
        )

    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()

    async def capture_input(
        self,
        message: str,
        metadata: Dict[str, Any] = None
    ):
        """
        Capture user input to Redis Stream (non-blocking).

        Args:
            message: User's input message
            metadata: Optional metadata (user_id, session_id, etc.)
        """
        if not self.redis_client:
            await self.connect()

        try:
            # Prepare stream entry
            entry = {
                "message": message,
                "timestamp": str(time.time()),
            }

            # Add optional metadata
            if metadata:
                entry.update(metadata)

            # Write to stream (fire and forget - non-blocking)
            await self.redis_client.xadd(
                config.REDIS_STREAM_KEY,
                entry,
                maxlen=1000  # Keep last 1000 entries
            )

        except Exception as e:
            # Log error but don't block chat response
            print(f"Warning: Failed to capture input to stream: {e}")


# Global instance
stream_handler = StreamHandler()
