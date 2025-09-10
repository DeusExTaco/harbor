"""
Unit tests for custom log handlers.

Tests rotation, compression, and buffering handlers.
"""

import gzip
import logging
import time
from pathlib import Path

import pytest

from app.utils.logging.handlers import (
    BufferedHandler,
    CompressedRotatingFileHandler,
    TimedCompressedRotatingFileHandler,
)


class TestCompressedRotatingFileHandler:
    """Test CompressedRotatingFileHandler functionality."""

    def test_handler_creates_log_file(self, tmp_path):
        """Test that handler creates log file."""
        log_file = tmp_path / "test.log"
        handler = CompressedRotatingFileHandler(str(log_file))

        # Log a message
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        handler.emit(record)
        handler.close()

        assert log_file.exists()
        assert "Test message" in log_file.read_text()

    def test_handler_rotation_by_size(self, tmp_path):
        """Test that handler rotates files by size."""
        log_file = tmp_path / "test.log"
        handler = CompressedRotatingFileHandler(
            str(log_file),
            maxBytes=100,  # Small size to trigger rotation
            backupCount=2,
        )

        # Log enough messages to trigger rotation
        logger = logging.getLogger("test_rotation")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        for i in range(20):
            logger.info(f"Test message {i} with padding to increase size")

        handler.close()

        # Check for rotated files
        rotated_files = list(tmp_path.glob("*.gz"))
        assert len(rotated_files) > 0

    def test_compressed_files_are_valid_gzip(self, tmp_path):
        """Test that compressed files are valid gzip."""
        log_file = tmp_path / "test.log"
        handler = CompressedRotatingFileHandler(
            str(log_file), maxBytes=50, backupCount=3
        )

        # Generate logs to trigger rotation
        logger = logging.getLogger("test_compress")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        for i in range(10):
            logger.info(f"Message {i}: " + "x" * 50)

        handler.close()

        # Check compressed files
        gz_files = list(tmp_path.glob("*.gz"))
        for gz_file in gz_files:
            # Verify it's valid gzip
            with gzip.open(gz_file, "rt") as f:
                content = f.read()
                assert "Message" in content

    def test_backup_count_limit(self, tmp_path):
        """Test that backup count limit is respected."""
        log_file = tmp_path / "test.log"
        backup_count = 2

        handler = CompressedRotatingFileHandler(
            str(log_file), maxBytes=30, backupCount=backup_count
        )

        logger = logging.getLogger("test_backup")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Generate many logs to exceed backup count
        for i in range(50):
            logger.info(f"Log entry {i}")

        handler.close()

        # Count compressed files
        gz_files = list(tmp_path.glob("*.gz"))
        assert len(gz_files) <= backup_count


class TestTimedCompressedRotatingFileHandler:
    """Test TimedCompressedRotatingFileHandler functionality."""

    def test_handler_creates_log_file(self, tmp_path):
        """Test that timed handler creates log file."""
        log_file = tmp_path / "timed.log"
        handler = TimedCompressedRotatingFileHandler(
            str(log_file),
            when="S",  # Rotate every second for testing
            interval=1,
            backupCount=2,
        )

        # Log a message
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Timed test message",
            args=(),
            exc_info=None,
        )
        handler.emit(record)
        handler.close()

        assert log_file.exists()

    @pytest.mark.slow
    def test_timed_rotation(self, tmp_path):
        """Test that handler rotates based on time."""
        log_file = tmp_path / "timed.log"
        handler = TimedCompressedRotatingFileHandler(
            str(log_file),
            when="S",  # Rotate every second
            interval=1,
            backupCount=3,
        )

        logger = logging.getLogger("test_timed")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Log over multiple seconds
        for i in range(3):
            logger.info(f"Timed message {i}")
            time.sleep(1.1)  # Wait for rotation

        handler.close()

        # Check for rotated files
        all_files = list(tmp_path.glob("*.log*"))
        assert len(all_files) > 1


class TestBufferedHandler:
    """Test BufferedHandler functionality."""

    def test_buffered_handler_buffers_messages(self, tmp_path):
        """Test that handler buffers messages before writing."""
        log_file = tmp_path / "buffered.log"

        # Create target handler
        target_handler = logging.FileHandler(str(log_file))

        # Create buffered handler
        buffered_handler = BufferedHandler(capacity=5, target=target_handler)

        logger = logging.getLogger("test_buffer")
        logger.addHandler(buffered_handler)
        logger.setLevel(logging.INFO)

        # Log fewer messages than buffer capacity
        for i in range(3):
            logger.info(f"Buffered message {i}")

        # File should be empty (messages buffered)
        assert not log_file.exists() or log_file.stat().st_size == 0

        # Flush buffer
        buffered_handler.flush()

        # Now file should have content
        assert log_file.exists()
        content = log_file.read_text()
        assert "Buffered message 0" in content
        assert "Buffered message 2" in content

        buffered_handler.close()
        target_handler.close()

    def test_buffered_handler_flushes_on_error(self, tmp_path):
        """Test that handler flushes immediately on error level."""
        log_file = tmp_path / "buffered_error.log"

        target_handler = logging.FileHandler(str(log_file))
        buffered_handler = BufferedHandler(
            capacity=10, flushLevel=logging.ERROR, target=target_handler
        )

        logger = logging.getLogger("test_error_flush")
        logger.addHandler(buffered_handler)
        logger.setLevel(logging.INFO)

        # Log info messages (buffered)
        logger.info("Info message 1")
        logger.info("Info message 2")

        # Log error message (should trigger flush)
        logger.error("Error message")

        # Check that all messages were written
        content = log_file.read_text()
        assert "Info message 1" in content
        assert "Info message 2" in content
        assert "Error message" in content

        buffered_handler.close()
        target_handler.close()
