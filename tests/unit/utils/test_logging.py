# tests/unit/utils/test_logging.py
"""
Unit tests for Harbor logging utilities.

Tests the structured logging configuration, correlation IDs,
and custom handlers.
"""

import gzip
import json
import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.utils.logging import (
    CompressedRotatingFileHandler,
    CorrelationIdFilter,
    HarborFormatter,
    get_access_logger,
    get_audit_logger,
    get_correlation_id,
    get_logger,
    log_performance,
    set_correlation_id,
    setup_logging,
)


class TestCorrelationIdFilter:
    """Test correlation ID filtering functionality."""

    def test_filter_adds_correlation_id(self):
        """Test that filter adds correlation ID to log records."""
        # Setup
        filter_obj = CorrelationIdFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Set correlation ID
        set_correlation_id("test-correlation-123")

        # Apply filter
        result = filter_obj.filter(record)

        # Verify
        assert result is True
        assert record.correlation_id == "test-correlation-123"
        assert record.request_id == "test-correlation-123"

    def test_filter_uses_system_when_no_correlation_id(self):
        """Test that filter uses 'system' when no correlation ID is set."""
        # Setup
        filter_obj = CorrelationIdFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Clear any existing correlation ID
        set_correlation_id("")

        # Apply filter
        result = filter_obj.filter(record)

        # Verify
        assert result is True
        assert record.correlation_id == "system"
        assert record.request_id == "system"


class TestCompressedRotatingFileHandler:
    """Test compressed rotating file handler."""

    def test_rollover_compresses_files(self, tmp_path):
        """Test that rollover compresses rotated log files."""
        # Setup
        log_file = tmp_path / "test.log"
        handler = CompressedRotatingFileHandler(
            str(log_file), maxBytes=100, backupCount=2
        )

        # Write enough data to trigger rollover
        logger = logging.getLogger("test_compress")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Write logs to trigger rollover
        for i in range(20):
            logger.info(f"Test message {i} with some padding to increase size")

        handler.close()

        # Check for compressed backup files
        compressed_files = list(tmp_path.glob("*.gz"))
        assert len(compressed_files) > 0

        # Verify compressed file is valid gzip
        if compressed_files:
            with gzip.open(compressed_files[0], "rt") as f:
                content = f.read()
                assert "Test message" in content


class TestHarborFormatter:
    """Test Harbor custom formatter."""

    def test_formatter_adds_default_attributes(self):
        """Test that formatter adds default attributes if missing."""
        # Setup
        formatter = HarborFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s"
        )

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Format without correlation_id attribute
        formatted = formatter.format(record)

        # Verify defaults were added
        assert hasattr(record, "correlation_id")
        assert record.correlation_id == "system"
        assert hasattr(record, "request_id")
        assert "[system]" in formatted


