"""
Custom logging filters for Harbor.

Provides filters for adding contextual information to log records.
"""

import logging
from typing import ClassVar

from app.utils.logging.context import correlation_id_var


class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to all log records within a request context."""

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add correlation_id to log record if available.

        Args:
            record: Log record to filter

        Returns:
            bool: Always True (doesn't filter out records)
        """
        # Get correlation ID from context or use 'system' for non-request logs
        correlation_id = correlation_id_var.get()

        # Use setattr to dynamically add attributes
        record.correlation_id = correlation_id if correlation_id else "system"
        record.request_id = getattr(record, "correlation_id", "system")

        return True


class EnvironmentFilter(logging.Filter):
    """Add environment/deployment profile to log records."""

    def __init__(self, deployment_profile: str = "unknown"):
        """
        Initialize environment filter.

        Args:
            deployment_profile: Current deployment profile
        """
        super().__init__()
        self.deployment_profile = deployment_profile

    def filter(self, record: logging.LogRecord) -> bool:
        """Add deployment profile to record."""
        record.deployment_profile = self.deployment_profile
        return True


class SensitiveDataFilter(logging.Filter):
    """Filter sensitive data from log records."""

    # Patterns to mask in log messages
    SENSITIVE_PATTERNS: ClassVar[list[str]] = [
        "password",
        "secret",
        "token",
        "api_key",
        "authorization",
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Mask sensitive data in log messages.

        Args:
            record: Log record to filter

        Returns:
            bool: Always True (doesn't filter out records)
        """
        # Check if message contains sensitive patterns
        message_lower = str(record.msg).lower()

        for pattern in self.SENSITIVE_PATTERNS:
            if pattern in message_lower:
                # Add warning attribute
                record.contains_sensitive = True
                break
        else:
            record.contains_sensitive = False

        return True
