# tests/unit/security/test_middleware.py
"""Unit tests for security middleware components."""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.security import SecurityHeadersMiddleware
from app.middleware import RequestLoggingMiddleware, AuthenticationMiddleware
from app.config import DeploymentProfile


def test_security_headers_middleware():
    """Test security headers are applied correctly."""
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/test")
    def test_endpoint():
        return {"message": "test"}

    client = TestClient(app)
    response = client.get("/test")

    # Check common security headers
    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "X-Frame-Options" in response.headers
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "Server" in response.headers
    assert response.headers["Server"] == "Harbor"


def test_request_logging_middleware():
    """Test request logging middleware adds request ID."""
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/test")
    def test_endpoint():
        return {"message": "test"}

    client = TestClient(app)
    response = client.get("/test")

    # Check request ID is added
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) == 36  # UUID length

    # Check response time is added
    assert "X-Response-Time" in response.headers
    assert "ms" in response.headers["X-Response-Time"]


def test_authentication_middleware_public_paths():
    """Test authentication middleware allows public paths."""
    app = FastAPI()
    app.add_middleware(AuthenticationMiddleware)

    @app.get("/healthz")
    def health_check():
        return {"status": "healthy"}

    @app.get("/api/protected")
    def protected_endpoint(request: Request):
        # Check if auth was required
        return {"auth_required": getattr(request.state, "auth_required", False)}

    client = TestClient(app)

    # Public path should work
    response = client.get("/healthz")
    assert response.status_code == 200

    # Protected path should have auth_required flag
    response = client.get("/api/protected")
    assert response.status_code == 200
    assert response.json()["auth_required"] is True


def test_middleware_order():
    """Test middleware runs in correct order."""
    app = FastAPI()

    # Add middleware in specific order
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/test")
    def test_endpoint():
        return {"message": "test"}

    client = TestClient(app)
    response = client.get("/test")

    # Both middleware should have run
    assert "X-Content-Type-Options" in response.headers  # From security headers
    assert "X-Request-ID" in response.headers  # From request logging
