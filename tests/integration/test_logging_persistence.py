"""
Test logging persistence and recovery.

Tests that logs are properly persisted and can survive application restarts.
"""

import gzip
import json
from pathlib import Path

import pytest

from app.utils.logging import get_logger, setup_logging


class TestLogPersistence:
    """Test log persistence and recovery."""

    def test_log_persistence_across_restarts(self, tmp_path):
        """Test that logs persist across application restarts."""
        log_dir = tmp_path / "persistent_logs"

        # First "application run"
        setup_logging(
            log_dir=log_dir,
            enable_rotation=True,
        )

        logger = get_logger("test.persistence")
        logger.info("Message from first run")

        # Simulate application restart by reinitializing logging
        setup_logging(
            log_dir=log_dir,
            enable_rotation=True,
        )

        logger = get_logger("test.persistence")
        logger.info("Message from second run")

        # Both messages should be in the log
        app_log = log_dir / "app.log"
        content = app_log.read_text()

        assert "Message from first run" in content
        assert "Message from second run" in content

    def test_compressed_log_recovery(self, tmp_path):
        """Test that compressed logs can be read back."""
        log_dir = tmp_path / "compressed_logs"

        # Create logs that will be rotated and compressed
        setup_logging(
            log_dir=log_dir,
            enable_rotation=True,
            max_bytes=100,  # Very small to force rotation
            backup_count=3,
        )

        logger = get_logger("test.compressed")

        # Generate enough logs to create compressed files
        messages = []
        for i in range(50):
            msg = f"Important message {i}"
            messages.append(msg)
            logger.info(msg + " " * 50)  # Pad to ensure rotation

        # Find and read compressed files
        compressed_files = list(log_dir.glob("*.gz"))
        assert len(compressed_files) > 0

        # Verify we can read all messages from compressed files
        recovered_messages = []
        for gz_file in compressed_files:
            with gzip.open(gz_file, "rt") as f:
                content = f.read()
                for msg in messages:
                    if msg in content:
                        recovered_messages.append(msg)

        # Should recover at least some messages
        assert len(recovered_messages) > 0

    def test_log_directory_structure(self, tmp_path):
        """Test that log directory structure is maintained."""
        log_dir = tmp_path / "structured_logs"

        setup_logging(
            log_dir=log_dir,
            enable_rotation=True,
        )

        # Log to different loggers
        get_logger("test.app").info("App message")
        get_logger("harbor.access").info("Access message")
        get_logger("harbor.audit").info("Audit message")
        get_logger("harbor.performance").info("Performance message")

        # Check that all log files are created
        expected_files = [
            "app.log",
            "error.log",
            "access.log",
            "audit.log",
            "performance.log",
        ]

        for filename in expected_files:
            log_file = log_dir / filename
            assert log_file.exists(), f"Missing log file: {filename}"

    def test_log_retention_policy(self, tmp_path):
        """Test that log retention policy is enforced."""
        log_dir = tmp_path / "retention_logs"
        backup_count = 2

        setup_logging(
            log_dir=log_dir,
            enable_rotation=True,
            max_bytes=50,  # Very small
            backup_count=backup_count,
        )

        logger = get_logger("test.retention")

        # Generate many logs to exceed backup count
        for i in range(100):
            logger.info(f"Message {i}: " + "x" * 100)

        # Count files for each log type
        app_files = list(log_dir.glob("app.log*"))

        # Should not exceed backup_count + 1 (current file)
        assert len(app_files) <= backup_count + 1
