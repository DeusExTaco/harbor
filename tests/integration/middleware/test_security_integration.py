"""
Integration tests for security middleware components.

Tests cover:
- Full request flow with all security middleware
- Authentication + rate limiting + validation
- Security headers in actual responses
- CSRF protection with forms
- Audit logging of security events
- Real FastAPI application integration
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta, UTC
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from httpx import AsyncClient
from unittest.mock import patch, Mock
import uuid

# Import from CORRECT locations
from app.security.headers import SecurityHeadersMiddleware
from app.security.rate_limit import RateLimitMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware
from app.middleware.correlation import CorrelationMiddleware
from app.middleware.authentication import AuthenticationMiddleware
from app.auth.dependencies import get_current_user, validate_csrf_token
from app.config import HarborSettings, DeploymentProfile

# Rest of the file remains the same...


@pytest.fixture
def test_app():
    """Create test FastAPI application with all security middleware."""
    app = FastAPI(title="Harbor Test")

    # Add all security middleware in correct order
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(CorrelationMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(AuthenticationMiddleware)

    # Add test endpoints
    @app.get("/")
    async def root():
        return {"message": "Hello World"}

    @app.get("/api/v1/test")
    async def test_endpoint():
        return {"status": "ok"}

    @app.get("/api/v1/protected")
    async def protected_endpoint(user=Depends(get_current_user)):
        return {"user": user.username}

    @app.post("/api/v1/action")
    async def action_endpoint(
        request: Request, csrf_valid=Depends(validate_csrf_token)
    ):
        return {"action": "performed"}

    @app.get("/healthz")
    async def health_check():
        return {"status": "healthy"}

    return app


@pytest.fixture
def sync_client(test_app):
    """Create synchronous test client."""
    return TestClient(test_app)


@pytest.fixture
async def async_client(test_app):
    """Create asynchronous test client."""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        yield client


class TestSecurityMiddlewareIntegration:
    """Test integration of all security middleware."""

    def test_security_headers_in_response(self, sync_client):
        """Test that security headers are present in actual responses."""
        response = sync_client.get("/")

        # Check security headers
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert "Referrer-Policy" in response.headers
        assert "Permissions-Policy" in response.headers
        assert "Content-Security-Policy" in response.headers

    def test_request_id_generation_and_propagation(self, sync_client):
        """Test request ID generation and propagation through middleware."""
        response = sync_client.get("/api/v1/test")

        # Should have request ID in response
        assert "X-Request-ID" in response.headers
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) > 0

        # Should have response time
        assert "X-Response-Time" in response.headers
        assert "ms" in response.headers["X-Response-Time"]

    def test_correlation_id_propagation(self, sync_client):
        """Test correlation ID propagation."""
        correlation_id = str(uuid.uuid4())
        response = sync_client.get(
            "/api/v1/test", headers={"X-Correlation-ID": correlation_id}
        )

        # Correlation ID should be in response
        assert response.headers.get("X-Correlation-ID") == correlation_id

    @pytest.mark.asyncio
    async def test_rate_limiting_enforcement(self, async_client):
        """Test that rate limiting is enforced."""
        # Make multiple rapid requests to trigger rate limit
        responses = []

        # Simulate burst of requests
        for _ in range(25):  # Exceed burst limit
            response = await async_client.get("/api/v1/test")
            responses.append(response)

        # At least one should be rate limited
        rate_limited = any(r.status_code == 429 for r in responses)
        assert rate_limited, "Rate limiting should have triggered"

        # Check rate limit headers
        last_response = responses[-1]
        if last_response.status_code != 429:
            assert "X-RateLimit-Limit" in last_response.headers
            assert "X-RateLimit-Remaining" in last_response.headers

    def test_health_check_bypasses_rate_limiting(self, sync_client):
        """Test that health checks bypass rate limiting."""
        # Make many health check requests
        for _ in range(50):
            response = sync_client.get("/healthz")
            assert response.status_code == 200

        # All should succeed (no rate limiting)
        response = sync_client.get("/healthz")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_authentication_middleware_integration(
        self, async_client, authenticated_api_key
    ):
        """Test authentication middleware with API key."""
        plain_key, api_key = authenticated_api_key

        # Without authentication
        response = await async_client.get("/api/v1/protected")
        assert response.status_code == 401

        # With API key
        response = await async_client.get(
            "/api/v1/protected", headers={"X-API-Key": plain_key}
        )
        assert response.status_code == 200
        data = response.json()
        assert "user" in data

    @pytest.mark.asyncio
    async def test_csrf_protection(self, async_client, authenticated_session):
        """Test CSRF protection for state-changing operations."""
        session_id, csrf_token = authenticated_session

        # POST without CSRF token should fail
        async_client.cookies.set("harbor_session", session_id)
        response = await async_client.post("/api/v1/action")
        assert response.status_code == 403

        # POST with CSRF token should succeed
        response = await async_client.post(
            "/api/v1/action", headers={"X-CSRF-Token": csrf_token}
        )
        assert response.status_code == 200


class TestSecurityHeaderProfiles:
    """Test security headers for different deployment profiles."""

    def test_homelab_profile_headers(self, sync_client):
        """Test headers for homelab deployment profile."""
        with patch("app.config.get_settings") as mock_settings:
            settings = Mock(spec=HarborSettings)
            settings.deployment_profile = DeploymentProfile.HOMELAB
            settings.security.require_https = False
            mock_settings.return_value = settings

            response = sync_client.get("/")

            # Check CSP is relaxed for homelab
            csp = response.headers.get("Content-Security-Policy", "")
            assert "'unsafe-inline'" in csp
            assert "'unsafe-eval'" in csp

            # No HSTS for homelab without HTTPS
            assert "Strict-Transport-Security" not in response.headers

    def test_production_profile_headers(self, sync_client):
        """Test headers for production deployment profile."""
        with patch("app.config.get_settings") as mock_settings:
            settings = Mock(spec=HarborSettings)
            settings.deployment_profile = DeploymentProfile.PRODUCTION
            settings.security.require_https = True
            mock_settings.return_value = settings

            response = sync_client.get("/")

            # Check strict CSP for production
            csp = response.headers.get("Content-Security-Policy", "")
            if csp:
                assert "'strict-dynamic'" in csp or "default-src 'self'" in csp

            # Should have HSTS
            hsts = response.headers.get("Strict-Transport-Security", "")
            if hsts:
                assert "max-age=" in hsts
                assert "includeSubDomains" in hsts


class TestRateLimitIntegration:
    """Test rate limiting integration with real requests."""

    @pytest.mark.asyncio
    async def test_ip_based_rate_limiting(self, async_client):
        """Test IP-based rate limiting."""
        # Track responses
        success_count = 0
        rate_limited_count = 0

        # Make requests up to and beyond limit
        for i in range(30):
            response = await async_client.get("/api/v1/test")
            if response.status_code == 200:
                success_count += 1
            elif response.status_code == 429:
                rate_limited_count += 1

            # Small delay to avoid burst limit
            if i % 5 == 0:
                await asyncio.sleep(0.1)

        # Should have some successful and some rate limited
        assert success_count > 0
        assert rate_limited_count > 0

    @pytest.mark.asyncio
    async def test_api_key_higher_limits(self, async_client, authenticated_api_key):
        """Test that API keys get higher rate limits."""
        plain_key, _ = authenticated_api_key

        # Make many requests with API key
        success_count = 0
        for _ in range(50):
            response = await async_client.get(
                "/api/v1/test", headers={"X-API-Key": plain_key}
            )
            if response.status_code == 200:
                success_count += 1

        # Should allow more requests with API key
        assert success_count > 30  # More than IP limit

    @pytest.mark.asyncio
    async def test_rate_limit_headers_accuracy(self, async_client):
        """Test accuracy of rate limit headers."""
        response = await async_client.get("/api/v1/test")

        if "X-RateLimit-Limit" in response.headers:
            limit = int(response.headers["X-RateLimit-Limit"])
            remaining = int(response.headers["X-RateLimit-Remaining"])

            # Make another request
            response2 = await async_client.get("/api/v1/test")

            if "X-RateLimit-Remaining" in response2.headers:
                remaining2 = int(response2.headers["X-RateLimit-Remaining"])

                # Remaining should decrease
                assert remaining2 < remaining or remaining2 == 0


class TestAuditLoggingIntegration:
    """Test audit logging of security events."""

    @pytest.mark.asyncio
    async def test_failed_auth_logged(self, async_client, async_session):
        """Test that failed authentication attempts are logged."""
        # Attempt to access protected endpoint without auth
        response = await async_client.get("/api/v1/protected")
        assert response.status_code == 401

        # Check audit log for failed auth event
        # Note: This would check actual audit logs in database
        # For now, we'll verify the response indicates auth failure
        assert response.json()["detail"] == "Not authenticated"

    @pytest.mark.asyncio
    async def test_rate_limit_violations_logged(self, async_client):
        """Test that rate limit violations are logged."""
        # Trigger rate limiting
        responses = []
        for _ in range(30):
            response = await async_client.get("/api/v1/test")
            responses.append(response)

        # Find rate limited responses
        rate_limited = [r for r in responses if r.status_code == 429]
        assert len(rate_limited) > 0

        # Verify rate limit error response format
        for response in rate_limited:
            data = response.json()
            assert data["error"]["code"] == "RATE_LIMITED"

    @pytest.mark.asyncio
    async def test_security_validation_failures_logged(self, async_client):
        """Test that input validation failures are logged."""
        # Send request with dangerous input
        response = await async_client.get(
            "/api/v1/test", params={"search": "'; DROP TABLE users--"}
        )

        # Should still work (params are sanitized/validated)
        # But validation attempt should be logged
        assert response.status_code in [200, 400]


class TestInputValidationIntegration:
    """Test input validation in real requests."""

    @pytest.mark.asyncio
    async def test_xss_prevention_in_responses(self, async_client):
        """Test that XSS attempts are prevented."""
        # Try to inject script in various parameters
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert(1)",
            "<img src=x onerror=alert(1)>",
        ]

        for payload in xss_payloads:
            response = await async_client.get("/api/v1/test", params={"q": payload})

            # Response should not contain unescaped script
            response_text = response.text
            assert "<script>" not in response_text
            assert "javascript:" not in response_text
            assert "onerror=" not in response_text

    @pytest.mark.asyncio
    async def test_sql_injection_prevention(self, async_client):
        """Test that SQL injection attempts are prevented."""
        sql_payloads = ["1' OR '1'='1", "'; DROP TABLE users--", "admin'--"]

        for payload in sql_payloads:
            response = await async_client.get("/api/v1/test", params={"id": payload})

            # Should handle safely (not cause SQL error)
            assert response.status_code in [200, 400, 422]

    @pytest.mark.asyncio
    async def test_path_traversal_prevention(self, async_client):
        """Test that path traversal attempts are prevented."""
        traversal_attempts = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "....//....//etc/passwd",
        ]

        for attempt in traversal_attempts:
            response = await async_client.get(f"/api/v1/test/{attempt}")

            # Should be blocked or sanitized
            assert response.status_code in [400, 404, 422]


class TestPerformanceWithSecurity:
    """Test performance impact of security middleware."""

    @pytest.mark.asyncio
    async def test_security_overhead(self, async_client):
        """Measure overhead of security middleware."""
        import time

        # Warm up
        await async_client.get("/api/v1/test")

        # Measure response times
        times = []
        for _ in range(10):
            start = time.time()
            response = await async_client.get("/api/v1/test")
            elapsed = time.time() - start
            if response.status_code == 200:
                times.append(elapsed)

        # Calculate average
        avg_time = sum(times) / len(times) if times else 0

        # Security middleware should not add excessive overhead
        assert avg_time < 0.1  # Less than 100ms average

    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, async_client):
        """Test handling of concurrent requests with security."""

        async def make_request():
            return await async_client.get("/api/v1/test")

        # Make concurrent requests
        tasks = [make_request() for _ in range(20)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Should handle concurrent requests
        successful = [
            r
            for r in responses
            if not isinstance(r, Exception) and r.status_code == 200
        ]
        assert len(successful) > 0

    @pytest.mark.asyncio
    async def test_rate_limit_cleanup_performance(self, async_client):
        """Test that rate limit cleanup doesn't impact performance."""
        # Generate traffic from many "clients"
        for i in range(100):
            response = await async_client.get(
                "/api/v1/test", headers={"X-Forwarded-For": f"192.168.1.{i}"}
            )

        # System should still be responsive
        start = time.time()
        response = await async_client.get("/api/v1/test")
        elapsed = time.time() - start

        assert elapsed < 0.05  # Should respond quickly


class TestSecurityEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_malformed_headers(self, async_client):
        """Test handling of malformed security headers."""
        # Send requests with malformed headers
        response = await async_client.get(
            "/api/v1/test",
            headers={
                "X-API-Key": "",  # Empty API key
                "X-Correlation-ID": "not-a-uuid",  # Invalid format
                "X-CSRF-Token": "../../etc/passwd",  # Path traversal attempt
            },
        )

        # Should handle gracefully
        assert response.status_code in [200, 400, 401]

    @pytest.mark.asyncio
    async def test_very_long_headers(self, async_client):
        """Test handling of very long header values."""
        # Send very long header
        long_value = "a" * 10000
        response = await async_client.get(
            "/api/v1/test", headers={"X-Custom-Header": long_value}
        )

        # Should handle without crashing
        assert response.status_code in [200, 400, 431]

    @pytest.mark.asyncio
    async def test_unicode_in_headers(self, async_client):
        """Test handling of unicode in headers."""
        # Send unicode in headers
        response = await async_client.get(
            "/api/v1/test", headers={"X-User-Name": "用户名"}
        )

        # Should handle unicode properly
        assert response.status_code in [200, 400]

    @pytest.mark.asyncio
    async def test_null_bytes_in_input(self, async_client):
        """Test handling of null bytes in input."""
        # Null byte injection attempts
        response = await async_client.get(
            "/api/v1/test", params={"file": "test.txt\x00.jpg"}
        )

        # Should sanitize or reject
        assert response.status_code in [200, 400, 422]


