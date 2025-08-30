# app/api/dependencies/rate_limit.py
"""
Rate limiting dependencies for FastAPI routes.

Implementation: M0 Milestone - Foundation Phase
"""

from fastapi import HTTPException, Request, status

from app.config import get_settings
from app.security.rate_limit import SlidingWindowRateLimiter
from app.utils.logging import get_logger


logger = get_logger(__name__)

# Create endpoint-specific rate limiters
settings = get_settings()

# Strict limiter for sensitive endpoints (e.g., login)
auth_limiter = SlidingWindowRateLimiter(
    max_requests=5,
    window_seconds=300,  # 5 requests per 5 minutes
)

# Standard endpoint limiter
endpoint_limiter = SlidingWindowRateLimiter(
    max_requests=30,
    window_seconds=60,  # 30 requests per minute
)

# Lenient limiter for read-only endpoints
read_limiter = SlidingWindowRateLimiter(
    max_requests=100,
    window_seconds=60,  # 100 requests per minute
)


async def check_rate_limit(
    request: Request,
    limiter: SlidingWindowRateLimiter = endpoint_limiter,
) -> None:
    """
    Check rate limit for specific endpoints.

    Args:
        request: FastAPI request
        limiter: Rate limiter to use

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    # Get client identifier
    client_ip = request.client.host if request.client else "unknown"
    client_key = f"{client_ip}:{request.url.path}"

    # Check rate limit
    allowed, info = await limiter.is_allowed(client_key)

    if not allowed:
        logger.warning(f"Rate limit exceeded for {client_key}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {info['window_seconds']} seconds.",
            headers={
                "Retry-After": str(info["window_seconds"]),
                "X-RateLimit-Limit": str(info["limit"]),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(info["reset_time"]),
            },
        )


async def check_auth_rate_limit(request: Request) -> None:
    """Rate limit for authentication endpoints."""
    await check_rate_limit(request, auth_limiter)


async def check_read_rate_limit(request: Request) -> None:
    """Rate limit for read-only endpoints."""
    await check_rate_limit(request, read_limiter)
