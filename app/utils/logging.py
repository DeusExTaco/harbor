# app/utils/logging.py (simplified version without Protocol)
"""
Harbor Logging Utilities - Enhanced Version

Provides structured logging configuration and utilities for Harbor application.
Integrates with existing middleware while adding structured logging support.
"""

import gzip
import logging
import logging.handlers
import sys
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4


# Context variable for correlation IDs
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")

# Module-level logger cache
_module_loggers: dict[str, logging.Logger] = {}


class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to all log records within a request context."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation_id to log record if available."""
        # Get correlation ID from context or use 'system' for non-request logs
        correlation_id = correlation_id_var.get()

        # Use setattr to dynamically add attributes
        record.correlation_id = correlation_id if correlation_id else "system"
        record.request_id = getattr(record, "correlation_id", "system")

        return True


class CompressedRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """
    Rotating file handler that compresses rotated log files.
    Important for home labs with limited storage.
    """

    def doRollover(self) -> None:  # noqa: N802
        """Override to compress the rotated log file."""
        super().doRollover()

        # Compress the rotated files
        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                sfn = f"{self.baseFilename}.{i}"
                sfn_path = Path(sfn)
                if sfn_path.exists() and not sfn.endswith(".gz"):
                    # Compress the file
                    with open(sfn, "rb") as f_in:
                        with gzip.open(f"{sfn}.gz", "wb", compresslevel=9) as f_out:
                            f_out.writelines(f_in)
                    # Remove uncompressed version
                    sfn_path.unlink()


class HarborFormatter(logging.Formatter):
    """Custom formatter that provides defaults for Harbor-specific fields."""

    def format(self, record: logging.LogRecord) -> str:
        # Ensure our custom attributes exist with defaults
        if not hasattr(record, "correlation_id"):
            record.correlation_id = "system"
        if not hasattr(record, "request_id"):
            record.request_id = getattr(record, "correlation_id", "system")
        return super().format(record)


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
    log_file: Path | None = None,
    json_format: bool = False,
    log_dir: Path | None = None,
    enable_rotation: bool = True,
    max_bytes: int = 10_485_760,  # 10MB
    backup_count: int = 5,
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

    # Create formatter with defaults to avoid KeyError
    if json_format:
        # JSON format for production/structured logging
        format_string = (
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "correlation_id": "%(correlation_id)s", '
            '"message": "%(message)s"}'
        )
    else:
        # Human-readable format for development
        format_string = "%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s"

    formatter = HarborFormatter(format_string)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(CorrelationIdFilter())
    root_logger.addHandler(console_handler)

    # File handlers with rotation
    if enable_rotation:
        # Main application log
        app_handler = CompressedRotatingFileHandler(
            log_path / "app.log", maxBytes=max_bytes, backupCount=backup_count
        )
        app_handler.setLevel(numeric_level)
        app_handler.setFormatter(formatter)
        app_handler.addFilter(CorrelationIdFilter())
        root_logger.addHandler(app_handler)

        # Error log (errors only)
        error_handler = CompressedRotatingFileHandler(
            log_path / "error.log", maxBytes=max_bytes, backupCount=backup_count
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        error_handler.addFilter(CorrelationIdFilter())
        root_logger.addHandler(error_handler)

        # Access log for HTTP requests
        access_logger = logging.getLogger("harbor.access")
        access_handler = CompressedRotatingFileHandler(
            log_path / "access.log", maxBytes=max_bytes, backupCount=backup_count
        )
        access_handler.setLevel(logging.INFO)
        access_handler.setFormatter(formatter)
        access_handler.addFilter(CorrelationIdFilter())
        access_logger.addHandler(access_handler)
        access_logger.propagate = False  # Don't propagate to root

        # Audit log for security events
        audit_logger = logging.getLogger("harbor.audit")
        audit_handler = CompressedRotatingFileHandler(
            log_path / "audit.log", maxBytes=max_bytes, backupCount=backup_count
        )
        audit_handler.setLevel(logging.INFO)
        audit_handler.setFormatter(formatter)
        audit_handler.addFilter(CorrelationIdFilter())
        audit_logger.addHandler(audit_handler)
        audit_logger.propagate = False  # Don't propagate to root

    # Set specific logger levels for third-party libraries
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Harbor logger
    harbor_logger = logging.getLogger("harbor")
    harbor_logger.setLevel(numeric_level)


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for the current context."""
    correlation_id_var.set(correlation_id)


def get_correlation_id() -> str:
    """Get the current correlation ID or generate a new one."""
    correlation_id = correlation_id_var.get()
    return correlation_id if correlation_id else str(uuid4())


def get_access_logger() -> logging.Logger:
    """Get the access logger for HTTP requests."""
    return get_logger("harbor.access")


def get_audit_logger() -> logging.Logger:
    """Get the audit logger for security events."""
    return get_logger("harbor.audit")


def log_performance(
    func_name: str, duration_ms: float, metadata: dict[str, Any] | None = None
) -> None:
    """
    Log performance metrics for monitoring.

    Args:
        func_name: Name of the function/operation
        duration_ms: Duration in milliseconds
        metadata: Additional metadata to log
    """
    logger = get_logger("harbor.performance")

    log_data = {
        "function": func_name,
        "duration_ms": duration_ms,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if metadata:
        log_data.update(metadata)

    logger.info(f"Performance: {func_name} took {duration_ms:.2f}ms", extra=log_data)


# Initialize basic logging on import
setup_logging()
