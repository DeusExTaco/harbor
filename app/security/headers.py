"""
Harbor Container Updater - Security Headers Middleware

Implements security headers middleware for production readiness and security hardening.
Following Harbor architecture design principles and security best practices.

Implementation: M0 Milestone - Foundation Phase
Part of: Authentication Foundation (v1: Simple)

Features:
- HTTP security headers (HSTS, CSP, X-Frame-Options, etc.)
- Profile-aware security level enforcement
- Development-friendly defaults with production security
- Comprehensive security header coverage
"""

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.config import DeploymentProfile, get_settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Security headers middleware for Harbor.

    Implements comprehensive security headers based on deployment profile:
    - Home lab: Basic security with development-friendly defaults
    - Development: Relaxed security for debugging
    - Production: Strict security headers for production deployment
    """

    def __init__(self, app: ASGIApp) -> None:
        """Initialize security headers middleware."""
        super().__init__(app)
        self.settings = get_settings()
        self.profile = self.settings.deployment_profile

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Apply security headers to all responses."""

        # Get the response from the next middleware/handler
        response = await call_next(request)

        # Apply security headers based on deployment profile
        self._apply_security_headers(response, request)

        return response

    def _apply_security_headers(self, response: Response, request: Request) -> None:
        """Apply security headers based on deployment profile."""

        # Common security headers for all profiles
        self._apply_common_headers(response)

        # Profile-specific headers
        if self.profile == DeploymentProfile.HOMELAB:
            self._apply_homelab_headers(response, request)
        elif self.profile == DeploymentProfile.DEVELOPMENT:
            self._apply_development_headers(response, request)
        elif self.profile == DeploymentProfile.PRODUCTION:
            self._apply_production_headers(response, request)
        elif self.profile == DeploymentProfile.STAGING:
            self._apply_staging_headers(response, request)

    def _apply_common_headers(self, response: Response) -> None:
        """Apply security headers common to all deployment profiles."""

        # Server identification
        response.headers["Server"] = "Harbor"  # Don't reveal technology stack

        # Content security
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Feature policy (permissions policy)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "camera=(), "
            "microphone=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "accelerometer=(), "
            "gyroscope=()"
        )

    def _apply_homelab_headers(self, response: Response, request: Request) -> None:
        """Apply security headers for home lab deployment."""

        # Content Security Policy (relaxed for home lab)
        # Allow inline scripts and styles for easier development
        csp_homelab = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "connect-src 'self' ws: wss:; "
            "font-src 'self'; "
            "object-src 'none'; "
            "media-src 'self'; "
            "frame-src 'none'"
        )
        response.headers["Content-Security-Policy"] = csp_homelab

        # HTTPS headers (only if HTTPS is required)
        if self.settings.security.require_https:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        # Cache control for home lab (allow some caching)
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "public, max-age=3600"  # 1 hour
        elif request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

    def _apply_development_headers(self, response: Response, request: Request) -> None:
        """Apply security headers for development environment."""

        # Very relaxed CSP for development
        csp_dev = (
            "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "connect-src 'self' ws: wss: http: https:; "
            "img-src 'self' data: blob: http: https:; "
            "font-src 'self' data: http: https:; "
            "style-src 'self' 'unsafe-inline' http: https:; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' http: https:"
        )
        response.headers["Content-Security-Policy"] = csp_dev

        # No HSTS in development (allows HTTP testing)
        # Cache control - no caching in development
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

        # Development-specific headers
        response.headers["X-Harbor-Environment"] = "development"

    def _apply_production_headers(self, response: Response, request: Request) -> None:
        """Apply strict security headers for production deployment."""

        # Strict Content Security Policy for production
        csp_production = (
            "default-src 'self'; "
            "script-src 'self' 'strict-dynamic'; "
            "style-src 'self'; "
            "img-src 'self' data: blob:; "
            "connect-src 'self'; "
            "font-src 'self'; "
            "object-src 'none'; "
            "media-src 'self'; "
            "frame-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers["Content-Security-Policy"] = csp_production

        # Strict Transport Security (HSTS) - mandatory in production
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )

        # Additional production security headers
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-site"

        # Cache control for production
        if request.url.path.startswith("/static/"):
            # Long caching for static assets with versioning
            response.headers["Cache-Control"] = (
                "public, max-age=31536000, immutable"  # 1 year
            )
        elif request.url.path.startswith("/api/"):
            # No caching for API responses
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        # Remove server information in production
        response.headers["Server"] = "Harbor"

    def _apply_staging_headers(self, response: Response, request: Request) -> None:
        """Apply security headers for staging environment."""

        # Production-like CSP but slightly relaxed for testing
        csp_staging = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "  # Allow inline for testing
            "style-src 'self' 'unsafe-inline'; "  # Allow inline for testing
            "img-src 'self' data: blob:; "
            "connect-src 'self'; "
            "font-src 'self'; "
            "object-src 'none'; "
            "media-src 'self'; "
            "frame-src 'none'"
        )
        response.headers["Content-Security-Policy"] = csp_staging

        # HSTS for staging
        response.headers["Strict-Transport-Security"] = (
            "max-age=86400; includeSubDomains"  # 1 day for staging
        )

        # Staging-specific headers
        response.headers["X-Harbor-Environment"] = "staging"

        # Cache control
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"


