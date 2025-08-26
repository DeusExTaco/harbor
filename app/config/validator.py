"""
Harbor Configuration Validator

This module provides utilities for validating Harbor configuration,
including profile-specific validation, YAML loading, and environment
variable handling.

Author: Harbor Team
License: MIT
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from app.config.base import (
    DeploymentProfile,
    HarborConfig,
    load_config,
)
from app.config.feature_flags import get_enabled_features, get_feature_flags


logger = logging.getLogger(__name__)


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

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If YAML is invalid
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


def merge_yaml_config_to_env(config_data: dict[str, Any], prefix: str = "HARBOR"):
    """
    Merge YAML configuration into environment variables.

    Args:
        config_data: Configuration dictionary from YAML
        prefix: Environment variable prefix
    """

    def set_env_var(key_path: list[str], value: Any):
        """Recursively set environment variables from nested dict."""
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                set_env_var(key_path + [sub_key], sub_value)
        elif isinstance(value, list):
            # Convert list to comma-separated string
            env_key = f"{prefix}_" + "_".join(k.upper() for k in key_path)
            env_value = ",".join(str(v) for v in value)
            if env_key not in os.environ:
                os.environ[env_key] = env_value
        else:
            # Set scalar value
            env_key = f"{prefix}_" + "_".join(k.upper() for k in key_path)
            if env_key not in os.environ:
                os.environ[env_key] = str(value)

    for key, value in config_data.items():
        set_env_var([key], value)


# =============================================================================
# Validation Functions
# =============================================================================


def validate_profile_config(
    profile: DeploymentProfile, config: HarborConfig | None = None
) -> tuple[bool, list[str], list[str]]:
    """
    Validate configuration for a specific deployment profile.
    """
    warnings: list[str] = []
    errors: list[str] = []

    # Load config if not provided
    if config is None:
        try:
            os.environ["HARBOR_MODE"] = profile.value
            config = load_config(validate=False)
        except ValidationError as e:
            errors.append(f"Failed to load configuration: {e}")
            return False, warnings, errors

    # Profile-specific validation
    if profile == DeploymentProfile.PRODUCTION:
        # Production must have proper security
        if not config.security.require_https:
            errors.append("HTTPS is required for production deployment")

        if config.security.session_timeout_hours > 24:
            warnings.append(
                f"Session timeout ({config.security.session_timeout_hours}h) is long for production"
            )

        if config.security.password_min_length < 8:
            errors.append("Password minimum length must be at least 8 for production")

        if not config.security.secret_key and not config.security.secret_key_file:
            errors.append("Secret key must be configured for production")

        # Database recommendations
        if config.database.type == "sqlite":
            warnings.append("PostgreSQL is recommended for production deployments")

        # Resource checks
        if config.resources.max_memory_usage_mb < 512:
            warnings.append(
                f"Memory limit ({config.resources.max_memory_usage_mb}MB) may be insufficient for production"
            )

    elif profile == DeploymentProfile.HOMELAB:
        # Home lab recommendations
        if config.security.require_https:
            warnings.append("HTTPS is not required for home lab deployments")

        if config.database.type != "sqlite":
            warnings.append("SQLite is recommended for home lab simplicity")

        if config.updates.max_concurrent_updates > 5:
            warnings.append(
                f"High concurrent updates ({config.updates.max_concurrent_updates}) may overload home hardware"
            )

    elif profile == DeploymentProfile.DEVELOPMENT:
        # Development warnings
        if not config.debug:
            warnings.append("Debug mode should be enabled for development")

        if config.security.require_https:
            warnings.append("HTTPS is usually not needed for development")

    # Common validation
    if config.updates.default_check_interval_seconds < 300:
        warnings.append(
            f"Update check interval ({config.updates.default_check_interval_seconds}s) is very frequent"
        )

    if config.logging.retention_days > 90:
        warnings.append(
            f"Log retention ({config.logging.retention_days} days) will use significant disk space"
        )

    # Docker socket validation
    if config.docker.host.startswith("unix://"):
        socket_path = config.docker.host[7:]  # Remove unix:// prefix
        if not Path(socket_path).exists():
            errors.append(f"Docker socket not found: {socket_path}")

    is_valid = len(errors) == 0
    return is_valid, warnings, errors


def validate_environment() -> dict[str, Any]:
    """
    Validate the current environment configuration.
    """
    result: dict[str, Any] = {
        "environment": {},
        "missing_required": [],
        "using_defaults": [],
        "profile": None,
    }

    # Check deployment profile
    profile_str = os.getenv("HARBOR_MODE", "homelab")
    try:
        profile = DeploymentProfile(profile_str)
        result["profile"] = profile.value
    except ValueError:
        result["missing_required"].append(f"Invalid HARBOR_MODE: {profile_str}")

    # Check for important environment variables
    important_vars = [
        ("HARBOR_SECRET_KEY", "Security secret key"),
        ("DATABASE_URL", "Database connection URL"),
        ("DOCKER_HOST", "Docker daemon connection"),
    ]

    for var_name, description in important_vars:
        value = os.getenv(var_name)
        if value:
            # Mask sensitive values
            if "SECRET" in var_name or "PASSWORD" in var_name:
                result["environment"][var_name] = "***REDACTED***"
            else:
                result["environment"][var_name] = (
                    value[:50] + "..." if len(value) > 50 else value
                )
        else:
            result["using_defaults"].append(f"{var_name} ({description})")

    # Check Harbor-specific variables
    harbor_vars = {k: v for k, v in os.environ.items() if k.startswith("HARBOR_")}
    for key, value in harbor_vars.items():
        if key not in result["environment"]:
            if "SECRET" in key or "PASSWORD" in key:
                result["environment"][key] = "***REDACTED***"
            else:
                result["environment"][key] = (
                    value[:50] + "..." if len(value) > 50 else value
                )

    return result


def check_system_requirements() -> dict[str, Any]:
    """
    Check system requirements for Harbor.

    Returns:
        Dictionary with system check results
    """
    import platform
    import shutil

    result = {
        "python_version": platform.python_version(),
        "python_version_ok": False,
        "platform": platform.platform(),
        "docker_available": False,
        "disk_space_gb": 0,
        "disk_space_ok": False,
        "checks_passed": False,
    }

    # Check Python version (3.11+)
    major, minor = sys.version_info[:2]
    result["python_version_ok"] = major == 3 and minor >= 11

    # Check Docker availability
    result["docker_available"] = shutil.which("docker") is not None

    # Check disk space
    try:
        import psutil

        disk_usage = psutil.disk_usage("/")
        disk_space_gb = disk_usage.free / (1024**3)
        result["disk_space_gb"] = disk_space_gb
        result["disk_space_ok"] = disk_space_gb > 1.0  # At least 1GB free
    except ImportError:
        # psutil not available, skip disk check
        result["disk_space_ok"] = True

    result["checks_passed"] = (
        result["python_version_ok"]
        and result["docker_available"]
        and result["disk_space_ok"]
    )

    return result


# =============================================================================
# CLI Interface
# =============================================================================


def print_validation_results(
    profile: DeploymentProfile,
    is_valid: bool,
    warnings: list[str],
    errors: list[str],
    verbose: bool = False,
):
    """Print validation results in a formatted way."""
    print(f"\n🔍 Configuration Validation Results for {profile.value.upper()} Profile")
    print("=" * 60)

    if is_valid:
        print("✅ Configuration is VALID")
    else:
        print("❌ Configuration is INVALID")

    if errors:
        print(f"\n🚫 Errors ({len(errors)}):")
        for error in errors:
            print(f"   ❌ {error}")

    if warnings:
        print(f"\n⚠️  Warnings ({len(warnings)}):")
        for warning in warnings:
            print(f"   ⚠️  {warning}")

    if not errors and not warnings:
        print("\n✨ No issues found!")

    if verbose:
        # Show feature flags
        flags = get_feature_flags(profile)
        enabled_features = get_enabled_features(flags)

        print("\n🎯 Enabled Features:")
        for category, features in enabled_features.items():
            if features:
                print(f"   {category}:")
                for feature, enabled in features.items():
                    if enabled:
                        print(f"      ✓ {feature}")


def validate_config_file(
    config_path: Path, profile: DeploymentProfile | None = None
) -> bool:
    """
    Validate a configuration file.

    Args:
        config_path: Path to configuration file
        profile: Override profile (uses file's profile if None)

    Returns:
        bool: True if valid
    """
    print(f"\n📄 Validating configuration file: {config_path}")

    try:
        # Load YAML configuration
        config_data = load_yaml_config(config_path)

        # Get profile from file or argument
        if profile is None:
            profile_str = config_data.get("deployment", {}).get("profile", "homelab")
            try:
                profile = DeploymentProfile(profile_str)
            except ValueError:
                print(f"❌ Invalid profile in config: {profile_str}")
                return False

        # Merge config to environment
        merge_yaml_config_to_env(config_data)

        # Validate configuration
        is_valid, warnings, errors = validate_profile_config(profile)

        # Print results
        print_validation_results(profile, is_valid, warnings, errors, verbose=True)

        return is_valid

    except Exception as e:
        print(f"❌ Failed to validate config file: {e}")
        return False


def main():
    """CLI entry point for configuration validation."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Harbor Configuration Validator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate current environment configuration
  python -m app.config.validator

  # Validate specific profile
  python -m app.config.validator --profile production

  # Validate configuration file
  python -m app.config.validator --file config/homelab.yaml

  # Check system requirements
  python -m app.config.validator --check-system

  # Export configuration template
  python -m app.config.validator --export production > .env.production
        """,
    )

    parser.add_argument(
        "--profile",
        "-p",
        type=str,
        choices=["homelab", "development", "staging", "production"],
        help="Deployment profile to validate",
    )

    parser.add_argument(
        "--file", "-f", type=Path, help="Configuration file to validate"
    )

    parser.add_argument(
        "--check-system", action="store_true", help="Check system requirements"
    )

    parser.add_argument(
        "--check-env", action="store_true", help="Check environment variables"
    )

    parser.add_argument(
        "--export",
        type=str,
        choices=["homelab", "development", "staging", "production"],
        help="Export configuration template for profile",
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Export template if requested
    if args.export:
        from app.config import export_config_template

        profile = DeploymentProfile(args.export)
        template = export_config_template(profile)
        print(template)
        return

    # Check system requirements
    if args.check_system:
        print("\n🖥️  System Requirements Check")
        print("=" * 60)

        requirements = check_system_requirements()

        status = "✅" if requirements["python_version_ok"] else "❌"
        print(
            f"{status} Python version: {requirements['python_version']} (3.11+ required)"
        )

        status = "✅" if requirements["docker_available"] else "❌"
        print(
            f"{status} Docker: {'Available' if requirements['docker_available'] else 'Not found'}"
        )

        if "disk_space_gb" in requirements:
            status = "✅" if requirements["disk_space_ok"] else "❌"
            print(f"{status} Disk space: {requirements['disk_space_gb']:.1f} GB free")

        print(f"\nPlatform: {requirements['platform']}")

        if requirements["checks_passed"]:
            print("\n✅ All system requirements met!")
        else:
            print("\n❌ Some requirements not met")
        return

    # Check environment variables
    if args.check_env:
        print("\n🔧 Environment Configuration")
        print("=" * 60)

        env_info = validate_environment()

        print(f"Profile: {env_info['profile'] or 'Not set (defaulting to homelab)'}")

        if env_info["environment"]:
            print("\nConfigured variables:")
            for key, value in sorted(env_info["environment"].items()):
                print(f"  {key}: {value}")

        if env_info["using_defaults"]:
            print("\nUsing defaults for:")
            for item in env_info["using_defaults"]:
                print(f"  - {item}")

        if env_info["missing_required"]:
            print("\n❌ Missing required:")
            for item in env_info["missing_required"]:
                print(f"  - {item}")

        return

    # Validate configuration file
    if args.file:
        success = validate_config_file(
            args.file, DeploymentProfile(args.profile) if args.profile else None
        )
        sys.exit(0 if success else 1)

    # Validate current configuration
    profile = DeploymentProfile(args.profile) if args.profile else None

    if profile:
        os.environ["HARBOR_MODE"] = profile.value
    else:
        # Get profile from environment
        profile_str = os.getenv("HARBOR_MODE", "homelab")
        try:
            profile = DeploymentProfile(profile_str)
        except ValueError:
            print(f"❌ Invalid HARBOR_MODE: {profile_str}")
            sys.exit(1)

    # Validate
    is_valid, warnings, errors = validate_profile_config(profile)
    print_validation_results(profile, is_valid, warnings, errors, args.verbose)

    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
