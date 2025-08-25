"""
Harbor Container Updater - Rate Limiting Middleware

Implements rate limiting middleware for API protection and resource management.
Following Harbor architecture design principles and security best practices.

Implementation: M0 Milestone - Foundation Phase
Part of: Authentication Foundation (v1: Simple)

Features:
- IP-based and API key-based rate limiting
- Sliding window algorithm for accurate rate limiting
- Profile-aware rate limits (home lab vs production)
- Redis backend support for distributed deployments (future)
- In-memory backend for simple deployments
"""

import asyncio
import functools
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.config import DeploymentProfile, get_settings
from app.security.headers import SecurityResponseHandler


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter implementation.

    Uses a sliding window algorithm to track requests over time windows.
    More accurate than fixed window rate limiting.
    """

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        """
        Initialize sliding window rate limiter.

        Args:
            max_requests: Maximum requests allowed in the time window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(self, key: str) -> tuple[bool, dict[str, Any]]:
        """
        Check if request is allowed and update counters.

        Args:
            key: Unique key for the client (IP, API key, etc.)

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        async with self._lock:
            current_time = time.time()
            window_start = current_time - self.window_seconds

            # Get request times for this key
            request_times = self.requests[key]

            # Remove old requests outside the window
            request_times[:] = [t for t in request_times if t > window_start]

            # Check if we're under the limit
            current_requests = len(request_times)
            is_allowed = current_requests < self.max_requests

            if is_allowed:
                # Add current request
                request_times.append(current_time)

            # Calculate rate limit info
            remaining = max(
                0, self.max_requests - current_requests - (1 if is_allowed else 0)
            )
            reset_time = int(current_time + self.window_seconds)

            rate_limit_info = {
                "limit": self.max_requests,
                "remaining": remaining,
                "reset_time": reset_time,
                "window_seconds": self.window_seconds,
                "current_requests": current_requests + (1 if is_allowed else 0),
            }

            return is_allowed, rate_limit_info

    async def cleanup_old_entries(self) -> None:
        """Clean up old entries to prevent memory leaks."""
        async with self._lock:
            current_time = time.time()
            window_start = current_time - self.window_seconds

            # Clean up entries that are completely outside the window
            keys_to_remove = []
            for key, request_times in self.requests.items():
                # Remove old requests
                request_times[:] = [t for t in request_times if t > window_start]

                # If no requests left, mark key for removal
                if not request_times:
                    keys_to_remove.append(key)

            # Remove empty keys
            for key in keys_to_remove:
                del self.requests[key]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for Harbor API protection.

    Implements multiple rate limiting strategies:
    - IP-based rate limiting for anonymous requests
    - API key-based rate limiting for authenticated requests
    - Different limits based on deployment profile
    - Burst allowance for reasonable usage spikes
    """

    def __init__(self, app: ASGIApp) -> None:
        """Initialize rate limiting middleware."""
        super().__init__(app)
        self.settings = get_settings()
        self.profile = self.settings.deployment_profile

        # Initialize rate limiters based on profile
        self._initialize_limiters()

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

    def _initialize_limiters(self) -> None:
        """Initialize rate limiters based on deployment profile."""

        if self.profile == DeploymentProfile.HOMELAB:
            # Generous limits for home lab
            self.ip_limiter = SlidingWindowRateLimiter(
                max_requests=100,  # 100 requests per hour
                window_seconds=3600,  # 1 hour
            )
            self.api_key_limiter = SlidingWindowRateLimiter(
                max_requests=1000,  # 1000 requests per hour for API keys
                window_seconds=3600,  # 1 hour
            )
            # Burst limiter (short term)
            self.burst_limiter = SlidingWindowRateLimiter(
                max_requests=20,  # 20 requests per minute
                window_seconds=60,  # 1 minute
            )

        elif self.profile == DeploymentProfile.DEVELOPMENT:
            # Very generous limits for development
            self.ip_limiter = SlidingWindowRateLimiter(
                max_requests=1000,  # High limit for development
                window_seconds=3600,
            )
            self.api_key_limiter = SlidingWindowRateLimiter(
                max_requests=10000,  # Very high for testing
                window_seconds=3600,
            )
            self.burst_limiter = SlidingWindowRateLimiter(
                max_requests=100,  # Allow burst testing
                window_seconds=60,
            )

        elif self.profile == DeploymentProfile.PRODUCTION:
            # Stricter limits for production
            self.ip_limiter = SlidingWindowRateLimiter(
                max_requests=self.settings.security.api_rate_limit_per_hour
                // 5,  # Lower for IPs
                window_seconds=3600,
            )
            self.api_key_limiter = SlidingWindowRateLimiter(
                max_requests=self.settings.security.api_rate_limit_per_hour,
                window_seconds=3600,
            )
            self.burst_limiter = SlidingWindowRateLimiter(
                max_requests=50,  # Moderate burst allowance
                window_seconds=60,
            )

        elif self.profile == DeploymentProfile.STAGING:
            # Production-like but more permissive
            self.ip_limiter = SlidingWindowRateLimiter(
                max_requests=200, window_seconds=3600
            )
            self.api_key_limiter = SlidingWindowRateLimiter(
                max_requests=2000, window_seconds=3600
            )
            self.burst_limiter = SlidingWindowRateLimiter(
                max_requests=30, window_seconds=60
            )

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Apply rate limiting to requests."""

        # Skip rate limiting for health checks and static files
        if self._should_skip_rate_limiting(request):
            return await call_next(request)

        # Get client identifier
        client_key = self._get_client_key(request)

        # Check rate limits
        is_allowed, rate_limit_info, limiter_type = await self._check_rate_limits(
            request, client_key
        )

        if not is_allowed:
            # Rate limit exceeded
            retry_after = self._calculate_retry_after(rate_limit_info)
            return SecurityResponseHandler.rate_limit_response(
                retry_after=retry_after,
                message=f"Rate limit exceeded for {limiter_type}. Try again in {retry_after} seconds.",
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        self._add_rate_limit_headers(response, rate_limit_info, limiter_type)

        return response

    def _should_skip_rate_limiting(self, request: Request) -> bool:
        """Check if rate limiting should be skipped for this request."""
        path = request.url.path

        # Skip for health checks
        if path in ["/healthz", "/readyz", "/metrics"]:
            return True

        # Skip for static files
        if path.startswith("/static/"):
            return True

        # Skip in development for certain paths
        if self.profile == DeploymentProfile.DEVELOPMENT:
            if path.startswith("/docs") or path.startswith("/redoc"):
                return True

        return False

    def _get_client_key(self, request: Request) -> str:
        """Get client identifier for rate limiting."""

        # Check for API key first (higher priority)
        api_key = request.headers.get("x-api-key") or request.headers.get(
            "authorization"
        )
        if api_key:
            # Use hash of API key as identifier
            import hashlib

            return f"api_key:{hashlib.sha256(api_key.encode()).hexdigest()[:16]}"

        # Fall back to IP address
        client_ip = self._get_client_ip(request)
        return f"ip:{client_ip}"

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address, handling proxy headers."""

        # Handle proxy headers in production
        if self.profile == DeploymentProfile.PRODUCTION:
            # Trust proxy headers in production (behind load balancer)
            forwarded_for = request.headers.get("x-forwarded-for")
            if forwarded_for:
                return forwarded_for.split(",")[0].strip()

            real_ip = request.headers.get("x-real-ip")
            if real_ip:
                return real_ip.strip()

        # Direct connection
        return request.client.host if request.client else "unknown"

    async def _check_rate_limits(
        self, request: Request, client_key: str
    ) -> tuple[bool, dict[str, Any], str]:
        """Check all applicable rate limits."""

        # Determine which limiters to check
        if client_key.startswith("api_key:"):
            # API key rate limiting
            is_allowed, rate_info = await self.api_key_limiter.is_allowed(client_key)
            limiter_type = "API key"
        else:
            # IP-based rate limiting
            is_allowed, rate_info = await self.ip_limiter.is_allowed(client_key)
            limiter_type = "IP address"

        # Always check burst limiter
        burst_allowed, burst_info = await self.burst_limiter.is_allowed(client_key)

        # Must pass both rate limits
        if not burst_allowed:
            return False, burst_info, "burst protection"

        return is_allowed, rate_info, limiter_type

    def _calculate_retry_after(self, rate_limit_info: dict[str, Any]) -> int:
        """Calculate retry-after seconds."""

        # Use window_seconds as a reasonable retry time
        # In production, could be more sophisticated
        window_seconds = rate_limit_info.get("window_seconds")
        if window_seconds is None:
            return 60  # Default fallback

        return min(int(window_seconds), 300)  # Max 5 minutes

    def _add_rate_limit_headers(
        self, response: Response, rate_limit_info: dict[str, Any], limiter_type: str
    ) -> None:
        """Add rate limit headers to response."""

        response.headers["X-RateLimit-Limit"] = str(rate_limit_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(rate_limit_info["reset_time"])
        response.headers["X-RateLimit-Window"] = str(rate_limit_info["window_seconds"])
        response.headers["X-RateLimit-Type"] = limiter_type.lower().replace(" ", "-")

    async def _periodic_cleanup(self) -> None:
        """Periodically clean up old rate limit entries."""
        while True:
            try:
                # Clean up every 5 minutes
                await asyncio.sleep(300)

                # Clean up all limiters
                await self.ip_limiter.cleanup_old_entries()
                await self.api_key_limiter.cleanup_old_entries()
                await self.burst_limiter.cleanup_old_entries()

            except asyncio.CancelledError:
                break
            except Exception:
                # Log error but continue cleanup loop
                # TODO: Use proper logging when available
                pass

    def __del__(self) -> None:
        """Clean up when middleware is destroyed."""
        if hasattr(self, "_cleanup_task"):
            self._cleanup_task.cancel()


# =============================================================================
# Rate Limiting Utilities
# =============================================================================


class RateLimitConfig:
    """Configuration helper for rate limiting settings."""

    @classmethod
    def get_limits_for_profile(
        cls, profile: DeploymentProfile
    ) -> dict[str, dict[str, int]]:
        """Get rate limits configuration for a deployment profile."""

        configs = {
            DeploymentProfile.HOMELAB: {
                "ip": {"requests": 100, "window": 3600},  # 100/hour
                "api_key": {"requests": 1000, "window": 3600},  # 1000/hour
                "burst": {"requests": 20, "window": 60},  # 20/minute
            },
            DeploymentProfile.DEVELOPMENT: {
                "ip": {"requests": 1000, "window": 3600},  # 1000/hour
                "api_key": {"requests": 10000, "window": 3600},  # 10000/hour
                "burst": {"requests": 100, "window": 60},  # 100/minute
            },
            DeploymentProfile.STAGING: {
                "ip": {"requests": 200, "window": 3600},  # 200/hour
                "api_key": {"requests": 2000, "window": 3600},  # 2000/hour
                "burst": {"requests": 30, "window": 60},  # 30/minute
            },
            DeploymentProfile.PRODUCTION: {
                "ip": {"requests": 100, "window": 3600},  # 100/hour (conservative)
                "api_key": {"requests": 5000, "window": 3600},  # 5000/hour
                "burst": {"requests": 50, "window": 60},  # 50/minute
            },
        }

        return configs.get(profile, configs[DeploymentProfile.HOMELAB])

    @classmethod
    def is_rate_limiting_enabled(cls, profile: DeploymentProfile) -> bool:
        """Check if rate limiting should be enabled for a profile."""

        # Always enable rate limiting except for development (optional)
        if profile == DeploymentProfile.DEVELOPMENT:
            # Could be disabled for development, but enabled by default
            return True

        return True


# =============================================================================
# Rate Limit Decorators (Future)
# =============================================================================


def rate_limit(
    max_requests: int,
    window_seconds: int = 3600,
    key_func: Callable[..., str] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for applying rate limits to specific endpoints.

    TODO: Implement in later milestones for fine-grained control.

    Args:
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds
        key_func: Function to generate rate limit key from request
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # Store rate limit metadata for future use
        rate_limit_config = {
            "max_requests": max_requests,
            "window_seconds": window_seconds,
            "key_func": key_func,
        }

        # Use functools.wraps to properly handle function metadata
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        # Store metadata using setattr - MyPy doesn't recognize this pattern
        # but it's valid Python and commonly used in decorators
        wrapper._rate_limit = rate_limit_config  # type: ignore[attr-defined]

        return wrapper

    return decorator


# =============================================================================
# Testing and Utilities
# =============================================================================


async def test_rate_limiter() -> None:
    """Test rate limiter functionality."""

    print("🚦 Testing Harbor Rate Limiter")
    print("=" * 35)

    # Test sliding window rate limiter
    limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=10)

    # Test multiple requests
    test_key = "test_client"

    print(
        f"Testing {limiter.max_requests} requests in {limiter.window_seconds} seconds..."
    )

    for i in range(7):  # Try 7 requests (limit is 5)
        allowed, info = await limiter.is_allowed(test_key)
        status = "✅ ALLOWED" if allowed else "❌ BLOCKED"
        print(f"Request {i + 1}: {status} (remaining: {info['remaining']})")

        if i == 4:  # After 5 requests, wait a bit
            print("  ⏳ Waiting 2 seconds...")
            await asyncio.sleep(2)

    print("\n📊 Rate Limit Test Complete")


if __name__ == "__main__":
    """Rate limiting testing and utilities"""

    # Run test if script is executed directly
    asyncio.run(test_rate_limiter())
