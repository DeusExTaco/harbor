"""
Unit tests for core logging functionality.

Tests the main setup_logging function and get_logger factory.
"""

import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.utils.logging.core import (
    _configure_third_party_loggers,
    _setup_specialized_loggers,
    get_logger,
    setup_logging,
)
from app.utils.logging.filters import CorrelationIdFilter, EnvironmentFilter


class TestGetLogger:
    """Test the get_logger factory function."""

    def test_get_logger_returns_logger_instance(self):
        """Test that get_logger returns a logging.Logger instance."""
        logger = get_logger("test.module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"

    def test_get_logger_caches_instances(self):
        """Test that get_logger returns cached instances for same name."""
        logger1 = get_logger("test.cache")
        logger2 = get_logger("test.cache")
        assert logger1 is logger2

    def test_get_logger_adds_correlation_filter(self):
        """Test that get_logger adds CorrelationIdFilter."""
        logger = get_logger("test.filter")

        # Check that correlation filter is added
        has_correlation_filter = any(
            isinstance(f, CorrelationIdFilter) for f in logger.filters
        )
        assert has_correlation_filter

    def test_get_logger_different_names_different_instances(self):
        """Test that different names return different logger instances."""
        logger1 = get_logger("test.module1")
        logger2 = get_logger("test.module2")
        assert logger1 is not logger2
        assert logger1.name != logger2.name


class TestSetupLogging:
    """Test the setup_logging configuration function."""

    def teardown_method(self):
        """Clean up after each test."""
        # Reset root logger
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    def test_setup_logging_creates_log_directory(self, tmp_path):
        """Test that setup_logging creates the log directory if it doesn't exist."""
        log_dir = tmp_path / "test_logs"
        assert not log_dir.exists()

        setup_logging(log_dir=log_dir, enable_rotation=False)

        assert log_dir.exists()
        assert log_dir.is_dir()

    def test_setup_logging_sets_root_logger_level(self):
        """Test that setup_logging sets the correct log level."""
        setup_logging(level="DEBUG", enable_rotation=False)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

        setup_logging(level="ERROR", enable_rotation=False)
        assert root_logger.level == logging.ERROR

    def test_setup_logging_adds_console_handler(self):
        """Test that console handler is added."""
        setup_logging(enable_rotation=False)

        root_logger = logging.getLogger()
        console_handlers = [
            h
            for h in root_logger.handlers
            if isinstance(h, logging.StreamHandler) and h.stream == sys.stdout
        ]
        assert len(console_handlers) >= 1

    def test_setup_logging_with_rotation(self, tmp_path):
        """Test setup with rotation enabled."""
        log_dir = tmp_path / "rotation_logs"

        setup_logging(
            log_dir=log_dir, enable_rotation=True, max_bytes=1024, backup_count=3
        )

        # Check that log files are created
        assert (log_dir / "app.log").exists()
        assert (log_dir / "error.log").exists()
        assert (log_dir / "access.log").exists()
        assert (log_dir / "audit.log").exists()
        assert (log_dir / "performance.log").exists()

    def test_setup_logging_with_json_format(self, tmp_path):
        """Test setup with JSON formatting."""
        log_dir = tmp_path / "json_logs"

        setup_logging(log_dir=log_dir, json_format=True, enable_rotation=True)

        # Log a test message
        logger = get_logger("test.json")
        logger.info("Test message")

        # Check that log file exists
        log_file = log_dir / "app.log"
        assert log_file.exists()

    def test_setup_logging_deployment_profiles(self, tmp_path):
        """Test different deployment profile configurations."""
        profiles = ["homelab", "development", "staging", "production"]

        for profile in profiles:
            log_dir = tmp_path / f"{profile}_logs"
            setup_logging(
                log_dir=log_dir, deployment_profile=profile, enable_rotation=False
            )

            # Verify profile-specific configuration
            root_logger = logging.getLogger()
            assert len(root_logger.handlers) > 0

    def test_setup_logging_sensitive_filter(self, tmp_path):
        """Test sensitive data filter configuration."""
        log_dir = tmp_path / "sensitive_logs"

        setup_logging(
            log_dir=log_dir, enable_sensitive_filter=True, enable_rotation=False
        )

        root_logger = logging.getLogger()
        # Check that handlers have sensitive filter
        for handler in root_logger.handlers:
            filters = handler.filters
            assert any(f.__class__.__name__ == "SensitiveDataFilter" for f in filters)

    @patch("app.utils.logging.core.TimedCompressedRotatingFileHandler")
    def test_setup_logging_time_rotation(self, mock_handler_class, tmp_path):
        """Test time-based rotation configuration."""
        log_dir = tmp_path / "time_logs"

        setup_logging(
            log_dir=log_dir,
            enable_rotation=True,
            enable_time_rotation=True,
            time_rotation_when="midnight",
        )

        # Verify time-based handler was used
        mock_handler_class.assert_called()


class TestConfigureThirdPartyLoggers:
    """Test third-party logger configuration."""

    def test_configure_development_profile(self):
        """Test third-party logger configuration for development."""
        _configure_third_party_loggers("development")

        sql_logger = logging.getLogger("sqlalchemy.engine")
        assert sql_logger.level == logging.INFO

        uvicorn_logger = logging.getLogger("uvicorn.access")
        assert uvicorn_logger.level == logging.INFO

    def test_configure_production_profile(self):
        """Test third-party logger configuration for production."""
        _configure_third_party_loggers("production")

        sql_logger = logging.getLogger("sqlalchemy.engine")
        assert sql_logger.level == logging.WARNING

        uvicorn_logger = logging.getLogger("uvicorn.access")
        assert uvicorn_logger.level == logging.WARNING

        asyncio_logger = logging.getLogger("asyncio")
        assert asyncio_logger.level == logging.WARNING