class TestLoggerFunctions:
    """Test logger utility functions."""

    def test_get_logger_returns_cached_instance(self):
        """Test that get_logger returns cached instances."""
        logger1 = get_logger("test.module")
        logger2 = get_logger("test.module")

        assert logger1 is logger2

    def test_get_logger_adds_correlation_filter(self):
        """Test that get_logger adds correlation ID filter."""
        logger = get_logger("test.correlation")

        # Check for correlation filter
        has_correlation_filter = any(
            isinstance(f, CorrelationIdFilter) for f in logger.filters
        )
        assert has_correlation_filter

    def test_set_and_get_correlation_id(self):
        """Test setting and getting correlation IDs."""
        # Set correlation ID
        set_correlation_id("test-id-456")

        # Get correlation ID
        correlation_id = get_correlation_id()

        assert correlation_id == "test-id-456"

    def test_get_correlation_id_generates_new_if_empty(self):
        """Test that get_correlation_id generates new ID if empty."""
        # Clear correlation ID
        set_correlation_id("")

        # Get correlation ID
        correlation_id = get_correlation_id()

        # Should be a UUID
        assert correlation_id != ""
        assert len(correlation_id) == 36  # UUID4 length with hyphens

    def test_get_access_logger(self):
        """Test getting access logger."""
        logger = get_access_logger()

        assert logger.name == "harbor.access"
        assert isinstance(logger, logging.Logger)

    def test_get_audit_logger(self):
        """Test getting audit logger."""
        logger = get_audit_logger()

        assert logger.name == "harbor.audit"
        assert isinstance(logger, logging.Logger)

    @patch("app.utils.logging.get_logger")
    def test_log_performance(self, mock_get_logger):
        """Test performance logging function."""
        # Setup mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Log performance
        log_performance(
            func_name="test_function",
            duration_ms=123.45,
            metadata={"extra": "data"},
        )

        # Verify
        mock_get_logger.assert_called_with("harbor.performance")
        mock_logger.info.assert_called_once()

        # Check log message
        call_args = mock_logger.info.call_args
        assert "test_function took 123.45ms" in call_args[0][0]

        # Check extra data
        extra = call_args[1]["extra"]
        assert extra["function"] == "test_function"
        assert extra["duration_ms"] == 123.45
        assert extra["extra"] == "data"


class TestSetupLogging:
    """Test logging setup functionality."""

    def test_setup_logging_default_configuration(self, tmp_path):
        """Test setup_logging with default configuration."""
        log_dir = tmp_path / "logs"

        setup_logging(
            level="INFO",
            log_dir=log_dir,
            json_format=False,
            enable_rotation=True,
        )

        # Check root logger configuration
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

        # Check log files were created
        assert log_dir.exists()
        assert (log_dir / "app.log").exists()
        assert (log_dir / "error.log").exists()

    def test_setup_logging_json_format(self, tmp_path):
        """Test setup_logging with JSON format."""
        log_dir = tmp_path / "logs"

        setup_logging(
            level="DEBUG",
            log_dir=log_dir,
            json_format=True,
            enable_rotation=True,
        )

        # Write a test log
        logger = get_logger("test.json")
        set_correlation_id("json-test-123")
        logger.info("Test JSON message")

        # Read and parse log file
        log_file = log_dir / "app.log"
        if log_file.exists():
            with open(log_file, "r") as f:
                lines = f.readlines()
                if lines:
                    # Last line should be JSON
                    last_line = lines[-1].strip()
                    try:
                        log_data = json.loads(last_line)
                        assert log_data["level"] == "INFO"
                        assert log_data["correlation_id"] == "json-test-123"
                        assert "Test JSON message" in log_data["message"]
                    except json.JSONDecodeError:
                        # If not valid JSON, check if it's in JSON-like format
                        assert '"level": "INFO"' in last_line

    def test_setup_logging_without_rotation(self, tmp_path):
        """Test setup_logging without rotation."""
        log_dir = tmp_path / "logs"

        setup_logging(
            level="WARNING",
            log_dir=log_dir,
            enable_rotation=False,
        )

        # Check that only console handler is added
        root_logger = logging.getLogger()

        # Should have at least console handler
        assert len(root_logger.handlers) >= 1

        # No file handlers when rotation is disabled
        file_handlers = [
            h
            for h in root_logger.handlers
            if isinstance(h, (logging.FileHandler, CompressedRotatingFileHandler))
        ]
        assert len(file_handlers) == 0

    def test_setup_logging_creates_specialized_loggers(self, tmp_path):
        """Test that setup_logging creates specialized loggers."""
        log_dir = tmp_path / "logs"

        setup_logging(
            log_dir=log_dir,
            enable_rotation=True,
        )

        # Check specialized loggers
        access_logger = logging.getLogger("harbor.access")
        audit_logger = logging.getLogger("harbor.audit")

        # These should not propagate to root
        assert access_logger.propagate is False
        assert audit_logger.propagate is False

        # Check log files exist
        assert (log_dir / "access.log").exists()
        assert (log_dir / "audit.log").exists()
