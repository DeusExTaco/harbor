# tests/unit/security/test_rate_limit.py
"""Unit tests for rate limiting functionality."""

import asyncio
import pytest

from app.security.rate_limit import SlidingWindowRateLimiter, RateLimitConfig
from app.config import DeploymentProfile


@pytest.mark.asyncio
async def test_sliding_window_rate_limiter():
    """Test sliding window rate limiter allows correct number of requests."""
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=1)

    # First 3 requests should be allowed
    for i in range(3):
        allowed, info = await limiter.is_allowed("test_client")
        assert allowed is True
        assert info["remaining"] == 2 - i

    # 4th request should be blocked
    allowed, info = await limiter.is_allowed("test_client")
    assert allowed is False
    assert info["remaining"] == 0

    # Wait for window to expire
    await asyncio.sleep(1.1)

    # Should be allowed again
    allowed, info = await limiter.is_allowed("test_client")
    assert allowed is True


@pytest.mark.asyncio
async def test_rate_limiter_different_clients():
    """Test rate limiter tracks different clients separately."""
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=10)

    # Client 1 requests
    allowed1, _ = await limiter.is_allowed("client1")
    allowed2, _ = await limiter.is_allowed("client1")
    allowed3, _ = await limiter.is_allowed("client1")

    assert allowed1 is True
    assert allowed2 is True
    assert allowed3 is False  # Client 1 blocked

    # Client 2 should still be allowed
    allowed4, _ = await limiter.is_allowed("client2")
    assert allowed4 is True


def test_rate_limit_config():
    """Test rate limit configuration for different profiles."""
    homelab_config = RateLimitConfig.get_limits_for_profile(DeploymentProfile.HOMELAB)
    assert homelab_config["ip"]["requests"] == 100
    assert homelab_config["api_key"]["requests"] == 1000

    prod_config = RateLimitConfig.get_limits_for_profile(DeploymentProfile.PRODUCTION)
    assert prod_config["ip"]["requests"] == 100
    assert prod_config["api_key"]["requests"] == 5000


@pytest.mark.asyncio
async def test_rate_limiter_cleanup():
    """Test rate limiter cleanup removes old entries."""
    limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=1)

    # Add some requests
    await limiter.is_allowed("client1")
    await limiter.is_allowed("client2")

    # Wait for window to expire
    await asyncio.sleep(1.1)

    # Cleanup should remove old entries
    await limiter.cleanup_old_entries()

    # Check that old entries are gone by verifying full limit is available
    allowed, info = await limiter.is_allowed("client1")
    assert allowed is True
    assert info["remaining"] == 4  # Full limit minus this request
