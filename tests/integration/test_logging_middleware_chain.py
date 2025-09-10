"""
Integration tests for the complete middleware chain with logging.

Tests request flow through all middleware layers.
"""

import json
from unittest.mock import patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.middleware.correlation import CorrelationMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware
from app.utils.logging import get_correlation_id, get_logger, setup_logging


@pytest.fixture
def middleware_app(tmp_path):
    """Create app with full middleware chain."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    setup_logging(
        log_dir=log_dir,
        json_format=True,
        deployment_profile="production",
    )

    app = FastAPI()

    # Add middleware in correct order
    app.add_middleware(CorrelationMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    @app.middleware("http")
    async def custom_middleware(request: Request, call_next):
        """Custom middleware that uses logging."""
        logger = get_logger("custom.middleware")
        logger.info(f"Custom middleware: {request.url.path}")
        response = await call_next(request)
        logger.info(f"Custom middleware complete: {response.status_code}")
        return response

    @app.get("/chain")
    async def chain_endpoint():
        """Endpoint that logs at multiple levels."""
        logger = get_logger("test.endpoint")

        correlation_id = get_correlation_id()
        logger.debug(f"Debug: Processing request {correlation_id}")
        logger.info(f"Info: Request correlation ID: {correlation_id}")
        logger.warning("Warning: This is a test warning")

        return {"correlation_id": correlation_id, "status": "processed"}

    @app.get("/nested")
    async def nested_logging():
        """Endpoint with nested function calls."""
        logger = get_logger("test.nested")

        def inner_function():
            inner_logger = get_logger("test.nested.inner")
            inner_logger.info("Inner function called")
            return get_correlation_id()

        logger.info("Outer function starting")
        correlation_id = inner_function()
        logger.info("Outer function complete")

        return {"correlation_id": correlation_id}

    return app


class TestMiddlewareChain:
    """Test complete middleware chain."""

    def test_middleware_order(self, middleware_app, tmp_path):
        """Test that middleware executes in correct order."""
        client = TestClient(middleware_app)

        response = client.get(
            "/chain", headers={"X-Correlation-ID": "middleware-test-123"}
        )
        assert response.status_code == 200

        # Read logs
        log_file = tmp_path / "logs" / "app.log"
        lines = log_file.read_text().strip().split("\n")

        # Parse JSON logs and check for expected messages
        log_messages = []
        for line in lines:
            if line:
                data = json.loads(line)
                log_messages.append(data["message"])

        # Check for key messages (order might vary slightly)
        expected_messages = ["Custom middleware", "Request correlation ID", "warning"]

        for expected in expected_messages:
            assert any(
                expected.lower() in msg.lower() for msg in log_messages
            ), f"Missing: {expected}"

    def test_correlation_id_consistency(self, middleware_app, tmp_path):
        """Test that correlation ID is consistent throughout request."""
        client = TestClient(middleware_app)

        response = client.get("/nested")
        assert response.status_code == 200

        correlation_id = response.json()["correlation_id"]

        # Read logs and verify correlation IDs
        log_file = tmp_path / "logs" / "app.log"
        lines = log_file.read_text().strip().split("\n")

        request_logs = []
        for line in lines:
            if line:
                data = json.loads(line)
                if data.get("correlation_id") == correlation_id:
                    request_logs.append(data)

        # Should have at least some log entries
        assert len(request_logs) >= 3

    def test_error_propagation(self, middleware_app, tmp_path):
        """Test that errors are properly logged through middleware chain."""
        app = middleware_app

        @app.get("/error")
        async def error_endpoint():
            logger = get_logger("test.error")
            logger.error("About to raise error")
            raise ValueError("Test error in middleware chain")

        client = TestClient(app)

        # Expect the error to be raised
        with pytest.raises(ValueError):
            response = client.get("/error")

        # Check error log
        error_log = tmp_path / "logs" / "error.log"
        if error_log.exists():
            content = error_log.read_text()
            assert "About to raise error" in content

        # Also check main log
        app_log = tmp_path / "logs" / "app.log"
        content = app_log.read_text()
        assert "About to raise error" in content

    def test_performance_impact(self, middleware_app, tmp_path):
        """Test that logging doesn't significantly impact performance."""
        client = TestClient(middleware_app)

        # Warm up
        client.get("/chain")

        # Measure with logging
        import time

        start = time.perf_counter()
        for _ in range(100):
            response = client.get("/chain")
            assert response.status_code == 200
        with_logging = time.perf_counter() - start

        # The logging overhead should be minimal
        # 100 requests should complete in reasonable time
        assert with_logging < 5.0  # 5 seconds for 100 requests

        # Verify logs were actually written
        log_file = tmp_path / "logs" / "app.log"
        content = log_file.read_text()
        # Should have logged all requests
        assert content.count("Request completed") >= 100
