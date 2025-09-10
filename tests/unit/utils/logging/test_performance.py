"""
Unit tests for performance logging utilities.

Tests performance tracking and measurement decorators.
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from app.utils.logging.performance import (
    PerformanceTracker,
    log_operation_time,
    log_performance,
    measure_performance,
)


class TestLogPerformance:
    """Test log_performance function."""

    @patch("app.utils.logging.performance.perf_logger")
    def test_log_performance_basic(self, mock_logger):
        """Test basic performance logging."""
        log_performance("test_operation", 123.45)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args

        # Check message
        assert "test_operation took 123.45ms" in call_args[0][0]

        # Check extra data
        extra = call_args[1]["extra"]
        assert extra["function"] == "test_operation"
        assert extra["duration_ms"] == 123.45

    @patch("app.utils.logging.performance.perf_logger")
    def test_log_performance_with_metadata(self, mock_logger):
        """Test performance logging with metadata."""
        metadata = {"user_id": 42, "action": "update"}
        log_performance("test_operation", 100.0, metadata)

        mock_logger.info.assert_called_once()
        extra = mock_logger.info.call_args[1]["extra"]

        assert extra["user_id"] == 42
        assert extra["action"] == "update"


class TestLogOperationTime:
    """Test log_operation_time context manager."""

    @patch("app.utils.logging.performance.log_performance")
    def test_log_operation_time_context_manager(self, mock_log_perf):
        """Test operation time logging with context manager."""
        with log_operation_time("test_operation"):
            time.sleep(0.01)  # Simulate work

        mock_log_perf.assert_called_once()
        call_args = mock_log_perf.call_args

        assert call_args[0][0] == "test_operation"
        # Duration should be at least 10ms
        assert call_args[0][1] >= 10

    @patch("app.utils.logging.performance.log_performance")
    def test_log_operation_time_with_metadata(self, mock_log_perf):
        """Test context manager with metadata."""
        with log_operation_time("db_query", query_type="select", table="users"):
            pass

        mock_log_perf.assert_called_once()
        metadata = mock_log_perf.call_args[0][2]

        assert metadata["query_type"] == "select"
        assert metadata["table"] == "users"

    @patch("app.utils.logging.performance.log_performance")
    def test_log_operation_time_with_exception(self, mock_log_perf):
        """Test that timing is logged even if exception occurs."""
        with pytest.raises(ValueError):
            with log_operation_time("failing_operation"):
                raise ValueError("Test error")

        # Should still log the performance
        mock_log_perf.assert_called_once()


class TestMeasurePerformance:
    """Test measure_performance decorator."""

    @patch("app.utils.logging.performance.log_performance")
    def test_measure_performance_sync_function(self, mock_log_perf):
        """Test decorator on synchronous function."""

        @measure_performance("custom_operation")
        def test_func(x, y):
            return x + y

        result = test_func(2, 3)

        assert result == 5
        mock_log_perf.assert_called_once()
        assert mock_log_perf.call_args[0][0] == "custom_operation"

    @patch("app.utils.logging.performance.log_performance")
    def test_measure_performance_default_name(self, mock_log_perf):
        """Test decorator uses function name by default."""

        @measure_performance()
        def my_function():
            return "result"

        my_function()

        mock_log_perf.assert_called_once()
        assert mock_log_perf.call_args[0][0] == "my_function"

    @patch("app.utils.logging.performance.log_performance")
    def test_measure_performance_with_args_logging(self, mock_log_perf):
        """Test decorator with argument logging."""

        @measure_performance(log_args=True)
        def test_func(x, y, z=10):
            return x + y + z

        test_func(1, 2, z=3)

        mock_log_perf.assert_called_once()
        metadata = mock_log_perf.call_args[0][2]

        assert "args" in metadata
        assert "(1, 2)" in metadata["args"]
        assert "z" in metadata["kwargs"]

    @patch("app.utils.logging.performance.log_performance")
    def test_measure_performance_with_result_logging(self, mock_log_perf):
        """Test decorator with result logging."""

        @measure_performance(log_result=True)
        def test_func():
            return "test_result"

        result = test_func()

        assert result == "test_result"
        metadata = mock_log_perf.call_args[0][2]
        assert metadata["result"] == "test_result"

    @pytest.mark.asyncio
    @patch("app.utils.logging.performance.log_performance")
    async def test_measure_performance_async_function(self, mock_log_perf):
        """Test decorator on async function."""

        @measure_performance("async_operation")
        async def async_func(x):
            await asyncio.sleep(0.01)
            return x * 2

        result = await async_func(5)

        assert result == 10
        mock_log_perf.assert_called_once()
        assert mock_log_perf.call_args[0][0] == "async_operation"
        # Should have recorded at least 10ms
        assert mock_log_perf.call_args[0][1] >= 10


class TestPerformanceTracker:
    """Test PerformanceTracker class."""

    def test_tracker_records_samples(self):
        """Test that tracker records performance samples."""
        tracker = PerformanceTracker("test_tracker", sample_size=5)

        tracker.record(10.0)
        tracker.record(20.0)
        tracker.record(15.0)

        assert len(tracker.samples) == 3
        assert tracker.total_calls == 3

    @patch("app.utils.logging.performance.perf_logger")  # Add this decorator
    def test_tracker_maintains_sample_size_limit(self, mock_logger):
        """Test that tracker maintains sample size limit."""
        tracker = PerformanceTracker("test_tracker", sample_size=3)

        for i in range(10):
            tracker.record(float(i))

        assert len(tracker.samples) == 3
        assert tracker.total_calls == 10
        # Should keep most recent samples
        assert 7.0 in tracker.samples
        assert 8.0 in tracker.samples
        assert 9.0 in tracker.samples

        # Verify statistics were logged (3 times: at 3rd, 6th, and 9th call)
        assert mock_logger.info.call_count == 3

    @patch("app.utils.logging.performance.perf_logger")
    def test_tracker_logs_statistics(self, mock_logger):
        """Test that tracker logs statistics periodically."""
        tracker = PerformanceTracker("test_tracker", sample_size=3)

        # Record exactly sample_size calls to trigger statistics
        tracker.record(10.0)
        tracker.record(20.0)
        tracker.record(30.0)

        # Statistics should be logged
        mock_logger.info.assert_called_once()

        call_args = mock_logger.info.call_args
        message = call_args[0][0]

        assert "Performance stats for test_tracker" in message
        assert "avg=20.00ms" in message
        assert "min=10.00ms" in message
        assert "max=30.00ms" in message
