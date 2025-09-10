"""
Core logging setup and configuration for Harbor.

This module provides the main logging setup function and logger factory.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Optional, Union

from app.utils.logging.filters import (
    CorrelationIdFilter,
    EnvironmentFilter,
    SensitiveDataFilter,
)
from app.utils.logging.formatters import get_formatter_for_profile
from app.utils.logging.handlers import (
    CompressedRotatingFileHandler,
    TimedCompressedRotatingFileHandler,
)


# Module-level logger cache
_module_loggers: dict[str, logging.Logger] = {}


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with correlation ID support.

    This maintains compatibility with existing code while adding
    correlation ID filtering.

    Args:
        name: Logger name (typically __name__ from calling module)

    Returns:
        logging.Logger: Configured logger instance
    """
    # Return cached logger if available
    if name in _module_loggers:
        return _module_loggers[name]

    # Create new logger
    logger = logging.getLogger(name)

    # Add correlation filter if not already present
    if not any(isinstance(f, CorrelationIdFilter) for f in logger.filters):
        logger.addFilter(CorrelationIdFilter())

    # Cache and return
    _module_loggers[name] = logger
    return logger


def setup_logging(
    level: str = "INFO",
    log_file: Path | None = None,  # Deprecated
    json_format: bool = False,
    log_dir: Path | None = None,
    enable_rotation: bool = True,
    max_bytes: int = 10_485_760,  # 10MB
    backup_count: int = 5,
    deployment_profile: str = "homelab",
    enable_compression: bool = True,
    enable_time_rotation: bool = False,
    time_rotation_when: str = "midnight",
    enable_sensitive_filter: bool = True,
) -> None:
    """
    Enhanced logging setup with rotation support.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Deprecated - use log_dir instead
        json_format: Whether to use JSON formatting (for production)
        log_dir: Directory for log files
        enable_rotation: Whether to enable log rotation
        max_bytes: Max size per log file before rotation
        backup_count: Number of backup files to keep
        deployment_profile: Current deployment profile
        enable_compression: Enable compression of rotated files
        enable_time_rotation: Use time-based rotation instead of size-based
        time_rotation_when: When to rotate (midnight, H, D, W, etc.)
        enable_sensitive_filter: Enable sensitive data filtering
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Determine log directory
    if log_dir:
        log_path = Path(log_dir)
    elif log_file:
        log_path = log_file.parent
    else:
        log_path = Path("data/logs")

    # Create log directory if needed
    log_path.mkdir(parents=True, exist_ok=True)

    # Get appropriate formatter
    formatter = get_formatter_for_profile(deployment_profile, json_format)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create filters
    filters = [
        CorrelationIdFilter(),
        EnvironmentFilter(deployment_profile),
    ]

    if enable_sensitive_filter:
        filters.append(SensitiveDataFilter())

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    for filter_obj in filters:
        console_handler.addFilter(filter_obj)
    root_logger.addHandler(console_handler)

    # File handlers with rotation
    if enable_rotation:
        # Choose handler class and prepare kwargs based on rotation type
        handler_class: (
            type[CompressedRotatingFileHandler]
            | type[TimedCompressedRotatingFileHandler]
        )
        handler_kwargs: dict[str, Any] = {}

        if enable_time_rotation:
            handler_class = TimedCompressedRotatingFileHandler
            handler_kwargs = {
                "when": time_rotation_when,
                "interval": 1,
                "backupCount": backup_count,
                "compression_level": 9 if enable_compression else 0,
            }
        else:
            handler_class = CompressedRotatingFileHandler
            handler_kwargs = {
                "maxBytes": max_bytes,
                "backupCount": backup_count,
                "compression_level": 9 if enable_compression else 0,
            }

        # Convert Path to string for handlers
        log_path_str = str(log_path)

        # Main application log
        app_handler = handler_class(str(log_path / "app.log"), **handler_kwargs)
        app_handler.setLevel(numeric_level)
        app_handler.setFormatter(formatter)
        for filter_obj in filters:
            app_handler.addFilter(filter_obj)
        root_logger.addHandler(app_handler)

        # Error log (errors only)
        error_handler = handler_class(str(log_path / "error.log"), **handler_kwargs)
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        for filter_obj in filters:
            error_handler.addFilter(filter_obj)
        root_logger.addHandler(error_handler)

        # Specialized loggers
        _setup_specialized_loggers(
            log_path, handler_class, handler_kwargs, formatter, filters
        )

    # Set specific logger levels for third-party libraries
    _configure_third_party_loggers(deployment_profile)


def _setup_specialized_loggers(
    log_path: Path,
    handler_class: type[CompressedRotatingFileHandler]
    | type[TimedCompressedRotatingFileHandler],
    handler_kwargs: dict[str, Any],
    formatter: logging.Formatter,
    filters: list,
) -> None:
    """Set up specialized loggers for specific purposes."""

    # Access log for HTTP requests
    access_logger = logging.getLogger("harbor.access")
    access_handler = handler_class(str(log_path / "access.log"), **handler_kwargs)
    access_handler.setLevel(logging.INFO)
    access_handler.setFormatter(formatter)
    for filter_obj in filters:
        access_handler.addFilter(filter_obj)
    access_logger.addHandler(access_handler)
    access_logger.propagate = False  # Don't propagate to root

    # Audit log for security events
    audit_logger = logging.getLogger("harbor.audit")
    audit_handler = handler_class(str(log_path / "audit.log"), **handler_kwargs)
    audit_handler.setLevel(logging.INFO)
    audit_handler.setFormatter(formatter)
    for filter_obj in filters:
        audit_handler.addFilter(filter_obj)
    audit_logger.addHandler(audit_handler)
    audit_logger.propagate = False

    # Performance log
    perf_logger = logging.getLogger("harbor.performance")
    perf_handler = handler_class(str(log_path / "performance.log"), **handler_kwargs)
    perf_handler.setLevel(logging.INFO)
    perf_handler.setFormatter(formatter)
    for filter_obj in filters:
        perf_handler.addFilter(filter_obj)
    perf_logger.addHandler(perf_handler)
    perf_logger.propagate = False


def _configure_third_party_loggers(deployment_profile: str) -> None:
    """Configure log levels for third-party libraries."""

    if deployment_profile == "development":
        # More verbose in development
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
        logging.getLogger("uvicorn.access").setLevel(logging.INFO)
        logging.getLogger("httpx").setLevel(logging.DEBUG)
    else:
        # Quieter in production
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("asyncio").setLevel(logging.WARNING)

    # Harbor logger configuration
    harbor_logger = logging.getLogger("harbor")
    harbor_logger.setLevel(
        logging.DEBUG if deployment_profile == "development" else logging.INFO
    )


# Initialize basic logging on import (for backward compatibility)
setup_logging()
