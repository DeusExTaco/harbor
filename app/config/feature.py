"""
Harbor Feature Flags System

This module provides feature flag management that integrates with the
existing factory-pattern configuration system.

Author: Harbor Team
License: MIT
"""

import os
from dataclasses import dataclass
from typing import Any

from app.config import DeploymentProfile, get_settings
from app.utils.logging import get_logger


logger = get_logger(__name__)


# =============================================================================
# Feature Flag Categories (v1.0 Focused)
# =============================================================================


@dataclass
class CoreFeatures:
    """Core v1.0 features (M0-M6) - Always enabled"""

    configuration_system: bool = True  # M0 - Complete
    security_middleware: bool = True  # M0 - Complete
    database_system: bool = True  # M0 - Complete
    authentication: bool = True  # M0 - In Progress
    container_discovery: bool = True  # M1
    registry_integration: bool = True  # M1
    update_engine: bool = True  # M2
    rollback_support: bool = True  # M2
    scheduling: bool = True  # M3
    web_interface: bool = True  # M3
    monitoring: bool = True  # M4
    metrics: bool = True  # M4
    production_hardening: bool = True  # M5
    documentation: bool = True  # M6


@dataclass
class FutureFeatures:
    """Future features (v1.1+) - Behind feature flags"""

    # M7+ Authentication Enhancements
    mfa_support: bool = False  # TODO: M7+ Multi-factor authentication
    oauth_integration: bool = False  # TODO: M7+ OAuth providers
    ldap_support: bool = False  # TODO: M9+ LDAP integration
    saml_support: bool = False  # TODO: M9+ SAML SSO

    # M8+ Multi-User & RBAC
    multi_user: bool = False  # TODO: M8+ Multiple users
    rbac: bool = False  # TODO: M8+ Role-based access
    api_key_scoping: bool = False  # TODO: M8+ Scoped API keys
    team_management: bool = False  # TODO: M8+ Team features

    # M8+ Update Strategies
    blue_green_deployment: bool = False  # TODO: M8+ Blue/green updates
    canary_deployment: bool = False  # TODO: M8+ Canary updates
    batch_updates: bool = False  # TODO: M8+ Batch processing
    dependency_ordering: bool = False  # TODO: M9+ Dependency-aware updates

    # M9+ Runtime Support
    kubernetes_runtime: bool = False  # TODO: M9+ Kubernetes support
    podman_runtime: bool = False  # TODO: M10+ Podman support
    docker_swarm: bool = False  # TODO: M11+ Docker Swarm

    # M7+ Integrations
    slack_notifications: bool = False  # TODO: M7+ Slack integration
    email_notifications: bool = False  # TODO: M7+ Email notifications
    teams_integration: bool = False  # TODO: M7+ Microsoft Teams
    discord_integration: bool = False  # TODO: M7+ Discord

    # M9+ Enterprise Features
    high_availability: bool = False  # TODO: M9+ HA deployment
    clustering: bool = False  # TODO: M9+ Multi-instance
    data_encryption: bool = False  # TODO: M9+ Database encryption
    compliance_reporting: bool = False  # TODO: M10+ Compliance


# =============================================================================
# Feature Flag Container
# =============================================================================


@dataclass
class HarborFeatureFlags:
    """Complete feature flag configuration"""

    core: CoreFeatures
    future: FutureFeatures
    profile: DeploymentProfile

    def is_enabled(self, feature_path: str) -> bool:
        """
        Check if a feature is enabled using dot notation.

        Args:
            feature_path: Dot-separated path like "future.mfa_support"

        Returns:
            bool: True if feature is enabled
        """
        try:
            parts = feature_path.split(".")
            if len(parts) != 2:
                return False

            category = parts[0]
            feature = parts[1]

            if category == "core":
                return getattr(self.core, feature, False)
            elif category == "future":
                return getattr(self.future, feature, False)
            else:
                return False

        except AttributeError:
            logger.warning(f"Unknown feature flag: {feature_path}")
            return False

    def get_enabled_features(self) -> dict[str, dict[str, bool]]:
        """Get all enabled features organized by category."""
        return {
            "core": {
                field: getattr(self.core, field)
                for field in self.core.__dataclass_fields__
                if getattr(self.core, field)
            },
            "future": {
                field: getattr(self.future, field)
                for field in self.future.__dataclass_fields__
                if getattr(self.future, field)
            },
        }


