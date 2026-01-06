"""
Configuration API Endpoints
Provides web-based configuration editor with validation.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional
import os
from pathlib import Path
import re


# Configuration schema with validation
class ConfigUpdate(BaseModel):
    """Configuration update request"""

    # Service URLs
    vorpal_url: Optional[str] = Field(None, description="Vorpal service URL")
    goblin_url: Optional[str] = Field(None, description="Goblin service URL")
    sandbox_url: Optional[str] = Field(None, description="Sandbox service URL")
    voice_url: Optional[str] = Field(None, description="Voice service URL")
    redis_url: Optional[str] = Field(None, description="Redis connection URL")

    # Feature flags
    async_memory: Optional[bool] = Field(None, description="Enable async memory worker")
    enable_voice: Optional[bool] = Field(None, description="Enable voice I/O")

    # Model settings
    vorpal_model: Optional[str] = Field(None, description="Vorpal model name")

    # Archive settings
    archive_days_threshold: Optional[int] = Field(None, ge=1, le=365, description="Archive threshold in days")
    archive_keep_recent: Optional[int] = Field(None, ge=100, le=10000, description="Number of recent memories to keep")
    archive_hour: Optional[int] = Field(None, ge=0, le=23, description="Archive hour (0-23)")
    archive_minute: Optional[int] = Field(None, ge=0, le=59, description="Archive minute (0-59)")
    archive_enabled: Optional[bool] = Field(None, description="Enable archival")

    # Logging
    log_level: Optional[str] = Field(None, description="Log level (DEBUG, INFO, WARNING, ERROR)")

    @validator("vorpal_url", "goblin_url", "sandbox_url", "voice_url")
    def validate_url(cls, v):
        """Validate URL format"""
        if v is not None and not re.match(r"^https?://[\w\.\-]+:\d+$", v):
            raise ValueError(f"Invalid URL format: {v}. Must be http://host:port or https://host:port")
        return v

    @validator("redis_url")
    def validate_redis_url(cls, v):
        """Validate Redis URL format"""
        if v is not None and not re.match(r"^redis://[\w\.\-]+:\d+$", v):
            raise ValueError(f"Invalid Redis URL format: {v}. Must be redis://host:port")
        return v

    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level"""
        if v is not None and v not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError(f"Invalid log level: {v}. Must be DEBUG, INFO, WARNING, ERROR, or CRITICAL")
        return v


class ConfigResponse(BaseModel):
    """Configuration response"""
    config: Dict[str, Any]
    restart_required: bool = False


router = APIRouter(prefix="/config", tags=["Configuration"])


def get_env_file_path() -> Path:
    """Get path to .env file"""
    # Assume .env is in project root (parent of brain/)
    brain_dir = Path(__file__).parent
    project_root = brain_dir.parent
    env_path = project_root / ".env"
    return env_path


def read_env_file() -> Dict[str, str]:
    """
    Read .env file and return as dictionary.

    Returns:
        Dictionary of environment variables
    """
    env_path = get_env_file_path()

    if not env_path.exists():
        return {}

    env_vars = {}

    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue

            # Parse KEY=VALUE
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                env_vars[key] = value

    return env_vars


def write_env_file(env_vars: Dict[str, str]):
    """
    Write environment variables to .env file.

    Args:
        env_vars: Dictionary of environment variables
    """
    env_path = get_env_file_path()

    # Read existing file to preserve comments
    existing_lines = []
    if env_path.exists():
        with open(env_path, "r") as f:
            existing_lines = f.readlines()

    # Build new content
    new_lines = []
    updated_keys = set()

    for line in existing_lines:
        stripped = line.strip()

        # Preserve comments and empty lines
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue

        # Update existing keys
        if "=" in stripped:
            key = stripped.split("=", 1)[0].strip()

            if key in env_vars:
                # Update value
                new_lines.append(f'{key}="{env_vars[key]}"\n')
                updated_keys.add(key)
            else:
                # Keep original line
                new_lines.append(line)
        else:
            # Keep non-key lines
            new_lines.append(line)

    # Add new keys that weren't in original file
    for key, value in env_vars.items():
        if key not in updated_keys:
            new_lines.append(f'{key}="{value}"\n')

    # Write to file
    with open(env_path, "w") as f:
        f.writelines(new_lines)


