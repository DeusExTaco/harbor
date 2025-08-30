# tests/integration/test_security_integration.py
"""Integration tests for security components."""

import pytest
import asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app
from app.security.rate_limit import SlidingWindowRateLimiter


@pytest.mark.asyncio
async def test_rate_limiting():
    """Test rate limiting works correctly."""
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=10)

    # Test within limits
    for i in range(3):
        allowed, info = await limiter.is_allowed("test_client")
        assert allowed is True
        assert info["remaining"] == 2 - i

    # Test exceeding limits
    allowed, info = await limiter.is_allowed("test_client")
    assert allowed is False
    assert info["remaining"] == 0


def test_security_headers_applied():
    """Test security headers are applied to all responses."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/healthz")

    # Check security headers
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "Server" in response.headers
    assert response.headers["Server"] == "Harbor"


def test_input_validation():
    """Test input validation and sanitization."""
    from app.security.validation import InputSanitizer, SecurityValidationError

    sanitizer = InputSanitizer()

    # Test HTML sanitization
    dangerous_html = "<script>alert('xss')</script>"
    safe_html = sanitizer.sanitize_html(dangerous_html)
    assert "<script>" not in safe_html
    assert "&lt;script&gt;" in safe_html

    # Test container name validation
    with pytest.raises(SecurityValidationError):
        sanitizer.sanitize_container_name("invalid/name")

    valid_name = sanitizer.sanitize_container_name("valid-name")
    assert valid_name == "valid-name"