# =============================================================================
# Profile-Based Feature Configuration
# =============================================================================


def get_feature_flags(profile: DeploymentProfile | None = None) -> HarborFeatureFlags:
    """
    Get feature flags for the specified profile.

    Args:
        profile: Deployment profile (uses current if None)

    Returns:
        HarborFeatureFlags instance
    """
    if profile is None:
        settings = get_settings()
        profile = settings.deployment_profile

    # Core features are always enabled
    core = CoreFeatures()

    # Future features depend on profile and environment
    future = FutureFeatures()

    # Development profile can enable some future features for testing
    if profile == DeploymentProfile.DEVELOPMENT:
        # Enable features for development testing
        future.mfa_support = os.getenv("HARBOR_ENABLE_MFA", "false").lower() == "true"
        future.multi_user = (
            os.getenv("HARBOR_ENABLE_MULTI_USER", "false").lower() == "true"
        )
        future.blue_green_deployment = (
            os.getenv("HARBOR_ENABLE_BLUE_GREEN", "false").lower() == "true"
        )
        future.slack_notifications = (
            os.getenv("HARBOR_ENABLE_SLACK", "false").lower() == "true"
        )

    # Staging can enable more features
    elif profile == DeploymentProfile.STAGING:
        future.mfa_support = os.getenv("HARBOR_ENABLE_MFA", "false").lower() == "true"
        future.multi_user = (
            os.getenv("HARBOR_ENABLE_MULTI_USER", "false").lower() == "true"
        )
        future.rbac = os.getenv("HARBOR_ENABLE_RBAC", "false").lower() == "true"
        future.blue_green_deployment = (
            os.getenv("HARBOR_ENABLE_BLUE_GREEN", "false").lower() == "true"
        )
        future.slack_notifications = (
            os.getenv("HARBOR_ENABLE_SLACK", "false").lower() == "true"
        )
        future.email_notifications = (
            os.getenv("HARBOR_ENABLE_EMAIL", "false").lower() == "true"
        )

    # Production only enables stable, tested features
    elif profile == DeploymentProfile.PRODUCTION:
        # Only enable future features that are explicitly enabled and tested
        future.email_notifications = (
            os.getenv("HARBOR_ENABLE_EMAIL", "false").lower() == "true"
        )

    return HarborFeatureFlags(core=core, future=future, profile=profile)


# =============================================================================
# Feature Flag Utilities
# =============================================================================