class SecurityResponseHandler:
    """Handle security-related responses and errors."""

    @staticmethod
    def security_error_response(
        message: str, status_code: int = 403, error_code: str = "SECURITY_ERROR"
    ) -> JSONResponse:
        """Create a standardized security error response."""

        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "error": {
                    "code": error_code,
                    "message": message,
                },
                "timestamp": "2024-01-15T10:30:00Z",  # TODO: Use actual timestamp
            },
            headers={
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Cache-Control": "no-cache, no-store, must-revalidate",
            },
        )

    @staticmethod
    def rate_limit_response(
        retry_after: int = 60, message: str = "Rate limit exceeded"
    ) -> JSONResponse:
        """Create a rate limit error response."""

        return JSONResponse(
            status_code=429,
            content={
                "success": False,
                "error": {
                    "code": "RATE_LIMITED",
                    "message": message,
                    "retry_after_seconds": retry_after,
                },
                "timestamp": "2024-01-15T10:30:00Z",  # TODO: Use actual timestamp
            },
            headers={
                "Retry-After": str(retry_after),
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Cache-Control": "no-cache, no-store, must-revalidate",
            },
        )

    @staticmethod
    def authentication_error_response(
        message: str = "Authentication required",
    ) -> JSONResponse:
        """Create an authentication error response."""

        return SecurityResponseHandler.security_error_response(
            message=message, status_code=401, error_code="AUTHENTICATION_REQUIRED"
        )

    @staticmethod
    def authorization_error_response(
        message: str = "Insufficient permissions",
    ) -> JSONResponse:
        """Create an authorization error response."""

        return SecurityResponseHandler.security_error_response(
            message=message, status_code=403, error_code="AUTHORIZATION_FAILED"
        )


# =============================================================================
# Security Context for Request Tracking
# =============================================================================


class SecurityContext:
    """Security context for tracking security-related request information."""

    def __init__(self, request: Request) -> None:
        """Initialize security context from request."""
        self.request = request
        self.client_ip = self._get_client_ip()
        self.user_agent = request.headers.get("user-agent", "")
        self.referer = request.headers.get("referer", "")

        # Security flags
        self.is_https = request.url.scheme == "https"
        self.has_auth = "authorization" in request.headers
        self.has_api_key = "x-api-key" in request.headers  # pragma: allowlist secret

    def _get_client_ip(self) -> str:
        """Get client IP address, handling proxy headers."""
        # Check for proxy headers (only in production with trusted proxies)
        settings = get_settings()

        if settings.deployment_profile == DeploymentProfile.PRODUCTION:
            # Trust proxy headers in production (behind load balancer)
            forwarded_for = self.request.headers.get("x-forwarded-for")
            if forwarded_for:
                # Get first IP in chain (original client)
                return forwarded_for.split(",")[0].strip()

            real_ip = self.request.headers.get("x-real-ip")
            if real_ip:
                return real_ip.strip()

        # Direct connection or development/home lab
        return self.request.client.host if self.request.client else "unknown"

    def is_secure_request(self) -> bool:
        """Check if request meets security requirements."""
        settings = get_settings()

        # HTTPS requirement check
        if settings.security.require_https and not self.is_https:
            return False

        # Authentication requirement check (future)
        # if settings.security.api_key_required and not (self.has_auth or self.has_api_key):
        #     return False

        return True

    def get_security_info(self) -> dict[str, Any]:
        """Get security information for logging/audit."""
        return {
            "client_ip": self.client_ip,
            "user_agent": self.user_agent,
            "referer": self.referer,
            "is_https": self.is_https,
            "has_auth": self.has_auth,
            "has_api_key": self.has_api_key,
            "is_secure": self.is_secure_request(),
        }


# =============================================================================
# Utility Functions
# =============================================================================


def get_security_headers_for_profile(profile: DeploymentProfile) -> dict[str, str]:
    """Get security headers dictionary for a specific deployment profile."""

    headers: dict[str, str] = {
        # Common headers
        "Server": "Harbor",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": (
            "geolocation=(), camera=(), microphone=(), "
            "payment=(), usb=(), magnetometer=(), "
            "accelerometer=(), gyroscope=()"
        ),
    }

    # Profile-specific additions
    if profile == DeploymentProfile.HOMELAB:
        headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "connect-src 'self' ws: wss:"
        )
    elif profile == DeploymentProfile.DEVELOPMENT:
        headers["Content-Security-Policy"] = (
            "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "connect-src 'self' ws: wss: http: https:"
        )
        headers["X-Harbor-Environment"] = "development"
    elif profile == DeploymentProfile.PRODUCTION:
        headers.update(
            {
                "Content-Security-Policy": (
                    "default-src 'self'; "
                    "script-src 'self' 'strict-dynamic'; "
                    "style-src 'self'; "
                    "object-src 'none'"
                ),
                "Strict-Transport-Security": (
                    "max-age=31536000; includeSubDomains; preload"
                ),
                "Cross-Origin-Embedder-Policy": "require-corp",
                "Cross-Origin-Opener-Policy": "same-origin",
                "Cross-Origin-Resource-Policy": "same-site",
            }
        )
    elif profile == DeploymentProfile.STAGING:
        headers.update(
            {
                "Content-Security-Policy": (
                    "default-src 'self'; "
                    "script-src 'self' 'unsafe-inline'; "
                    "style-src 'self' 'unsafe-inline'"
                ),
                "Strict-Transport-Security": "max-age=86400; includeSubDomains",
                "X-Harbor-Environment": "staging",
            }
        )

    return headers


if __name__ == "__main__":
    """Security headers testing and utilities"""

    print("🔒 Harbor Security Headers Middleware")
    print("=" * 40)

    # Test headers for different profiles
    for profile in DeploymentProfile:
        print(f"\n{profile.value.title()} Profile Headers:")
        headers = get_security_headers_for_profile(profile)

        for name, value in headers.items():
            print(f"  {name}: {value}")