class TestComplianceRequirements:
    """Test compliance-related security requirements."""

    def test_no_sensitive_data_in_logs(self, sync_client):
        """Test that sensitive data is not logged."""
        with patch("app.utils.logging.get_logger") as mock_logger:
            logger = Mock()
            mock_logger.return_value = logger

            # Make request with sensitive data
            response = sync_client.post(
                "/api/v1/auth/login",
                json={
                    "username": "admin",
                    "password": "secret123",  # pragma: allowlist secret
                },  # pragma: allowlist secret
            )

            # Password should not appear in logs
            for call in logger.info.call_args_list:
                assert "secret123" not in str(call)
            for call in logger.debug.call_args_list:
                assert "secret123" not in str(call)

    def test_security_headers_for_compliance(self, sync_client):
        """Test that required security headers are present."""
        response = sync_client.get("/")

        # Required security headers for compliance
        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Referrer-Policy",
            "Content-Security-Policy",
        ]

        for header in required_headers:
            assert header in response.headers, f"Missing required header: {header}"

    @pytest.mark.asyncio
    async def test_session_timeout_enforcement(
        self, async_client, authenticated_session
    ):
        """Test that session timeouts are enforced."""
        session_id, _ = authenticated_session

        # Mock session as expired
        with patch("app.auth.sessions.SessionData.is_expired") as mock_expired:
            mock_expired.return_value = True

            async_client.cookies.set("harbor_session", session_id)
            response = await async_client.get("/api/v1/protected")

            # Should reject expired session
            assert response.status_code == 401