def require_feature(feature_path: str):
    """
    Decorator to enforce feature flag requirements.

    Args:
        feature_path: Dot-separated feature path (e.g., "future.mfa_support")

    Example:
        @require_feature("future.mfa_support")
        def setup_mfa():
            # Only runs if MFA is enabled
            pass
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            flags = get_feature_flags()
            if not flags.is_enabled(feature_path):
                raise NotImplementedError(
                    f"Feature '{feature_path}' is not enabled in {flags.profile.value} profile. "
                    f"This feature is planned for a future release."
                )
            return func(*args, **kwargs)

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator


def get_milestone_status() -> dict[str, Any]:
    """
    Get current milestone implementation status.

    Returns:
        Dictionary with milestone progress
    """
    flags = get_feature_flags()

    return {
        "current_milestone": "M0",
        "milestone_name": "Foundation",
        "progress": {
            "M0_Foundation": {
                "status": "in_progress",
                "completed": [
                    "configuration_system",
                    "security_middleware",
                    "database_system",
                ],
                "in_progress": [
                    "authentication",
                ],
                "pending": [
                    "api_endpoints",
                    "template_system",
                ],
            },
            "M1_Discovery": {
                "status": "pending",
                "features": [
                    "container_discovery",
                    "registry_integration",
                ],
            },
            "M2_UpdateEngine": {
                "status": "pending",
                "features": [
                    "update_engine",
                    "rollback_support",
                ],
            },
            "M3_Automation": {
                "status": "pending",
                "features": [
                    "scheduling",
                    "web_interface",
                ],
            },
            "M4_Observability": {
                "status": "pending",
                "features": [
                    "monitoring",
                    "metrics",
                ],
            },
            "M5_Production": {
                "status": "pending",
                "features": [
                    "production_hardening",
                ],
            },
            "M6_Release": {
                "status": "pending",
                "features": [
                    "documentation",
                    "community_launch",
                ],
            },
        },
        "future_features": {
            "enabled": [
                feature for feature, enabled in flags.future.__dict__.items() if enabled
            ],
            "total_future_features": len(flags.future.__dataclass_fields__),
        },
    }


def validate_feature_compatibility(profile: DeploymentProfile) -> dict[str, Any]:
    """
    Validate feature compatibility for a deployment profile.

    Args:
        profile: Deployment profile to validate

    Returns:
        Dictionary with compatibility information
    """
    flags = get_feature_flags(profile)
    settings = get_settings()

    issues = []
    warnings = []

    # Check future features in production
    if profile == DeploymentProfile.PRODUCTION:
        if any(
            [
                flags.future.mfa_support,
                flags.future.multi_user,
                flags.future.blue_green_deployment,
            ]
        ):
            warnings.append(
                "Future features enabled in production - ensure they are thoroughly tested"
            )

    # Check resource requirements for features
    if flags.future.clustering and settings.updates.max_concurrent_updates < 5:
        warnings.append("Clustering enabled but max_concurrent_updates is low")

    # Check database compatibility
    if (
        flags.future.high_availability
        and settings.database.database_type.value == "sqlite"
    ):
        issues.append("High availability requires PostgreSQL, not SQLite")

    return {
        "profile": profile.value,
        "compatible": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "feature_summary": {
            "core_features": sum(
                1 for f in flags.core.__dataclass_fields__ if getattr(flags.core, f)
            ),
            "future_features_enabled": sum(
                1 for f in flags.future.__dataclass_fields__ if getattr(flags.future, f)
            ),
        },
    }


# =============================================================================
# Feature Flag Status Report
# =============================================================================


def get_feature_report() -> str:
    """
    Generate a human-readable feature flag report.

    Returns:
        String with formatted feature report
    """
    flags = get_feature_flags()
    settings = get_settings()

    lines = [
        "Harbor Feature Flag Report",
        f"Profile: {flags.profile.value}",
        f"Version: {settings.app_version}",
        "",
        "Core Features (v1.0):",
    ]

    for field in flags.core.__dataclass_fields__:
        status = "✅" if getattr(flags.core, field) else "❌"
        lines.append(f"  {status} {field}")

    lines.extend(
        [
            "",
            "Future Features (v1.1+):",
        ]
    )

    for field in flags.future.__dataclass_fields__:
        enabled = getattr(flags.future, field)
        if enabled:
            lines.append(f"  ✅ {field} [ENABLED FOR TESTING]")
        else:
            # Add TODO milestone info
            if "mfa" in field or "oauth" in field:
                lines.append(f"  ⏳ {field} (TODO: M7+)")
            elif "multi_user" in field or "rbac" in field:
                lines.append(f"  ⏳ {field} (TODO: M8+)")
            elif "kubernetes" in field:
                lines.append(f"  ⏳ {field} (TODO: M9+)")
            else:
                lines.append(f"  ⏳ {field} (TODO: Future)")

    return "\n".join(lines)
