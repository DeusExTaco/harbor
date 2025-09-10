"""
Specialized loggers for Harbor.

Provides pre-configured loggers for specific use cases.
"""

import logging

from app.utils.logging.core import get_logger


def get_access_logger() -> logging.Logger:
    """
    Get the access logger for HTTP requests.

    Returns:
        logging.Logger: Access logger instance
    """
    return get_logger("harbor.access")


def get_audit_logger() -> logging.Logger:
    """
    Get the audit logger for security events.

    Returns:
        logging.Logger: Audit logger instance
    """
    return get_logger("harbor.audit")


def get_security_logger() -> logging.Logger:
    """
    Get the security logger for security-related events.

    Returns:
        logging.Logger: Security logger instance
    """
    return get_logger("harbor.security")


def get_database_logger() -> logging.Logger:
    """
    Get the database logger for database operations.

    Returns:
        logging.Logger: Database logger instance
    """
    return get_logger("harbor.database")


def get_docker_logger() -> logging.Logger:
    """
    Get the Docker logger for container operations.

    Returns:
        logging.Logger: Docker logger instance
    """
    return get_logger("harbor.docker")


class StructuredLogger:
    """
    Wrapper for structured logging with consistent field names.
    """

    def __init__(self, logger_name: str):
        """
        Initialize structured logger.

        Args:
            logger_name: Name of the logger
        """
        self.logger = get_logger(logger_name)

    def log_event(
        self, event_type: str, message: str, level: int = logging.INFO, **metadata
    ) -> None:
        """
        Log a structured event.

        Args:
            event_type: Type of event (e.g., "container_update", "auth_failure")
            message: Human-readable message
            level: Log level
            **metadata: Additional structured data
        """
        extra = {"event_type": event_type, **metadata}

        self.logger.log(level, message, extra=extra)

    def log_success(self, operation: str, message: str, **metadata) -> None:
        """Log a successful operation."""
        self.log_event(
            f"{operation}_success", message, logging.INFO, status="success", **metadata
        )

    def log_failure(
        self, operation: str, message: str, error: Exception | None = None, **metadata
    ) -> None:
        """Log a failed operation."""
        if error:
            metadata["error_type"] = type(error).__name__
            metadata["error_message"] = str(error)

        self.log_event(
            f"{operation}_failure", message, logging.ERROR, status="failure", **metadata
        )
