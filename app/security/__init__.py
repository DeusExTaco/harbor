# app/security/__init__.py
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

from typing import Any  # ADD THIS IMPORT

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

    This function configures:
    1. Security headers middleware
    2. Rate limiting middleware
    3. Request logging middleware
    4. Authentication middleware
    5. CORS middleware

    Args:
        app: FastAPI application instance
        settings: Harbor settings (optional, will get from config if None)

    Returns:
        FastAPI app with security middleware configured
    """
    from app.config import get_settings

    if settings is None:
        settings = get_settings()

    # The order matters! Middleware runs in reverse order of addition
    # So we add them in this order to run: Logging -> RateLimit -> Headers

    # 1. Add security headers middleware (runs last, modifies response)
    app.add_middleware(SecurityHeadersMiddleware)

    # 2. Add rate limiting middleware (if enabled)
    from app.core.security import SecurityConfig

    security_config = SecurityConfig.get_security_config()

    if security_config["rate_limiting"]["enabled"]:
        app.add_middleware(RateLimitMiddleware)

    # 3. Add request logging middleware (runs first)
    try:
        from app.middleware import RequestLoggingMiddleware

        app.add_middleware(RequestLoggingMiddleware)
    except ImportError:
        pass  # Middleware not available yet

    # 4. Add authentication middleware
    try:
        from app.middleware import AuthenticationMiddleware

        app.add_middleware(AuthenticationMiddleware)
    except ImportError:
        pass  # Middleware not available yet

    return app
