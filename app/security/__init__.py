"""
Harbor Container Updater - Security Module

Main security module providing authentication, authorization, and security middleware.
Following Harbor architecture design principles and security best practices.

Implementation: M0 Milestone - Foundation Phase
Part of: Authentication Foundation (v1: Simple)

Features:
- Security middleware integration
- Input validation and sanitization
- Rate limiting and protection
- Security headers management
- Authentication preparation (basic framework)
"""

from typing import Any

# Security middleware exports
from app.security.headers import (
    SecurityContext,
    SecurityHeadersMiddleware,
    SecurityResponseHandler,
    get_security_headers_for_profile,
)
from app.security.rate_limit import (
    RateLimitConfig,
    RateLimitMiddleware,
    SlidingWindowRateLimiter,
)
from app.security.validation import (
    ConfigurationValidator,
    ContainerIdentifier,
    ImageReference,
    InputSanitizer,
    RequestValidator,
    ScheduleTime,
    SecurityValidationError,
    URLReference,
)


# Security utilities
__all__ = [
    # Middleware
    "SecurityHeadersMiddleware",
    "RateLimitMiddleware",
    # Response handling
    "SecurityResponseHandler",
    "SecurityContext",
    # Rate limiting
    "SlidingWindowRateLimiter",
    "RateLimitConfig",
    # Input validation
    "InputSanitizer",
    "SecurityValidationError",
    "RequestValidator",
    "ConfigurationValidator",
    # Validation models
    "ContainerIdentifier",
    "ImageReference",
    "ScheduleTime",
    "URLReference",
    # Utilities
    "get_security_headers_for_profile",
    "setup_security_middleware",
]


def setup_security_middleware(app: Any, settings: Any = None) -> Any:
    """
    Set up all security middleware for Harbor application.

    Args:
        app: FastAPI application instance
        settings: Harbor settings (optional, will get from config if None)

    Returns:
        FastAPI app with security middleware configured
    """
    from app.config import get_settings

    if settings is None:
        settings = get_settings()

    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)

    # Add rate limiting middleware (if enabled)
    if RateLimitConfig.is_rate_limiting_enabled(settings.deployment_profile):
        app.add_middleware(RateLimitMiddleware)

    return app