@router.get("/", response_model=ConfigResponse)
async def get_config():
    """
    Get current configuration.

    Returns current values from environment variables (runtime source of truth).
    """
    # Build config dict from os.getenv to reflect actual runtime state
    config = {
        # Service URLs
        "vorpal_url": os.getenv("VORPAL_URL", "http://vorpal:8000"),
        "goblin_url": os.getenv("GOBLIN_URL", "http://goblin:8080"),
        "sandbox_url": os.getenv("SANDBOX_URL", "http://sandbox:8000"),
        "voice_url": os.getenv("VOICE_URL", "http://voice:8001"),
        "redis_url": os.getenv("REDIS_URL", "redis://redis:6379"),

        # Feature flags
        "async_memory": os.getenv("ASYNC_MEMORY", "true").lower() == "true",
        "enable_voice": os.getenv("ENABLE_VOICE", "false").lower() == "true",

        # Model settings
        "vorpal_model": os.getenv("VORPAL_MODEL", "Qwen/Qwen2.5-3B-Instruct"),

        # Archive settings
        "archive_days_threshold": int(os.getenv("ARCHIVE_DAYS_THRESHOLD", "30")),
        "archive_keep_recent": int(os.getenv("ARCHIVE_KEEP_RECENT", "1000")),
        "archive_hour": int(os.getenv("ARCHIVE_HOUR", "3")),
        "archive_minute": int(os.getenv("ARCHIVE_MINUTE", "0")),
        "archive_enabled": os.getenv("ARCHIVE_ENABLED", "true").lower() == "true",

        # Logging
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
    }

    return ConfigResponse(config=config, restart_required=False)


@router.post("/", response_model=ConfigResponse)
async def update_config(update: ConfigUpdate):
    """
    Update configuration.

    Validates input, updates .env file, and returns updated config.
    Note: Restart required for changes to take effect.
    """
    # Read current .env
    env_vars = read_env_file()

    # Track if any changes were made
    changes_made = False

    # Update environment variables
    mapping = {
        "vorpal_url": "VORPAL_URL",
        "goblin_url": "GOBLIN_URL",
        "sandbox_url": "SANDBOX_URL",
        "voice_url": "VOICE_URL",
        "redis_url": "REDIS_URL",
        "async_memory": "ASYNC_MEMORY",
        "enable_voice": "ENABLE_VOICE",
        "vorpal_model": "VORPAL_MODEL",
        "archive_days_threshold": "ARCHIVE_DAYS_THRESHOLD",
        "archive_keep_recent": "ARCHIVE_KEEP_RECENT",
        "archive_hour": "ARCHIVE_HOUR",
        "archive_minute": "ARCHIVE_MINUTE",
        "archive_enabled": "ARCHIVE_ENABLED",
        "log_level": "LOG_LEVEL",
    }

    for field_name, env_name in mapping.items():
        value = getattr(update, field_name)

        if value is not None:
            # Convert to string
            if isinstance(value, bool):
                str_value = "true" if value else "false"
            else:
                str_value = str(value)

            # Check if value changed
            current_value = env_vars.get(env_name, "")
            if str_value != current_value:
                env_vars[env_name] = str_value
                changes_made = True

    # Write updated .env file
    if changes_made:
        write_env_file(env_vars)

    # Return updated config
    config_response = await get_config()
    config_response.restart_required = changes_made

    return config_response


@router.post("/validate")
async def validate_config(update: ConfigUpdate):
    """
    Validate configuration without saving.

    Returns validation errors if any.
    """
    # Pydantic will automatically validate
    # If we reach here, validation passed
    return {"valid": True, "message": "Configuration is valid"}


@router.post("/reset")
async def reset_config():
    """
    Reset configuration to defaults.

    Removes custom values from .env file, reverting to defaults.
    """
    env_path = get_env_file_path()

    if not env_path.exists():
        raise HTTPException(status_code=404, detail=".env file not found")

    # Read .env.example for defaults
    example_path = env_path.parent / ".env.example"

    if not example_path.exists():
        raise HTTPException(status_code=404, detail=".env.example file not found")

    # Copy .env.example to .env
    import shutil
    shutil.copy(example_path, env_path)

    return {"message": "Configuration reset to defaults", "restart_required": True}


# Add router to main app in brain/main.py:
# app.include_router(config_api.router)
