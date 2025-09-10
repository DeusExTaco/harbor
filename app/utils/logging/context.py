"""
Logging context management for correlation IDs.

Manages correlation IDs across async contexts for request tracing.
"""

from contextvars import ContextVar
from uuid import uuid4


# Context variable for correlation IDs
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def set_correlation_id(correlation_id: str) -> None:
    """
    Set the correlation ID for the current context.

    Args:
        correlation_id: Correlation ID to set
    """
    correlation_id_var.set(correlation_id)


def get_correlation_id() -> str:
    """
    Get the current correlation ID or generate a new one.

    Returns:
        str: Current correlation ID or newly generated UUID
    """
    correlation_id = correlation_id_var.get()
    return correlation_id if correlation_id else str(uuid4())


def clear_correlation_id() -> None:
    """Clear the correlation ID from context."""
    correlation_id_var.set("")
