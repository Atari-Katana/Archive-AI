"""
Centralized Error Handling System
Provides clear, actionable error messages with recovery instructions.
"""

from typing import Optional, Dict, Any
from enum import Enum
import httpx


class ErrorCategory(Enum):
    """Error categories for better organization"""
    MODEL = "model"
    NETWORK = "network"
    VALIDATION = "validation"
    RESOURCE = "resource"
    PERMISSION = "permission"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


class ErrorFormatter:
    """
    Formats errors with ASCII boxes and recovery instructions.

    Creates visually distinct error messages that are easy to spot
    in logs and provide actionable recovery steps.
    """

    @staticmethod
    def format_box(title: str, message: str, recovery_steps: Optional[list] = None) -> str:
        """
        Format error message in ASCII box for visibility.

        Args:
            title: Error title (e.g., "Model Not Available")
            message: Error description
            recovery_steps: List of recovery actions

        Returns:
            Formatted error message with box and recovery steps

        Example:
            >>> ErrorFormatter.format_box(
            ...     "Model Not Available",
            ...     "Vorpal engine is not responding",
            ...     ["Check if Docker container is running", "Restart services"]
            ... )
        """
        width = 70
        box_top = "╔" + "═" * (width - 2) + "╗"
        box_bottom = "╚" + "═" * (width - 2) + "╝"
        box_side = "║"

        def wrap_line(text: str, width: int) -> list:
            """Wrap text to fit within width"""
            words = text.split()
            lines = []
            current_line = ""

            for word in words:
                if len(current_line) + len(word) + 1 <= width:
                    current_line += (word + " ")
                else:
                    if current_line:
                        lines.append(current_line.rstrip())
                    current_line = word + " "

            if current_line:
                lines.append(current_line.rstrip())

            return lines if lines else [""]

        # Build message
        output = [box_top]

        # Title
        title_padded = f" ⚠ {title} ".center(width - 2)
        output.append(f"{box_side}{title_padded}{box_side}")
        output.append("║" + "─" * (width - 2) + "║")

        # Message
        for line in wrap_line(message, width - 6):
            line_padded = f"  {line}".ljust(width - 2)
            output.append(f"{box_side}{line_padded}{box_side}")

        # Recovery steps
        if recovery_steps:
            output.append("║" + " " * (width - 2) + "║")
            recovery_title = "  Recovery Steps:".ljust(width - 2)
            output.append(f"{box_side}{recovery_title}{box_side}")

            for i, step in enumerate(recovery_steps, 1):
                for line in wrap_line(f"{i}. {step}", width - 8):
                    line_padded = f"    {line}".ljust(width - 2)
                    output.append(f"{box_side}{line_padded}{box_side}")

        output.append(box_bottom)

        return "\n".join(output)

    @staticmethod
    def format_simple(title: str, message: str) -> str:
        """
        Format error without box (for less critical errors).

        Args:
            title: Error title
            message: Error description

        Returns:
            Simple formatted error message
        """
        return f"⚠ {title}: {message}"


