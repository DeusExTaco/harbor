"""
Custom log formatters for Harbor.

Provides formatters for different output formats and deployment profiles.
"""

import json
import logging
from datetime import datetime
from typing import Any, ClassVar


class HarborFormatter(logging.Formatter):
    """Custom formatter that provides defaults for Harbor-specific fields."""

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with Harbor defaults.

        Args:
            record: Log record to format

        Returns:
            str: Formatted log message
        """
        # Ensure our custom attributes exist with defaults
        if not hasattr(record, "correlation_id"):
            record.correlation_id = "system"
        if not hasattr(record, "request_id"):
            record.request_id = getattr(record, "correlation_id", "system")
        if not hasattr(record, "deployment_profile"):
            record.deployment_profile = "unknown"
        if not hasattr(record, "contains_sensitive"):
            record.contains_sensitive = False

        return super().format(record)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging in production."""

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            str: JSON-formatted log message
        """
        # Build log data dictionary
        log_data: dict[str, Any] = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", "system"),
            "deployment_profile": getattr(record, "deployment_profile", "unknown"),
        }

        # Add optional fields
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        if hasattr(record, "contains_sensitive") and record.contains_sensitive:
            log_data["sensitive_data_warning"] = True

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra"):
            log_data["extra"] = record.extra

        # Add source location
        log_data["source"] = {
            "file": record.pathname,
            "line": record.lineno,
            "function": record.funcName,
        }

        return json.dumps(log_data, default=str)


class DevelopmentFormatter(logging.Formatter):
    """Enhanced formatter for development with colors and better readability."""

    # ANSI color codes
    COLORS: ClassVar[dict[str, str]] = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",
    }

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with colors for development.

        Args:
            record: Log record to format

        Returns:
            str: Formatted log message with ANSI colors
        """
        # Add default attributes
        if not hasattr(record, "correlation_id"):
            record.correlation_id = "system"

        # Get color for level
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
            )

        # Format message
        formatted = super().format(record)

        # Reset levelname for other handlers
        record.levelname = levelname

        return formatted


def get_formatter_for_profile(
    deployment_profile: str, json_format: bool = False
) -> logging.Formatter:
    """
    Get appropriate formatter for deployment profile.

    Args:
        deployment_profile: Current deployment profile
        json_format: Force JSON format

    Returns:
        logging.Formatter: Configured formatter
    """
    if json_format or deployment_profile in ["production", "staging"]:
        return JSONFormatter()
    elif deployment_profile == "development":
        format_string = (
            "%(asctime)s - %(levelname)s - %(name)s - "
            "[%(correlation_id)s] - %(message)s"
        )
        return DevelopmentFormatter(format_string)
    else:  # homelab or default
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - "
            "[%(correlation_id)s] - %(message)s"
        )
        return HarborFormatter(format_string)
