"""
Harbor Logging Package

Provides structured logging configuration and utilities for Harbor application.
This package refactors the original logging.py into modular components for
better maintainability and testing.
"""

from app.utils.logging.context import (
    correlation_id_var,
    get_correlation_id,
    set_correlation_id,
)
from app.utils.logging.core import (
    get_logger,
    setup_logging,
)
from app.utils.logging.filters import CorrelationIdFilter
from app.utils.logging.formatters import HarborFormatter
from app.utils.logging.handlers import CompressedRotatingFileHandler
from app.utils.logging.performance import log_performance
from app.utils.logging.specialized import get_access_logger, get_audit_logger


__all__ = [
    # Core functions
    "setup_logging",
    "get_logger",
    # Context management
    "correlation_id_var",
    "get_correlation_id",
    "set_correlation_id",
    # Specialized loggers
    "get_access_logger",
    "get_audit_logger",
    # Performance
    "log_performance",
    # Classes (for testing/extension)
    "CorrelationIdFilter",
    "HarborFormatter",
    "CompressedRotatingFileHandler",
]
