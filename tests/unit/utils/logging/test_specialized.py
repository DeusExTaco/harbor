"""
Unit tests for specialized loggers.

Tests pre-configured loggers and structured logging utilities.
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

from app.utils.logging.specialized import (
    StructuredLogger,
    get_access_logger,
    get_audit_logger,
    get_database_logger,
    get_docker_logger,
    get_security_logger,
)


class TestSpecializedLoggers:
    """Test specialized logger functions."""

    def test_get_access_logger(self):
        """Test access logger retrieval."""
        logger = get_access_logger()
        assert isinstance(logger, logging.Logger)
        assert logger.name == "harbor.access"

    def test_get_audit_logger(self):
        """Test audit logger retrieval."""
        logger = get_audit_logger()
        assert isinstance(logger, logging.Logger)
        assert logger.name == "harbor.audit"

    def test_get_security_logger(self):
        """Test security logger retrieval."""
        logger = get_security_logger()
        assert isinstance(logger, logging.Logger)
        assert logger.name == "harbor.security"

    def test_get_database_logger(self):
        """Test database logger retrieval."""
        logger = get_database_logger()
        assert isinstance(logger, logging.Logger)
        assert logger.name == "harbor.database"

    def test_get_docker_logger(self):
        """Test Docker logger retrieval."""
        logger = get_docker_logger()
        assert isinstance(logger, logging.Logger)
        assert logger.name == "harbor.docker"

    def test_loggers_are_cached(self):
        """Test that specialized loggers are cached."""
        logger1 = get_access_logger()
        logger2 = get_access_logger()
        assert logger1 is logger2


class TestStructuredLogger:
    """Test StructuredLogger class."""

    @patch("app.utils.logging.specialized.get_logger")
    def test_structured_logger_initialization(self, mock_get_logger):
        """Test StructuredLogger initialization."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        structured = StructuredLogger("test.structured")

        mock_get_logger.assert_called_once_with("test.structured")
        assert structured.logger is mock_logger

    def test_log_event(self):
        """Test log_event method."""
        structured = StructuredLogger("test.events")

        with patch.object(structured.logger, "log") as mock_log:
            structured.log_event(
                "user_login",
                "User logged in successfully",
                level=logging.INFO,
                user_id=42,
                ip_address="192.168.1.1",
            )

            mock_log.assert_called_once()
            call_args = mock_log.call_args

            assert call_args[0][0] == logging.INFO
            assert call_args[0][1] == "User logged in successfully"

            extra = call_args[1]["extra"]
            assert extra["event_type"] == "user_login"
            assert extra["user_id"] == 42
            assert extra["ip_address"] == "192.168.1.1"

    def test_log_success(self):
        """Test log_success helper method."""
        structured = StructuredLogger("test.success")

        with patch.object(structured, "log_event") as mock_log_event:
            structured.log_success(
                "container_update",
                "Container updated successfully",
                container_id="abc123",
                duration_ms=1500,
            )

            mock_log_event.assert_called_once_with(
                "container_update_success",
                "Container updated successfully",
                logging.INFO,
                status="success",
                container_id="abc123",
                duration_ms=1500,
            )

    def test_log_failure_without_exception(self):
        """Test log_failure without exception."""
        structured = StructuredLogger("test.failure")

        with patch.object(structured, "log_event") as mock_log_event:
            structured.log_failure(
                "database_connection",
                "Failed to connect to database",
                host="localhost",
                port=5432,
            )

            mock_log_event.assert_called_once_with(
                "database_connection_failure",
                "Failed to connect to database",
                logging.ERROR,
                status="failure",
                host="localhost",
                port=5432,
            )

    def test_log_failure_with_exception(self):
        """Test log_failure with exception details."""
        structured = StructuredLogger("test.failure")

        test_error = ValueError("Invalid configuration")

        with patch.object(structured, "log_event") as mock_log_event:
            structured.log_failure(
                "config_load",
                "Failed to load configuration",
                error=test_error,
                config_file="/app/config.yaml",
            )

            call_args = mock_log_event.call_args
            metadata = call_args[1]

            assert metadata["error_type"] == "ValueError"
            assert metadata["error_message"] == "Invalid configuration"
            assert metadata["config_file"] == "/app/config.yaml"
