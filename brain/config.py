"""
Archive-Brain Configuration
Central configuration for the orchestrator.
"""

import os


class Config:
    """Application configuration"""

    # Service URLs
    VORPAL_URL = os.getenv("VORPAL_URL", "http://vorpal:8000")
    GOBLIN_URL = os.getenv("GOBLIN_URL", "http://goblin:8080")
    SANDBOX_URL = os.getenv("SANDBOX_URL", "http://sandbox:8000")
    VOICE_URL = os.getenv("VOICE_URL", "http://voice:8001")
    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
    BRAIN_URL = "http://localhost:8080"  # Internal brain URL for agents
    MEMORY_LAST_ID_KEY = os.getenv("MEMORY_LAST_ID_KEY", "memory_worker:last_id")
    MEMORY_START_FROM_LATEST = os.getenv("MEMORY_START_FROM_LATEST", "true").lower() == "true"

    # Feature flags
    ASYNC_MEMORY = os.getenv("ASYNC_MEMORY", "true").lower() == "true"
    ENABLE_VOICE = os.getenv("ENABLE_VOICE", "false").lower() == "true"

    # Brain settings
    DEFAULT_ENGINE = "vorpal"
    REQUEST_TIMEOUT = 30  # seconds

    # Model names
    VORPAL_MODEL = "Qwen/Qwen2.5-3B-Instruct"  # Scout model for chat/routing

    # Redis settings
    REDIS_STREAM_KEY = "session:input_stream"
    REDIS_MEMORY_PREFIX = "memory:"

    # Cold storage archival settings (Chunk 5.6)
    ARCHIVE_DAYS_THRESHOLD = int(os.getenv("ARCHIVE_DAYS_THRESHOLD", "30"))  # Archive after 30 days
    ARCHIVE_KEEP_RECENT = int(os.getenv("ARCHIVE_KEEP_RECENT", "1000"))  # Keep 1000 most recent in Redis
    ARCHIVE_HOUR = int(os.getenv("ARCHIVE_HOUR", "3"))  # Run at 3 AM
    ARCHIVE_MINUTE = int(os.getenv("ARCHIVE_MINUTE", "0"))  # Run at :00
    ARCHIVE_ENABLED = os.getenv("ARCHIVE_ENABLED", "true").lower() == "true"


config = Config()
