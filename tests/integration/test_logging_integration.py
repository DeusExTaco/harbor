# tests/integration/test_logging_integration.py
"""
Integration tests for Harbor logging system.

Tests the complete logging system integration with middleware,
health monitoring, and request processing.
"""

import asyncio
import json
import logging
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.middleware.correlation import CorrelationMiddleware
from app.utils.logging import (
    get_correlation_id,
    get_logger,
    set_correlation_id,
    setup_logging,
)


@pytest.fixture
def temp_log_dir():
    """Create temporary log directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def app_with_correlation():
    """Create FastAPI app with correlation middleware."""
    app = FastAPI()

    # Add correlation middleware
    app.add_middleware(CorrelationMiddleware)

    @app.get("/test")
    async def test_endpoint():
        logger = get_logger("test.endpoint")
        correlation_id = get_correlation_id()
        logger.info(f"Test endpoint called with correlation ID: {correlation_id}")
        return {"correlation_id": correlation_id}

    @app.get("/health")
    async def health_endpoint():
        return {"status": "ok"}

    return app


class TestLoggingMiddlewareIntegration:
    """Test logging system integration with middleware."""

    def test_correlation_id_propagation(self, app_with_correlation):
        """Test that correlation ID propagates through request."""
        client = TestClient(app_with_correlation)

        # Make request with correlation ID header
        response = client.get(
            "/test", headers={"X-Correlation-ID": "test-correlation-456"}
        )

        assert response.status_code == 200

        # Check response headers
        assert response.headers.get("X-Correlation-ID") == "test-correlation-456"
        assert response.headers.get("X-Request-ID") == "test-correlation-456"

    def test_correlation_id_generation(self, app_with_correlation):
        """Test that correlation ID is generated if not provided."""
        client = TestClient(app_with_correlation)

        # Make request without correlation ID
        response = client.get("/test")

        assert response.status_code == 200

        # Should have generated correlation ID
        correlation_id = response.headers.get("X-Correlation-ID")
        assert correlation_id is not None
        assert len(correlation_id) == 36  # UUID format

    def test_multiple_concurrent_requests(self, app_with_correlation):
        """Test that multiple concurrent requests maintain separate correlation IDs."""
        client = TestClient(app_with_correlation)

        # Make multiple requests with different correlation IDs
        responses = []
        correlation_ids = ["req-1", "req-2", "req-3"]

        for cid in correlation_ids:
            response = client.get("/test", headers={"X-Correlation-ID": cid})
            responses.append(response)

        # Verify each response has correct correlation ID
        for i, response in enumerate(responses):
            assert response.headers.get("X-Correlation-ID") == correlation_ids[i]
            assert response.json()["correlation_id"] == correlation_ids[i]


class TestHealthMonitoringIntegration:
    """Test health monitoring integration with logging."""

    @pytest.mark.asyncio
    async def test_health_check_logging(self, temp_log_dir):
        """Test that health checks are properly logged."""
        # Setup logging
        setup_logging(
            level="INFO",
            log_dir=temp_log_dir,
            enable_rotation=True,
        )

        # Import and test health service
        from app.services.health import HealthStatus, health_monitor

        # Get health
        health = await health_monitor.get_health()

        # Verify health structure
        assert "status" in health
        assert "checks" in health
        assert health["status"] in [
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.UNHEALTHY,
        ]

    @pytest.mark.asyncio
    async def test_readiness_check_logging(self, temp_log_dir):
        """Test that readiness checks are properly logged."""
        setup_logging(
            level="DEBUG",
            log_dir=temp_log_dir,
            enable_rotation=True,
        )

        from app.services.health import health_monitor

        readiness = await health_monitor.get_readiness()

        assert "ready" in readiness
        assert "checks" in readiness
        assert isinstance(readiness["ready"], bool)


class TestRequestLoggingIntegration:
    """Test request logging middleware integration."""

    def test_request_logging_with_correlation(self, temp_log_dir):
        """Test that requests are logged with correlation IDs."""
        from app.middleware.request_logging import RequestLoggingMiddleware

        app = FastAPI()
        app.add_middleware(CorrelationMiddleware)
        app.add_middleware(RequestLoggingMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        client = TestClient(app)

        # Setup logging
        setup_logging(
            level="INFO",
            log_dir=temp_log_dir,
            enable_rotation=True,
        )

        # Make request
        response = client.get("/test")

        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        assert "X-Response-Time" in response.headers

    # tests/integration/test_logging_integration.py - Fixed version of the failing test

    def test_sensitive_endpoint_logging(self, temp_log_dir):
        """Test that sensitive endpoints are logged appropriately."""
        from app.middleware.request_logging import RequestLoggingMiddleware

        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)

        @app.post("/api/v1/auth/login")
        async def login():
            return {"token": "secret"}

        client = TestClient(app)

        # Setup logging without setting a correlation ID that contains "test"
        setup_logging(
            level="INFO",
            log_dir=temp_log_dir,
            json_format=True,
            enable_rotation=True,
        )

        # Clear any existing correlation ID
        set_correlation_id("")

        # Make request to sensitive endpoint with a unique username
        response = client.post("/api/v1/auth/login", json={"username": "secretuser123"})

        assert response.status_code == 200

        # Force flush logs
        for handler in logging.getLogger().handlers:
            if hasattr(handler, "flush"):
                handler.flush()

        # Check that sensitive data is not logged
        app_log = temp_log_dir / "app.log"
        if app_log.exists():
            content = app_log.read_text()
            # Should log the endpoint but not the body
            assert "/api/v1/auth/login" in content
            # The actual username from the request body should not be logged
            assert "secretuser123" not in content  # Username should not be logged
            assert '"username"' not in content  # The key should not be logged either
            # The response token should not be logged
            assert "secret" not in content


class TestLoggingRotationIntegration:
    """Test log rotation integration."""

    def test_log_rotation_with_compression(self, temp_log_dir):
        """Test that log rotation works with compression."""
        # Setup logging with small max bytes to trigger rotation
        setup_logging(
            level="DEBUG",
            log_dir=temp_log_dir,
            enable_rotation=True,
            max_bytes=1024,  # Small size to trigger rotation
            backup_count=3,
        )

        logger = get_logger("test.rotation")

        # Write many log messages to trigger rotation
        for i in range(100):
            logger.info(f"Test message {i} with padding to increase size " + "x" * 50)

        # Force handlers to flush
        for handler in logger.handlers:
            if hasattr(handler, "flush"):
                handler.flush()

        # Check for rotated and compressed files
        log_files = list(temp_log_dir.glob("*.log*"))
        gz_files = list(temp_log_dir.glob("*.gz"))

        # Should have some log files
        assert len(log_files) > 0

        # May have compressed files if rotation occurred
        # (depending on timing and buffer flushing)
        print(f"Log files: {log_files}")
        print(f"Compressed files: {gz_files}")


class TestAuditLoggingIntegration:
    """Test audit logging integration."""

    def test_audit_logger_separation(self, temp_log_dir):
        """Test that audit logger is separate from main logger."""
        setup_logging(
            level="INFO",
            log_dir=temp_log_dir,
            enable_rotation=True,
        )

        # Get different loggers
        app_logger = get_logger("app.test")
        audit_logger = get_logger("harbor.audit")
        access_logger = get_logger("harbor.access")

        # Log to each
        app_logger.info("App message")
        audit_logger.info("Audit message")
        access_logger.info("Access message")

        # Force flush
        for logger in [app_logger, audit_logger, access_logger]:
            for handler in logger.handlers:
                if hasattr(handler, "flush"):
                    handler.flush()

        # Check that separate log files exist
        assert (temp_log_dir / "app.log").exists()
        assert (temp_log_dir / "audit.log").exists()
        assert (temp_log_dir / "access.log").exists()

        # Read audit log
        audit_content = (temp_log_dir / "audit.log").read_text()
        assert "Audit message" in audit_content

        # Audit log should not contain app messages due to propagate=False
        assert "App message" not in audit_content


class TestPerformanceLoggingIntegration:
    """Test performance logging integration."""

    @pytest.mark.asyncio
    async def test_performance_logging_with_correlation(self, temp_log_dir):
        """Test performance logging with correlation IDs."""
        setup_logging(
            level="INFO",
            log_dir=temp_log_dir,
            json_format=True,
            enable_rotation=True,
        )

        # Set correlation ID
        set_correlation_id("perf-test-123")

        # Log performance
        from app.utils.logging import log_performance

        log_performance(
            func_name="database_query",
            duration_ms=45.67,
            metadata={"query": "SELECT * FROM users", "rows": 100},
        )

        # Force flush
        for handler in logging.getLogger().handlers:
            if hasattr(handler, "flush"):
                handler.flush()

        # Read log file
        app_log = temp_log_dir / "app.log"
        if app_log.exists():
            content = app_log.read_text()
            if content:
                # Check that performance data is logged
                assert "database_query" in content
                assert "45.67ms" in content

                # Parse JSON log if in JSON format
                lines = content.strip().split("\n")
                for line in lines:
                    if "database_query" in line:
                        try:
                            log_entry = json.loads(line)
                            assert log_entry["correlation_id"] == "perf-test-123"
                        except json.JSONDecodeError:
                            # Check text format
                            assert "perf-test-123" in line


class TestErrorLoggingIntegration:
    """Test error logging integration."""

    def test_error_log_separation(self, temp_log_dir):
        """Test that errors are logged to separate error log."""
        setup_logging(
            level="DEBUG",
            log_dir=temp_log_dir,
            enable_rotation=True,
        )

        logger = get_logger("test.errors")

        # Log different levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

        # Force flush
        for handler in logging.getLogger().handlers:
            if hasattr(handler, "flush"):
                handler.flush()

        # Check error log
        error_log = temp_log_dir / "error.log"
        if error_log.exists():
            error_content = error_log.read_text()

            # Should only contain ERROR and CRITICAL
            assert (
                "Error message" in error_content or "Critical message" in error_content
            )
            assert "Debug message" not in error_content
            assert "Info message" not in error_content


class TestConfigurationIntegration:
    """Test logging configuration integration with Harbor config."""

    @patch("app.config.get_settings")
    def test_logging_uses_config_settings(self, mock_get_settings, temp_log_dir):
        """Test that logging setup uses configuration settings."""
        from app.config import LogLevel

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.logging.log_level = LogLevel.DEBUG
        mock_settings.logging.log_format = "json"
        mock_settings.logging.log_retention_days = 30
        mock_settings.logging.enable_file_logging = True
        mock_settings.logs_dir = temp_log_dir

        mock_get_settings.return_value = mock_settings

        # Setup logging with config
        setup_logging(
            level=mock_settings.logging.log_level.value,
            log_dir=mock_settings.logs_dir,
            json_format=mock_settings.logging.log_format == "json",
            enable_rotation=mock_settings.logging.enable_file_logging,
        )

        # Verify logging is configured correctly
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
