"""
Performance logging utilities for Harbor.

Provides functions for logging performance metrics and monitoring.
"""

import time
from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime
from functools import wraps
from typing import Any

from app.utils.logging.core import get_logger


# Performance logger instance
perf_logger = get_logger("harbor.performance")


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
    log_data = {
        "function": func_name,
        "duration_ms": duration_ms,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if metadata:
        log_data.update(metadata)

    perf_logger.info(
        f"Performance: {func_name} took {duration_ms:.2f}ms", extra=log_data
    )


@contextmanager
def log_operation_time(operation_name: str, **metadata):
    """
    Context manager to log operation execution time.

    Args:
        operation_name: Name of the operation
        **metadata: Additional metadata to log

    Example:
        with log_operation_time("database_query", query_type="select"):
            # Perform operation
            pass
    """
    start_time = time.perf_counter()

    try:
        yield
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000
        log_performance(operation_name, duration_ms, metadata)


def measure_performance(
    operation_name: str | None = None, log_args: bool = False, log_result: bool = False
) -> Callable:
    """
    Decorator to measure and log function performance.

    Args:
        operation_name: Custom operation name (defaults to function name)
        log_args: Include function arguments in metadata
        log_result: Include function result in metadata

    Returns:
        Callable: Decorated function

    Example:
        @measure_performance("api_call")
        async def fetch_data():
            pass
    """

    def decorator(func: Callable) -> Callable:
        name = operation_name or func.__name__

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            metadata = {}

            if log_args:
                metadata["args"] = str(args)[:100]  # Truncate for safety
                metadata["kwargs"] = str(kwargs)[:100]

            start_time = time.perf_counter()

            try:
                result = func(*args, **kwargs)

                if log_result:
                    metadata["result"] = str(result)[:100]

                return result
            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000
                log_performance(name, duration_ms, metadata)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            metadata = {}

            if log_args:
                metadata["args"] = str(args)[:100]
                metadata["kwargs"] = str(kwargs)[:100]

            start_time = time.perf_counter()

            try:
                result = await func(*args, **kwargs)

                if log_result:
                    metadata["result"] = str(result)[:100]

                return result
            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000
                log_performance(name, duration_ms, metadata)

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class PerformanceTracker:
    """
    Track performance metrics over time.
    Useful for identifying performance degradation.
    """

    def __init__(self, name: str, sample_size: int = 100):
        """
        Initialize performance tracker.

        Args:
            name: Tracker name
            sample_size: Number of samples to keep for statistics
        """
        self.name = name
        self.sample_size = sample_size
        self.samples: list[float] = []
        self.total_calls = 0

    def record(self, duration_ms: float) -> None:
        """
        Record a performance sample.

        Args:
            duration_ms: Duration in milliseconds
        """
        self.total_calls += 1
        self.samples.append(duration_ms)

        # Keep only recent samples
        if len(self.samples) > self.sample_size:
            self.samples.pop(0)

        # Log statistics periodically
        if self.total_calls % self.sample_size == 0:
            self._log_statistics()

    def _log_statistics(self) -> None:
        """Log performance statistics."""
        if not self.samples:
            return

        avg_ms = sum(self.samples) / len(self.samples)
        min_ms = min(self.samples)
        max_ms = max(self.samples)

        perf_logger.info(
            f"Performance stats for {self.name}: "
            f"avg={avg_ms:.2f}ms, min={min_ms:.2f}ms, max={max_ms:.2f}ms",
            extra={
                "tracker": self.name,
                "avg_ms": avg_ms,
                "min_ms": min_ms,
                "max_ms": max_ms,
                "samples": len(self.samples),
                "total_calls": self.total_calls,
            },
        )
