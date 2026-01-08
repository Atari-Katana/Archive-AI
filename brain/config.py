"""
Archive-Brain Configuration
Central configuration for the orchestrator.
"""

import os


class Config:
    """Application configuration"""

    # Service URLs (internal Docker network)
    VORPAL_URL = os.getenv("VORPAL_URL", "http://vorpal:8000")
    GOBLIN_URL = os.getenv("GOBLIN_URL", "http://goblin:8080")
    SANDBOX_URL = os.getenv("SANDBOX_URL", "http://sandbox:8000")
    VOICE_URL = os.getenv("VOICE_URL", "http://voice:8001")
    BIFROST_URL = os.getenv("BIFROST_URL", "http://bifrost:8080")
    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

    # Public-facing URL (use PUBLIC_URL env var for Cloudflare/production, fallback to localhost)
    PUBLIC_URL = os.getenv("PUBLIC_URL", "http://localhost:8080")
    BRAIN_URL = PUBLIC_URL  # Used by agents and external references

    # Proxy settings (for Cloudflare, nginx, etc.)
    TRUST_PROXY = os.getenv("TRUST_PROXY", "false").lower() == "true"
    MEMORY_LAST_ID_KEY = os.getenv("MEMORY_LAST_ID_KEY", "memory_worker:last_id")
    MEMORY_START_FROM_LATEST = os.getenv("MEMORY_START_FROM_LATEST", "true").lower() == "true"
    LOG_DIR = os.getenv("LOG_DIR", "logs")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # Feature flags
    ASYNC_MEMORY = os.getenv("ASYNC_MEMORY", "true").lower() == "true"
    ENABLE_VOICE = os.getenv("ENABLE_VOICE", "true").lower() == "true"

    # Brain settings
    DEFAULT_ENGINE = "vorpal"
    REQUEST_TIMEOUT = 60  # Increased timeout for longer responses
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1024"))

    # HTTP Client timeouts (seconds)
    HEALTH_CHECK_TIMEOUT = float(os.getenv("HEALTH_CHECK_TIMEOUT", "2.0"))
    METRICS_TIMEOUT = float(os.getenv("METRICS_TIMEOUT", "2.0"))
    SANDBOX_TIMEOUT = float(os.getenv("SANDBOX_TIMEOUT", "10.0"))
    VERIFICATION_TIMEOUT = float(os.getenv("VERIFICATION_TIMEOUT", "30.0"))
    RESEARCH_TIMEOUT = float(os.getenv("RESEARCH_TIMEOUT", "30.0"))
    AGENT_TIMEOUT = float(os.getenv("AGENT_TIMEOUT", "60.0"))
    ERROR_HANDLER_TIMEOUT = float(os.getenv("ERROR_HANDLER_TIMEOUT", "5.0"))

    # Model names
    VORPAL_MODEL = os.getenv("VORPAL_MODEL", "Qwen/Qwen2.5-3B-Instruct")

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