class ModelChecker:
    """
    Checks model availability and provides helpful error messages.
    """

    @staticmethod
    async def check_vorpal(vorpal_url: str) -> tuple[bool, Optional[str]]:
        """
        Check if Vorpal engine is available.

        Args:
            vorpal_url: Vorpal service URL

        Returns:
            Tuple of (is_available, error_message)
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{vorpal_url}/health")
                if response.status_code == 200:
                    return True, None
                else:
                    return False, f"Vorpal responded with status {response.status_code}"
        except httpx.ConnectError:
            return False, "Cannot connect to Vorpal engine"
        except httpx.TimeoutException:
            return False, "Vorpal engine timed out"
        except Exception as e:
            return False, f"Vorpal health check failed: {str(e)}"

    @staticmethod
    async def check_goblin(goblin_url: str) -> tuple[bool, Optional[str]]:
        """
        Check if Goblin engine is available.

        Args:
            goblin_url: Goblin service URL

        Returns:
            Tuple of (is_available, error_message)
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{goblin_url}/health")
                if response.status_code == 200:
                    return True, None
                else:
                    return False, f"Goblin responded with status {response.status_code}"
        except httpx.ConnectError:
            return False, "Cannot connect to Goblin engine"
        except httpx.TimeoutException:
            return False, "Goblin engine timed out"
        except Exception as e:
            return False, f"Goblin health check failed: {str(e)}"

    @staticmethod
    async def check_sandbox(sandbox_url: str) -> tuple[bool, Optional[str]]:
        """
        Check if sandbox service is available.

        Args:
            sandbox_url: Sandbox service URL

        Returns:
            Tuple of (is_available, error_message)
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{sandbox_url}/health")
                if response.status_code == 200:
                    return True, None
                else:
                    return False, f"Sandbox responded with status {response.status_code}"
        except httpx.ConnectError:
            return False, "Cannot connect to sandbox service"
        except httpx.TimeoutException:
            return False, "Sandbox service timed out"
        except Exception as e:
            return False, f"Sandbox health check failed: {str(e)}"


class ArchiveAIError(Exception):
    """
    Base exception for Archive-AI with enhanced error messages.

    Provides structured error information with category, context,
    and recovery instructions.
    """

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        context: Optional[Dict[str, Any]] = None,
        recovery_steps: Optional[list] = None,
        original_error: Optional[Exception] = None
    ):
        """
        Initialize enhanced error.

        Args:
            message: Error description
            category: Error category for classification
            context: Additional context (request ID, user action, etc.)
            recovery_steps: List of recovery actions
            original_error: Original exception if this is a wrapper
        """
        self.message = message
        self.category = category
        self.context = context or {}
        self.recovery_steps = recovery_steps or []
        self.original_error = original_error

        super().__init__(message)

    def format(self, use_box: bool = True) -> str:
        """
        Format error message with recovery steps.

        Args:
            use_box: If True, use ASCII box formatting

        Returns:
            Formatted error message
        """
        title = f"{self.category.value.title()} Error"

        if use_box:
            return ErrorFormatter.format_box(
                title,
                self.message,
                self.recovery_steps if self.recovery_steps else None
            )
        else:
            return ErrorFormatter.format_simple(title, self.message)

    def __str__(self) -> str:
        """String representation (simple format)"""
        return ErrorFormatter.format_simple(
            f"{self.category.value.title()} Error",
            self.message
        )


# Specific error types with predefined recovery steps

class ModelUnavailableError(ArchiveAIError):
    """Model service is not responding"""

    def __init__(self, model_name: str, reason: str):
        super().__init__(
            message=f"The {model_name} model is not available: {reason}",
            category=ErrorCategory.MODEL,
            recovery_steps=[
                "Check if Docker containers are running: docker ps",
                "Check service logs: docker logs vorpal (or goblin)",
                "Restart services: bash scripts/start.sh",
                "Verify VRAM availability: nvidia-smi"
            ]
        )


class RedisUnavailableError(ArchiveAIError):
    """Redis service is not responding"""

    def __init__(self, reason: str):
        super().__init__(
            message=f"Redis is not available: {reason}",
            category=ErrorCategory.RESOURCE,
            recovery_steps=[
                "Check if Redis container is running: docker ps",
                "Check Redis logs: docker logs redis-stack",
                "Restart Redis: docker-compose restart redis-stack",
                "Check Redis connection in .env file"
            ]
        )


class SandboxUnavailableError(ArchiveAIError):
    """Code sandbox service is not responding"""

    def __init__(self, reason: str):
        super().__init__(
            message=f"Code sandbox is not available: {reason}",
            category=ErrorCategory.RESOURCE,
            recovery_steps=[
                "Check if sandbox container is running: docker ps",
                "Check sandbox logs: docker logs sandbox",
                "Restart sandbox: docker-compose restart sandbox",
                "Verify sandbox port in config: should be 8081"
            ]
        )


class ValidationError(ArchiveAIError):
    """Input validation failed"""

    def __init__(self, field: str, reason: str, valid_range: Optional[str] = None):
        message = f"Invalid {field}: {reason}"
        recovery_steps = []

        if valid_range:
            recovery_steps.append(f"Valid range: {valid_range}")

        recovery_steps.extend([
            "Check API documentation: http://localhost:8080/docs",
            "Review input parameters and try again"
        ])

        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION,
            recovery_steps=recovery_steps
        )


class VRAMExceededError(ArchiveAIError):
    """VRAM budget exceeded"""

    def __init__(self, used_mb: float, budget_mb: float):
        super().__init__(
            message=f"VRAM usage ({used_mb:.1f}MB) exceeds budget ({budget_mb:.1f}MB)",
            category=ErrorCategory.RESOURCE,
            recovery_steps=[
                "Check VRAM usage: nvidia-smi",
                "Stop unused model engines",
                "Reduce context length in config",
                "Switch to single-engine mode (Vorpal only)"
            ]
        )


class ConfigurationError(ArchiveAIError):
    """Configuration is invalid or missing"""

    def __init__(self, setting: str, reason: str):
        super().__init__(
            message=f"Configuration error for '{setting}': {reason}",
            category=ErrorCategory.CONFIGURATION,
            recovery_steps=[
                "Check .env file exists and is readable",
                "Verify environment variables are set correctly",
                "Compare with .env.example for reference",
                "Restart services after configuration changes"
            ]
        )


# Error message templates for common scenarios

ERROR_TEMPLATES = {
    "empty_input": "Input cannot be empty. Please provide {field_name}.",
    "too_long": "{field_name} is too long ({current} chars). Maximum is {maximum} characters.",
    "too_short": "{field_name} is too short ({current} chars). Minimum is {minimum} characters.",
    "out_of_range": "{field_name} is out of range ({current}). Valid range is {minimum} to {maximum}.",
    "invalid_format": "{field_name} has invalid format. Expected: {expected}",
    "not_found": "{resource} not found: {identifier}",
    "already_exists": "{resource} already exists: {identifier}",
    "timeout": "Operation timed out after {seconds} seconds",
    "rate_limit": "Rate limit exceeded. Try again in {seconds} seconds.",
}


def create_error_message(template_key: str, **kwargs) -> str:
    """
    Create error message from template.

    Args:
        template_key: Key from ERROR_TEMPLATES
        **kwargs: Template parameters

    Returns:
        Formatted error message

    Examples:
        >>> create_error_message("empty_input", field_name="message")
        'Input cannot be empty. Please provide message.'

        >>> create_error_message("too_long", field_name="code", current=6000, maximum=5000)
        'code is too long (6000 chars). Maximum is 5000 characters.'
    """
    template = ERROR_TEMPLATES.get(template_key, "Unknown error: {error}")
    try:
        return template.format(**kwargs)
    except KeyError as e:
        return f"Error template formatting failed: missing key {e}"
