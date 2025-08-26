"""
Harbor Enhanced Configuration Extensions

This module extends the existing configuration system with additional
functionality while maintaining compatibility with the factory pattern
approach in app/config.py.

Author: Harbor Team
License: MIT
"""

import os
from pathlib import Path
from typing import Any

import yaml

from app.config import (
    DeploymentProfile,
    HarborSettings,
    create_harbor_settings,
    get_settings,
)
from app.utils.logging import get_logger


logger = get_logger(__name__)


# =============================================================================
# Configuration File Loading
# =============================================================================


def load_yaml_config(config_path: Path) -> dict[str, Any]:
    """
    Load configuration from a YAML file.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        Dictionary containing configuration data
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with open(config_path) as f:
            config_data = yaml.safe_load(f)

        if not isinstance(config_data, dict):
            raise ValueError(f"Invalid configuration format in {config_path}")

        return config_data

    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {config_path}: {e}")


def apply_yaml_config(config_path: Path) -> HarborSettings:
    """
    Apply configuration from a YAML file to environment and create settings.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        HarborSettings with YAML configuration applied
    """
    config_data = load_yaml_config(config_path)

    # Flatten nested configuration to environment variables
    def set_env_from_dict(data: dict[str, Any], prefix: str = "HARBOR"):
        for key, value in data.items():
            if isinstance(value, dict):
                set_env_from_dict(value, f"{prefix}_{key.upper()}")
            elif isinstance(value, list):
                env_key = f"{prefix}_{key.upper()}"
                os.environ[env_key] = ",".join(str(v) for v in value)
            else:
                env_key = f"{prefix}_{key.upper()}"
                os.environ[env_key] = str(value)

    # Apply configuration to environment
    set_env_from_dict(config_data)

    # Create settings with new environment
    return create_harbor_settings()


# =============================================================================
# Configuration Validation Extensions
# =============================================================================


def validate_harbor_config(settings: HarborSettings | None = None) -> dict[str, Any]:
    """
    Extended validation for Harbor configuration.

    Args:
        settings: Settings to validate (uses current if None)

    Returns:
        Dictionary with validation results
    """
    if settings is None:
        settings = get_settings()

    result: dict[str, Any] = {
        "valid": True,
        "warnings": [],  # This is already a list
        "errors": [],  # This is already a list
        "profile": settings.deployment_profile.value,
    }

    # Profile-specific validation
    if settings.deployment_profile == DeploymentProfile.PRODUCTION:
        # Production requirements
        if not settings.security.require_https:
            result["errors"].append("HTTPS must be enabled for production")
            result["valid"] = False

        if settings.security.session_timeout_hours > 24:
            result["warnings"].append(
                f"Session timeout ({settings.security.session_timeout_hours}h) is long for production"
            )

        if settings.security.password_min_length < 12:
            result["warnings"].append(
                f"Password minimum length ({settings.security.password_min_length}) should be at least 12 for production"
            )

        if settings.database.database_type.value == "sqlite":
            result["warnings"].append("PostgreSQL is recommended for production")

    elif settings.deployment_profile == DeploymentProfile.HOMELAB:
        # Home lab recommendations
        if settings.updates.max_concurrent_updates > 5:
            result["warnings"].append(
                f"High concurrent updates ({settings.updates.max_concurrent_updates}) may overload home hardware"
            )

        if settings.security.api_key_required:
            result["warnings"].append("API key may not be necessary for home lab use")

    # Common validation
    if settings.updates.default_check_interval_seconds < 300:
        result["warnings"].append(
            f"Update check interval ({settings.updates.default_check_interval_seconds}s) is very frequent"
        )

    # Docker socket validation
    docker_host = os.getenv("DOCKER_HOST", "unix:///var/run/docker.sock")
    if docker_host.startswith("unix://"):
        socket_path = docker_host[7:]
        if not Path(socket_path).exists():
            result["errors"].append(f"Docker socket not found: {socket_path}")
            result["valid"] = False

    return result


# =============================================================================
# Configuration Export
# =============================================================================


def export_config_template(
    profile: DeploymentProfile = DeploymentProfile.HOMELAB,
) -> str:
    """
    Export a configuration template for the specified profile.

    Args:
        profile: Deployment profile to export

    Returns:
        String containing environment variable template
    """
    # Set the profile and create settings
    os.environ["HARBOR_MODE"] = profile.value
    settings = create_harbor_settings()

    lines = [
        f"# Harbor Configuration Template - {profile.value.upper()} Profile",
        "# Generated by Harbor configuration system",
        "",
        f"HARBOR_MODE={profile.value}",
        f"HARBOR_DEBUG={str(settings.debug).lower()}",
        "",
        "# Security Configuration",
        f"HARBOR_SECURITY_REQUIRE_HTTPS={str(settings.security.require_https).lower()}",
        f"HARBOR_SECURITY_SESSION_TIMEOUT_HOURS={settings.security.session_timeout_hours}",
        f"HARBOR_SECURITY_API_KEY_REQUIRED={str(settings.security.api_key_required).lower()}",
        f"HARBOR_SECURITY_PASSWORD_MIN_LENGTH={settings.security.password_min_length}",
        f"HARBOR_SECURITY_PASSWORD_REQUIRE_SPECIAL={str(settings.security.password_require_special).lower()}",
        "",
        "# Database Configuration",
        f"HARBOR_DATABASE_TYPE={settings.database.database_type.value}",
        f"HARBOR_DB_POOL_SIZE={settings.database.pool_size}",
        f"HARBOR_DB_MAX_OVERFLOW={settings.database.max_overflow}",
        f"HARBOR_DB_POOL_TIMEOUT={settings.database.pool_timeout}",
        "",
        "# Update Configuration",
        f"HARBOR_UPDATE_DEFAULT_CHECK_INTERVAL_SECONDS={settings.updates.default_check_interval_seconds}",
        f"HARBOR_UPDATE_DEFAULT_UPDATE_TIME={settings.updates.default_update_time}",
        f"HARBOR_UPDATE_MAX_CONCURRENT_UPDATES={settings.updates.max_concurrent_updates}",
        f"HARBOR_UPDATE_DEFAULT_CLEANUP_KEEP_IMAGES={settings.updates.default_cleanup_keep_images}",
        "",
        "# Logging Configuration",
        f"HARBOR_LOG_LOG_LEVEL={settings.logging.log_level.value}",
        f"HARBOR_LOG_FORMAT={settings.logging.log_format}",
        f"HARBOR_LOG_RETENTION_DAYS={settings.logging.log_retention_days}",
        "",
        "# Feature Flags",
        f"HARBOR_FEATURE_ENABLE_AUTO_DISCOVERY={str(settings.features.enable_auto_discovery).lower()}",
        f"HARBOR_FEATURE_ENABLE_METRICS={str(settings.features.enable_metrics).lower()}",
        f"HARBOR_FEATURE_ENABLE_HEALTH_CHECKS={str(settings.features.enable_health_checks).lower()}",
        f"HARBOR_FEATURE_ENABLE_SIMPLE_MODE={str(settings.features.enable_simple_mode).lower()}",
        f"HARBOR_FEATURE_SHOW_GETTING_STARTED={str(settings.features.show_getting_started).lower()}",
    ]

    return "\n".join(lines)


# =============================================================================
# Configuration Summary
# =============================================================================


def get_extended_config_summary(
    settings: HarborSettings | None = None,
) -> dict[str, Any]:
    """
    Get extended configuration summary with validation.

    Args:
        settings: Settings to summarize (uses current if None)

    Returns:
        Dictionary with configuration summary and validation
    """
    if settings is None:
        settings = get_settings()

    # Get validation results
    validation = validate_harbor_config(settings)

    summary = {
        "profile": settings.deployment_profile.value,
        "version": settings.app_version,
        "debug": settings.debug,
        "data_dir": str(settings.data_dir),
        "database": {
            "type": settings.database.database_type.value,
            "url": settings.database.database_url
            if settings.database.database_url
            else "auto-generated",
            "pool_size": settings.database.pool_size,
        },
        "security": {
            "https_required": settings.security.require_https,
            "api_key_required": settings.security.api_key_required,
            "session_timeout": f"{settings.security.session_timeout_hours} hours",
            "password_min_length": settings.security.password_min_length,
        },
        "updates": {
            "check_interval": f"{settings.updates.default_check_interval_seconds} seconds",
            "update_time": settings.updates.default_update_time,
            "max_concurrent": settings.updates.max_concurrent_updates,
            "cleanup_keep_images": settings.updates.default_cleanup_keep_images,
        },
        "features": {
            "auto_discovery": settings.features.enable_auto_discovery,
            "metrics": settings.features.enable_metrics,
            "health_checks": settings.features.enable_health_checks,
            "simple_mode": settings.features.enable_simple_mode,
            "getting_started": settings.features.show_getting_started,
        },
        "validation": {
            "valid": validation["valid"],
            "warnings": len(validation["warnings"]),
            "errors": len(validation["errors"]),
            "issues": validation["warnings"] + validation["errors"],
        },
    }

    return summary


# =============================================================================
# Profile Detection
# =============================================================================


def suggest_deployment_profile() -> DeploymentProfile:
    """
    Suggest a deployment profile based on system characteristics.

    Returns:
        Suggested DeploymentProfile
    """

    # Check if in container
    is_container = os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv")

    # Check if in CI/CD
    is_ci = any(
        [
            os.getenv("CI"),
            os.getenv("GITHUB_ACTIONS"),
            os.getenv("GITLAB_CI"),
            os.getenv("JENKINS_HOME"),
        ]
    )

    # Check if in cloud
    is_cloud = any(
        [
            os.getenv("AWS_EXECUTION_ENV"),
            os.getenv("GOOGLE_CLOUD_PROJECT"),
            os.getenv("AZURE_FUNCTIONS_ENVIRONMENT"),
            os.getenv("KUBERNETES_SERVICE_HOST"),
        ]
    )

    # Check system resources
    cpu_count = os.cpu_count() or 1

    # Determine profile
    if is_cloud or os.getenv("PRODUCTION"):
        return DeploymentProfile.PRODUCTION
    elif is_ci:
        return DeploymentProfile.STAGING
    elif os.getenv("DEBUG") or os.getenv("FLASK_DEBUG"):
        return DeploymentProfile.DEVELOPMENT
    elif cpu_count <= 4 and not is_cloud:
        return DeploymentProfile.HOMELAB
    else:
        return DeploymentProfile.HOMELAB  # Default to home lab


# =============================================================================
# Environment Helpers
# =============================================================================


def get_required_env_vars(profile: DeploymentProfile) -> list[str]:
    """
    Get list of required environment variables for a profile.

    Args:
        profile: Deployment profile

    Returns:
        List of required environment variable names
    """
    required = []

    if profile == DeploymentProfile.PRODUCTION:
        required.extend(
            [
                "HARBOR_SECRET_KEY",
                "DATABASE_URL",  # PostgreSQL required for production
            ]
        )

    return required


def check_env_vars(profile: DeploymentProfile | None = None) -> dict[str, Any]:
    """
    Check if required environment variables are set.

    Args:
        profile: Deployment profile to check (uses current if None)

    Returns:
        Dictionary with check results
    """
    if profile is None:
        settings = get_settings()
        profile = settings.deployment_profile

    required = get_required_env_vars(profile)
    missing = []
    present = []

    for var in required:
        if os.getenv(var):
            present.append(var)
        else:
            missing.append(var)

    return {
        "profile": profile.value,
        "required": required,
        "present": present,
        "missing": missing,
        "all_set": len(missing) == 0,
    }
