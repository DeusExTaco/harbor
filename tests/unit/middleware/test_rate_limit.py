# tests/unit/middleware/test_rate_limit.py
"""
Unit tests for rate limiting middleware.

Tests cover:
- IP-based rate limiting
- API key rate limiting
- Sliding window algorithm
- Rate limit headers
- Different deployment profiles
- Burst protection
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import Request, Response
from fastapi.responses import JSONResponse

# Import from the correct location - app.security.rate_limit
from app.security.rate_limit import (
    SlidingWindowRateLimiter,
    RateLimitMiddleware,
    RateLimitConfig,
)
from app.config import HarborSettings, DeploymentProfile


class TestSlidingWindowRateLimiter:
    """Test sliding window rate limiter implementation."""

    @pytest.mark.asyncio
    async def test_basic_rate_limiting(self):
        """Test basic rate limiting functionality."""
        limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=10)
        test_key = "test_client"

        # First 5 requests should be allowed
        for i in range(5):
            allowed, info = await limiter.is_allowed(test_key)
            assert allowed is True
            assert info["remaining"] == 4 - i
            assert info["limit"] == 5

        # 6th request should be blocked
        allowed, info = await limiter.is_allowed(test_key)
        assert allowed is False
        assert info["remaining"] == 0
        assert info["current_requests"] == 5

    @pytest.mark.asyncio
    async def test_sliding_window_behavior(self):
        """Test that old requests expire from the window."""
        limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=1)
        test_key = "test_client"

        # Make 3 requests
        for _ in range(3):
            allowed, _ = await limiter.is_allowed(test_key)
            assert allowed is True

        # 4th request blocked
        allowed, _ = await limiter.is_allowed(test_key)
        assert allowed is False

        # Wait for window to expire
        await asyncio.sleep(1.1)

        # Should be allowed again
        allowed, info = await limiter.is_allowed(test_key)
        assert allowed is True
        assert info["remaining"] == 2

    @pytest.mark.asyncio
    async def test_multiple_clients(self):
        """Test rate limiting for multiple clients."""
        limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=10)

        # Client 1
        allowed1, _ = await limiter.is_allowed("client1")
        allowed2, _ = await limiter.is_allowed("client1")
        allowed3, _ = await limiter.is_allowed("client1")

        assert allowed1 is True
        assert allowed2 is True
        assert allowed3 is False

        # Client 2 should have separate limit
        allowed1, _ = await limiter.is_allowed("client2")
        allowed2, _ = await limiter.is_allowed("client2")
        allowed3, _ = await limiter.is_allowed("client2")

        assert allowed1 is True
        assert allowed2 is True
        assert allowed3 is False

    @pytest.mark.asyncio
    async def test_cleanup_old_entries(self):
        """Test cleanup of old entries to prevent memory leaks."""
        limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=1)

        # Create entries for multiple clients
        for i in range(10):
            await limiter.is_allowed(f"client_{i}")

        # Check that entries exist
        assert len(limiter.requests) == 10

        # Wait for window to expire
        await asyncio.sleep(1.1)

        # Clean up old entries
        await limiter.cleanup_old_entries()

        # All entries should be cleaned up
        assert len(limiter.requests) == 0

    @pytest.mark.asyncio
    async def test_rate_limit_info_accuracy(self):
        """Test accuracy of rate limit information."""
        limiter = SlidingWindowRateLimiter(max_requests=10, window_seconds=60)
        test_key = "test_client"

        # Make some requests
        for i in range(7):
            allowed, info = await limiter.is_allowed(test_key)
            assert allowed is True
            assert info["limit"] == 10
            assert info["remaining"] == 9 - i
            assert info["window_seconds"] == 60
            assert info["current_requests"] == i + 1
            assert info["reset_time"] > time.time()


class TestRateLimitMiddleware:
    """Test rate limiting middleware."""

    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock(spec=Request)
        request.url = Mock()
        request.url.path = "/api/v1/containers"
        request.method = "GET"
        request.headers = {}
        request.client = Mock()
        request.client.host = "127.0.0.1"
        return request

    @pytest.fixture
    async def middleware_instance(self):
        """Create middleware instance and clean it up properly."""
        app = Mock()
        middleware = RateLimitMiddleware(app)

        # Store original cleanup task if it exists
        cleanup_task = getattr(middleware, "_cleanup_task", None)

        yield middleware

        # Properly cancel cleanup task if it exists
        if cleanup_task and hasattr(cleanup_task, "cancel"):
            try:
                cleanup_task.cancel()
                # Wait for cancellation to complete
                try:
                    await cleanup_task
                except asyncio.CancelledError:
                    pass
            except:
                pass

    @pytest.mark.asyncio
    async def test_rate_limit_initialization(self, middleware_instance):
        """Test middleware initialization with different profiles."""
        middleware = middleware_instance

        # Check limiter initialization - use actual values
        assert hasattr(middleware, "ip_limiter")
        assert hasattr(middleware, "api_key_limiter")
        assert hasattr(middleware, "burst_limiter")

        # Check that limiters have reasonable values
        assert middleware.ip_limiter.max_requests > 0
        assert middleware.api_key_limiter.max_requests > 0
        assert middleware.burst_limiter.max_requests > 0

    @pytest.mark.asyncio
    async def test_skip_rate_limiting_health_checks(
        self, mock_request, middleware_instance
    ):
        """Test that health checks skip rate limiting."""
        middleware = middleware_instance

        # Health check paths should skip rate limiting
        health_paths = ["/healthz", "/readyz", "/metrics"]

        for path in health_paths:
            mock_request.url.path = path
            assert middleware._should_skip_rate_limiting(mock_request) is True

    @pytest.mark.asyncio
    async def test_skip_rate_limiting_static_files(
        self, mock_request, middleware_instance
    ):
        """Test that static files skip rate limiting."""
        middleware = middleware_instance

        mock_request.url.path = "/static/style.css"
        assert middleware._should_skip_rate_limiting(mock_request) is True

    @pytest.mark.asyncio
    async def test_client_key_extraction_ip(self, mock_request, middleware_instance):
        """Test client key extraction for IP-based limiting."""
        middleware = middleware_instance

        # No API key or auth header
        mock_request.headers = {}
        key = middleware._get_client_key(mock_request)
        assert key == "ip:127.0.0.1"

    @pytest.mark.asyncio
    async def test_client_key_extraction_api_key(
        self, mock_request, middleware_instance
    ):
        """Test client key extraction for API key-based limiting."""
        middleware = middleware_instance

        # With API key
        test_api_key = "sk_harbor_test123456789"  # pragma: allowlist secret
        mock_request.headers = {"x-api-key": test_api_key}
        key = middleware._get_client_key(mock_request)

        # Key should start with "api_key:"
        assert key.startswith("api_key:")

        # The key should contain some part of the original API key
        # The implementation takes first 16 chars if key is longer than 16
        key_part = key.replace("api_key:", "")
        assert len(key_part) > 0  # Should have some key content

        # If the API key is longer than 16 chars, it should be truncated
        if len(test_api_key) > 16:
            assert key_part == test_api_key[:16]
        else:
            assert key_part == test_api_key

    @pytest.mark.asyncio
    async def test_client_ip_extraction_proxy(self, mock_request, middleware_instance):
        """Test client IP extraction with proxy headers in production."""
        middleware = middleware_instance

        # Test X-Forwarded-For
        mock_request.headers = {"x-forwarded-for": "192.168.1.100, 10.0.0.1"}
        ip = middleware._get_client_ip(mock_request)
        # Should get some IP
        assert ip

        # Test X-Real-IP
        mock_request.headers = {"x-real-ip": "192.168.1.200"}
        ip = middleware._get_client_ip(mock_request)
        assert ip

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded_response(
        self, mock_request, middleware_instance
    ):
        """Test response when rate limit is exceeded."""
        middleware = middleware_instance

        # Mock the limiter to return rate limit exceeded
        with patch.object(middleware, "_check_rate_limits") as mock_check:
            mock_check.return_value = (False, {"window_seconds": 60}, "IP address")

            async def call_next(req):
                return Response(content="test")

            response = await middleware.dispatch(mock_request, call_next)

            # Should return 429 status
            assert isinstance(response, JSONResponse)
            assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_rate_limit_headers_added(self, mock_request, middleware_instance):
        """Test that rate limit headers are added to responses."""
        middleware = middleware_instance

        # Mock successful rate limit check
        with patch.object(middleware, "_check_rate_limits") as mock_check:
            mock_check.return_value = (
                True,
                {
                    "limit": 100,
                    "remaining": 99,
                    "reset_time": int(time.time()) + 3600,
                    "window_seconds": 3600,
                },
                "IP address",
            )

            async def call_next(req):
                return Response(content="test")

            response = await middleware.dispatch(mock_request, call_next)

            # Check rate limit headers
            assert "X-RateLimit-Limit" in response.headers
            assert response.headers["X-RateLimit-Limit"] == "100"
            assert "X-RateLimit-Remaining" in response.headers
            assert response.headers["X-RateLimit-Remaining"] == "99"
            assert "X-RateLimit-Reset" in response.headers
            assert "X-RateLimit-Window" in response.headers
            assert "X-RateLimit-Type" in response.headers

    @pytest.mark.asyncio
    async def test_burst_protection(self, mock_request, middleware_instance):
        """Test burst protection limiting."""
        middleware = middleware_instance

        # Simulate burst requests
        client_key = "ip:127.0.0.1"  # pragma: allowlist secret

        # First check both limiters
        allowed, info, limiter_type = await middleware._check_rate_limits(
            mock_request, client_key
        )
        assert allowed is True

        # Make burst limit number of requests quickly
        for _ in range(middleware.burst_limiter.max_requests - 1):
            allowed, info, limiter_type = await middleware._check_rate_limits(
                mock_request, client_key
            )
            assert allowed is True

        # Next request should be blocked by burst limiter
        allowed, info, limiter_type = await middleware._check_rate_limits(
            mock_request, client_key
        )
        assert allowed is False
        assert limiter_type == "burst protection"

    @pytest.mark.asyncio
    async def test_api_key_higher_limits(self, mock_request, middleware_instance):
        """Test that API keys get higher rate limits."""
        middleware = middleware_instance

        # Test IP-based limits
        ip_key = "ip:127.0.0.1"
        _, info, _ = await middleware._check_rate_limits(mock_request, ip_key)
        ip_limit = info["limit"]

        # Test API key limits
        api_key = "api_key:test123"  # pragma: allowlist secret
        _, info, _ = await middleware._check_rate_limits(mock_request, api_key)
        api_limit = info["limit"]

        # API key should have higher limit
        assert api_limit > ip_limit


class TestRateLimitConfig:
    """Test rate limit configuration."""

    def test_get_limits_for_homelab(self):
        """Test rate limits for homelab profile."""
        limits = RateLimitConfig.get_limits_for_profile(DeploymentProfile.HOMELAB)

        assert limits["ip"]["requests"] == 100
        assert limits["ip"]["window"] == 3600
        assert limits["api_key"]["requests"] == 1000
        assert limits["burst"]["requests"] == 20

    def test_get_limits_for_production(self):
        """Test rate limits for production profile."""
        limits = RateLimitConfig.get_limits_for_profile(DeploymentProfile.PRODUCTION)

        assert limits["ip"]["requests"] == 100
        assert limits["api_key"]["requests"] == 5000
        assert limits["burst"]["requests"] == 50

    def test_get_limits_for_development(self):
        """Test rate limits for development profile."""
        limits = RateLimitConfig.get_limits_for_profile(DeploymentProfile.DEVELOPMENT)

        # Development should have very generous limits
        assert limits["ip"]["requests"] == 1000
        assert limits["api_key"]["requests"] == 10000
        assert limits["burst"]["requests"] == 100

    def test_rate_limiting_enabled_check(self):
        """Test checking if rate limiting is enabled."""
        # Should be enabled for all profiles by default
        assert (
            RateLimitConfig.is_rate_limiting_enabled(DeploymentProfile.HOMELAB) is True
        )
        assert (
            RateLimitConfig.is_rate_limiting_enabled(DeploymentProfile.PRODUCTION)
            is True
        )
        assert (
            RateLimitConfig.is_rate_limiting_enabled(DeploymentProfile.DEVELOPMENT)
            is True
        )


class TestRateLimitPerformance:
    """Performance tests for rate limiting."""

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test rate limiter with concurrent requests."""
        limiter = SlidingWindowRateLimiter(max_requests=100, window_seconds=10)

        async def make_request(client_id):
            return await limiter.is_allowed(f"client_{client_id % 10}")

        # Create 100 concurrent requests from 10 clients
        tasks = [make_request(i) for i in range(100)]
        results = await asyncio.gather(*tasks)

        # Should handle concurrent access without errors
        assert len(results) == 100

    @pytest.mark.asyncio
    async def test_cleanup_performance(self):
        """Test cleanup performance with many clients."""
        limiter = SlidingWindowRateLimiter(max_requests=10, window_seconds=1)

        # Create entries for many clients
        for i in range(1000):
            await limiter.is_allowed(f"client_{i}")

        # Measure cleanup time
        start_time = time.time()
        await limiter.cleanup_old_entries()
        cleanup_time = time.time() - start_time

        # Cleanup should be fast even with many entries
        assert cleanup_time < 0.1  # Less than 100ms
