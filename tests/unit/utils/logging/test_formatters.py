"""
Unit tests for custom log formatters.

Tests all formatter implementations.
"""

import json
import logging
from datetime import datetime

import pytest

from app.utils.logging.formatters import (
    DevelopmentFormatter,
    HarborFormatter,
    JSONFormatter,
    get_formatter_for_profile,
)


class TestHarborFormatter:
    """Test HarborFormatter functionality."""

    def create_record(self):
        """Create a test log record."""
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="/app/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.created = 1609459200.0
        record.funcName = "test_function"
        return record

    def test_formatter_adds_default_attributes(self):
        """Test that formatter adds default attributes."""
        formatter = HarborFormatter("%(correlation_id)s - %(message)s")
        record = self.create_record()

        # Format without attributes
        formatted = formatter.format(record)

        # Check defaults were added
        assert hasattr(record, "correlation_id")
        assert record.correlation_id == "system"
        assert hasattr(record, "request_id")
        assert hasattr(record, "deployment_profile")
        assert hasattr(record, "contains_sensitive")

    def test_formatter_preserves_existing_attributes(self):
        """Test that formatter preserves existing attributes."""
        formatter = HarborFormatter("%(correlation_id)s - %(message)s")
        record = self.create_record()

        # Add attributes before formatting
        record.correlation_id = "existing-id"
        record.deployment_profile = "production"

        formatted = formatter.format(record)

        # Check attributes were preserved
        assert record.correlation_id == "existing-id"
        assert record.deployment_profile == "production"
        assert "existing-id" in formatted


class TestJSONFormatter:
    """Test JSONFormatter functionality."""

    def create_record(self):
        """Create a test log record."""
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="/app/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.created = 1609459200.0  # Fixed timestamp for testing
        return record

    def test_json_formatter_output_structure(self):
        """Test that JSON formatter produces valid JSON with expected fields."""
        formatter = JSONFormatter()
        record = self.create_record()

        formatted = formatter.format(record)

        # Parse JSON
        data = json.loads(formatted)

        # Check required fields
        assert "timestamp" in data
        assert "level" in data
        assert "logger" in data
        assert "message" in data
        assert "correlation_id" in data
        assert "deployment_profile" in data
        assert "source" in data

        # Check values
        assert data["level"] == "INFO"
        assert data["logger"] == "test.module"
        assert data["message"] == "Test message"
        assert data["correlation_id"] == "system"

    def test_json_formatter_with_exception(self):
        """Test JSON formatter with exception info."""
        formatter = JSONFormatter()
        record = self.create_record()

        # Add exception info
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            record.exc_info = sys.exc_info()

        formatted = formatter.format(record)
        data = json.loads(formatted)

        assert "exception" in data
        assert "ValueError: Test error" in data["exception"]

    def test_json_formatter_with_extra_fields(self):
        """Test JSON formatter with extra fields."""
        formatter = JSONFormatter()
        record = self.create_record()

        # Add extra fields
        record.request_id = "req-123"
        record.contains_sensitive = True
        record.extra = {"user_id": 42, "action": "update"}

        formatted = formatter.format(record)
        data = json.loads(formatted)

        assert data["request_id"] == "req-123"
        assert data["sensitive_data_warning"] is True
        assert data["extra"]["user_id"] == 42

    def test_json_formatter_source_location(self):
        """Test that source location is included."""
        formatter = JSONFormatter()
        record = self.create_record()
        record.funcName = "test_function"  # Ensure funcName is set

        formatted = formatter.format(record)
        data = json.loads(formatted)

        assert data["source"]["file"] == "/app/test.py"
        assert data["source"]["line"] == 42
        assert data["source"]["function"] == "test_function"


class TestDevelopmentFormatter:
    """Test DevelopmentFormatter functionality."""

    def test_development_formatter_adds_colors(self):
        """Test that development formatter adds ANSI colors."""
        format_string = "%(levelname)s - %(message)s"
        formatter = DevelopmentFormatter(format_string)

        levels = {
            logging.DEBUG: "\033[36m",  # Cyan
            logging.INFO: "\033[32m",  # Green
            logging.WARNING: "\033[33m",  # Yellow
            logging.ERROR: "\033[31m",  # Red
            logging.CRITICAL: "\033[35m",  # Magenta
        }

        for level, color in levels.items():
            record = logging.LogRecord(
                name="test",
                level=level,
                pathname="",
                lineno=0,
                msg="Test",
                args=(),
                exc_info=None,
            )

            formatted = formatter.format(record)

            # Check that color code is in the output
            assert color in formatted
            assert "\033[0m" in formatted  # Reset code

    def test_development_formatter_preserves_levelname(self):
        """Test that levelname is restored after formatting."""
        formatter = DevelopmentFormatter("%(levelname)s")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test",
            args=(),
            exc_info=None,
        )

        original_levelname = record.levelname
        formatter.format(record)

        # Levelname should be restored
        assert record.levelname == original_levelname


class TestGetFormatterForProfile:
    """Test get_formatter_for_profile function."""

    def test_json_formatter_for_production(self):
        """Test that production profile returns JSON formatter."""
        formatter = get_formatter_for_profile("production")
        assert isinstance(formatter, JSONFormatter)

    def test_json_formatter_for_staging(self):
        """Test that staging profile returns JSON formatter."""
        formatter = get_formatter_for_profile("staging")
        assert isinstance(formatter, JSONFormatter)

    def test_development_formatter_for_development(self):
        """Test that development profile returns development formatter."""
        formatter = get_formatter_for_profile("development")
        assert isinstance(formatter, DevelopmentFormatter)

    def test_harbor_formatter_for_homelab(self):
        """Test that homelab profile returns Harbor formatter."""
        formatter = get_formatter_for_profile("homelab")
        assert isinstance(formatter, HarborFormatter)

    def test_json_format_override(self):
        """Test that json_format parameter overrides profile."""
        formatter = get_formatter_for_profile("homelab", json_format=True)
        assert isinstance(formatter, JSONFormatter)

        formatter = get_formatter_for_profile("development", json_format=True)
        assert isinstance(formatter, JSONFormatter)
