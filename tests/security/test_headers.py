# tests/unit/security/test_headers.py
"""Unit tests for security headers."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.security.headers import (
    SecurityHeadersMiddleware,
    get_security_headers_for_profile,
)
from app.config import DeploymentProfile


def test_security_headers_for_profiles():
    """Test security headers are generated correctly for each profile."""
    # Fix: Explicitly iterate over enum members
    for profile in list(DeploymentProfile):  # Convert to list to iterate
        headers = get_security_headers_for_profile(profile)

        # Common headers should always be present
        assert "X-Content-Type-Options" in headers
        assert "X-Frame-Options" in headers
        assert headers["X-Content-Type-Options"] == "nosniff"

        # Production should have HSTS
        if profile == DeploymentProfile.PRODUCTION:
            assert "Strict-Transport-Security" in headers


def test_middleware_applies_headers():
    """Test middleware applies headers to responses."""
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/test")
    def test_endpoint():
        return {"message": "test"}

    client = TestClient(app)
    response = client.get("/test")

    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
