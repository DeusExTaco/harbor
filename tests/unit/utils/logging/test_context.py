"""
Unit tests for logging context management.

Tests correlation ID management across async contexts.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.utils.logging.context import (
    clear_correlation_id,
    correlation_id_var,
    get_correlation_id,
    set_correlation_id,
)


class TestCorrelationIdManagement:
    """Test correlation ID context management."""

    def test_set_and_get_correlation_id(self):
        """Test basic set and get of correlation ID."""
        test_id = "test-correlation-123"
        set_correlation_id(test_id)

        retrieved_id = get_correlation_id()
        assert retrieved_id == test_id

    def test_get_correlation_id_generates_new_when_empty(self):
        """Test that get_correlation_id generates UUID when empty."""
        clear_correlation_id()

        generated_id = get_correlation_id()
        assert generated_id != ""
        assert len(generated_id) == 36  # UUID4 format
        assert generated_id.count("-") == 4

    def test_clear_correlation_id(self):
        """Test clearing correlation ID."""
        set_correlation_id("test-id")
        assert correlation_id_var.get() == "test-id"

        clear_correlation_id()
        assert correlation_id_var.get() == ""

    def test_correlation_id_isolation_between_contexts(self):
        """Test that correlation IDs are isolated between contexts."""
        # Set ID in main context
        set_correlation_id("main-context-id")

        def worker():
            # This should not see the main context ID
            return correlation_id_var.get()

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(worker)
            result = future.result()

        # Worker should have empty ID
        assert result == ""

        # Main context should still have its ID
        assert get_correlation_id() == "main-context-id"

    @pytest.mark.asyncio
    async def test_correlation_id_in_async_context(self):
        """Test correlation ID preservation in async context."""
        set_correlation_id("async-test-id")

        async def async_task():
            return get_correlation_id()

        # Run async task
        result = await async_task()
        assert result == "async-test-id"

    @pytest.mark.asyncio
    async def test_correlation_id_isolation_in_concurrent_tasks(self):
        """Test that concurrent async tasks maintain separate correlation IDs."""

        async def task(task_id: str):
            set_correlation_id(f"task-{task_id}")
            await asyncio.sleep(0.01)  # Simulate some work
            return get_correlation_id()

        # Run multiple tasks concurrently
        results = await asyncio.gather(task("1"), task("2"), task("3"))

        # Each task should have its own ID
        assert results == ["task-1", "task-2", "task-3"]

    def test_correlation_id_context_var_default(self):
        """Test the default value of correlation_id_var."""
        # Clear any existing value
        clear_correlation_id()

        # Direct access should return empty string (the default)
        assert correlation_id_var.get() == ""
