# app/core/security.py
"""
Harbor Core Security Configuration

Central security configuration and utilities for the Harbor application.
Provides unified security settings across all components.

Implementation: M0 Milestone - Foundation Phase
"""

from typing import Any

from app.config import DeploymentProfile, get_settings
from app.utils.logging import get_logger


logger = get_logger(__name__)


class SecurityConfig:
    """Central security configuration management."""

    @classmethod
    def get_security_config(cls) -> dict[str, Any]:
        """
        Get comprehensive security configuration based on deployment profile.

        Returns:
            Dictionary with all security settings
        """
        settings = get_settings()
        profile = settings.deployment_profile

        return {
            "authentication": {
                "enabled": True,
                "session_enabled": True,
                "api_key_enabled": True,
                "require_auth": settings.security.api_key_required,
                "session_timeout": settings.security.session_timeout_hours * 3600,
                "password_min_length": settings.security.password_min_length,
                "password_require_special": settings.security.password_require_special,
            },
            "rate_limiting": {
                "enabled": cls._should_enable_rate_limiting(profile),
                "ip_limit": settings.security.api_rate_limit_per_hour // 5,
                "api_key_limit": settings.security.api_rate_limit_per_hour,
                "burst_limit": 20 if profile == DeploymentProfile.HOMELAB else 50,
            },
            "cors": {
                "enabled": True,
                "origins": cls._get_cors_origins(profile),
                "allow_credentials": True,
                "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                "allow_headers": ["*"],
            },
            "audit": {
                "enabled": profile != DeploymentProfile.DEVELOPMENT,
                "log_requests": True,
                "log_auth_events": True,
                "retention_days": 7 if profile == DeploymentProfile.HOMELAB else 90,
            },
            "https": {
                "required": settings.security.require_https,
                "hsts_enabled": profile == DeploymentProfile.PRODUCTION,
            },
        }

    @staticmethod
    def _should_enable_rate_limiting(profile: DeploymentProfile) -> bool:
        """Determine if rate limiting should be enabled."""
        # Always enable except optionally in development
        return True  # Can be made configurable via environment variable

    @staticmethod
    def _get_cors_origins(profile: DeploymentProfile) -> list[str]:
        """Get CORS allowed origins for profile."""
        if profile == DeploymentProfile.DEVELOPMENT:
            return ["*"]
        elif profile == DeploymentProfile.HOMELAB:
            return [
                "http://localhost:*",
                "http://127.0.0.1:*",
                "http://192.168.*",
                "http://10.*",
                "http://172.16.*",
                "http://172.17.*",
                "http://172.18.*",
                "http://172.19.*",
                "http://172.20.*",
                "http://172.21.*",
                "http://172.22.*",
                "http://172.23.*",
                "http://172.24.*",
                "http://172.25.*",
                "http://172.26.*",
                "http://172.27.*",
                "http://172.28.*",
                "http://172.29.*",
                "http://172.30.*",
                "http://172.31.*",
            ]
        else:  # Production/Staging
            settings = get_settings()
            return getattr(settings, "cors_origins", ["https://harbor.local"])

    @classmethod
    def get_public_paths(cls) -> list[str]:
        """Get list of paths that don't require authentication."""
        return [
            "/",
            "/healthz",
            "/readyz",
            "/version",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/logout",
            "/static/",
            "/security/status",
            "/database/status",  # For health monitoring
            "/database/health",  # For health monitoring
        ]
