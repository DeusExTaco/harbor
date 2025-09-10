"""
Unit tests for custom logging filters.

Tests all custom filter implementations.
"""

import logging

import pytest

from app.utils.logging.context import set_correlation_id
from app.utils.logging.filters import (
    CorrelationIdFilter,
    EnvironmentFilter,
    SensitiveDataFilter,
)


class TestCorrelationIdFilter:
    """Test CorrelationIdFilter functionality."""

    def create_log_record(self, msg="Test message"):
        """Helper to create a log record."""
        return logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=msg,
            args=(),
            exc_info=None,
        )

    def test_filter_adds_correlation_id(self):
        """Test that filter adds correlation ID to records."""
        filter_obj = CorrelationIdFilter()
        record = self.create_log_record()

        set_correlation_id("test-correlation-456")

        result = filter_obj.filter(record)

        assert result is True
        assert hasattr(record, "correlation_id")
        assert record.correlation_id == "test-correlation-456"
        assert hasattr(record, "request_id")
        assert record.request_id == "test-correlation-456"

    def test_filter_uses_system_when_no_correlation_id(self):
        """Test that filter uses 'system' when no correlation ID is set."""
        filter_obj = CorrelationIdFilter()
        record = self.create_log_record()

        set_correlation_id("")  # Clear any existing ID

        result = filter_obj.filter(record)

        assert result is True
        assert record.correlation_id == "system"
        assert record.request_id == "system"

    def test_filter_always_returns_true(self):
        """Test that filter never filters out records."""
        filter_obj = CorrelationIdFilter()
        record = self.create_log_record()

        # Should always return True (doesn't filter records)
        assert filter_obj.filter(record) is True


class TestEnvironmentFilter:
    """Test EnvironmentFilter functionality."""

    def test_filter_adds_deployment_profile(self):
        """Test that filter adds deployment profile to records."""
        filter_obj = EnvironmentFilter("production")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test",
            args=(),
            exc_info=None,
        )

        result = filter_obj.filter(record)

        assert result is True
        assert hasattr(record, "deployment_profile")
        assert record.deployment_profile == "production"

    def test_filter_with_different_profiles(self):
        """Test filter with different deployment profiles."""
        profiles = ["homelab", "development", "staging", "production"]

        for profile in profiles:
            filter_obj = EnvironmentFilter(profile)
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="Test",
                args=(),
                exc_info=None,
            )

            filter_obj.filter(record)
            assert record.deployment_profile == profile


class TestSensitiveDataFilter:
    """Test SensitiveDataFilter functionality."""

    def create_record(self, msg):
        """Helper to create a log record with a message."""
        return logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=msg,
            args=(),
            exc_info=None,
        )

    def test_filter_detects_password_in_message(self):
        """Test that filter detects 'password' in messages."""
        filter_obj = SensitiveDataFilter()

        record = self.create_record("User password: secret123")
        result = filter_obj.filter(record)

        assert result is True
        assert hasattr(record, "contains_sensitive")
        assert record.contains_sensitive is True

    def test_filter_detects_various_sensitive_patterns(self):
        """Test detection of various sensitive patterns."""
        filter_obj = SensitiveDataFilter()

        sensitive_messages = [
            "password: admin123",
            "secret_key: abc456",
            "token=xyz789",
            "api_key: sk_test_123",
            "Authorization: Bearer token123",
        ]

        for msg in sensitive_messages:
            record = self.create_record(msg)
            filter_obj.filter(record)
            assert (
                record.contains_sensitive is True
            ), f"Failed to detect sensitive data in: {msg}"

    def test_filter_marks_non_sensitive_as_false(self):
        """Test that non-sensitive messages are marked as such."""
        filter_obj = SensitiveDataFilter()

        safe_messages = [
            "Container started successfully",
            "Database connection established",
            "Health check passed",
            "Update completed",
        ]

        for msg in safe_messages:
            record = self.create_record(msg)
            filter_obj.filter(record)
            assert record.contains_sensitive is False

    def test_filter_case_insensitive_detection(self):
        """Test that detection is case-insensitive."""
        filter_obj = SensitiveDataFilter()

        test_cases = [
            "PASSWORD: test",
            "Password: test",
            "password: test",
            "PaSsWoRd: test",
        ]

        for msg in test_cases:
            record = self.create_record(msg)
            filter_obj.filter(record)
            assert record.contains_sensitive is True
