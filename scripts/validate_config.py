#!/usr/bin/env python3
"""
Harbor Container Updater - Configuration Validator

Validates Harbor configuration files and environment settings.
Part of M0 milestone - Foundation phase.

Usage:
    python scripts/validate_config.py                    # Validate current config
    python scripts/validate_config.py --profile homelab  # Validate specific profile
    python scripts/validate_config.py --env-only         # Validate environment only
    python scripts/validate_config.py --export production # Export config template
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from app.config import (
        AppSettings,
        DeploymentProfile,
        detect_environment,
        export_config_template,
        get_config_summary,
        get_profile_recommendations,
        get_settings,
        reload_settings,
        validate_runtime_requirements,
    )
except ImportError as e:
    print(f"❌ Failed to import Harbor configuration: {e}")
    print("💡 Make sure you're running from the Harbor project root directory")
    sys.exit(1)


# =============================================================================
# Validation Functions
# =============================================================================


def validate_configuration(profile: str | None = None) -> dict[str, Any]:
    """
    Validate Harbor configuration for a specific profile.

    Args:
        profile: Optional deployment profile to validate

    Returns:
        Dict[str, Any]: Validation results
    """
    results: dict[str, Any] = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "info": [],
        "profile": profile or os.getenv("HARBOR_MODE", "homelab"),
    }

    try:
        # Set profile if specified
        if profile:
            os.environ["HARBOR_MODE"] = profile
            # Force reload settings with new profile
            reload_settings()

        # Load settings
        settings = get_settings()
        results["profile"] = settings.deployment_profile.value

        # Validate runtime requirements
        errors = validate_runtime_requirements()
        if errors:
            results["errors"].extend(errors)
            results["valid"] = False

        # Profile-specific validations
        profile_errors = _validate_profile_specific(settings)
        if profile_errors:
            results["errors"].extend(profile_errors)
            results["valid"] = False

        # Check for warnings
        warnings = _check_configuration_warnings(settings)
        results["warnings"].extend(warnings)

        # Add info messages
        info = _get_configuration_info(settings)
        results["info"].extend(info)

        # Add configuration summary
        results["config_summary"] = get_config_summary()

    except Exception as e:
        results["valid"] = False
        results["errors"].append(f"Configuration loading failed: {e}")

    return results


def _validate_profile_specific(settings: AppSettings) -> list[str]:
    """Validate profile-specific requirements"""
    errors: list[str] = []

    if settings.deployment_profile == DeploymentProfile.PRODUCTION:
        # Production requirements
        if not settings.security.require_https:
            errors.append("Production profile requires HTTPS")

        if settings.security.password_min_length < 8:
            errors.append("Production profile requires minimum 8 character passwords")

        if not settings.security.api_key_required:
            errors.append("Production profile requires API key authentication")

        if settings.database.database_type.value == "sqlite":
            errors.append("Production profile should use PostgreSQL, not SQLite")

    elif settings.deployment_profile == DeploymentProfile.HOMELAB:
        # Home lab recommendations (warnings, not errors)
        pass  # Home lab is very permissive

    return errors


def _check_configuration_warnings(settings: AppSettings) -> list[str]:
    """Check for configuration warnings"""
    warnings: list[str] = []

    # Security warnings
    if settings.deployment_profile != DeploymentProfile.DEVELOPMENT:
        if "dev" in settings.security.secret_key.lower():
            warnings.append("Secret key appears to be a development key")

        if len(settings.security.secret_key) < 32:
            warnings.append("Secret key is shorter than recommended 32 characters")

    # Performance warnings
    if settings.updates.max_concurrent_updates > 10:
        warnings.append("High concurrent updates may impact system performance")

    if settings.resources.max_memory_usage_mb > 4096:
        warnings.append("High memory limit - ensure sufficient system resources")

    # Home lab specific warnings
    if settings.deployment_profile == DeploymentProfile.HOMELAB:
        if settings.security.require_https:
            warnings.append("HTTPS enabled but may complicate home lab setup")

        if settings.updates.max_concurrent_updates > 3:
            warnings.append("High concurrent updates may overwhelm home lab hardware")

    return warnings


def _get_configuration_info(settings: AppSettings) -> list[str]:
    """Get informational messages about configuration"""
    info: list[str] = []

    # Profile information
    recommendations = get_profile_recommendations(settings.deployment_profile)
    info.append(f"Profile focus: {recommendations['deployment_focus']}")
    info.append(f"Security level: {recommendations['security_level']}")

    # Feature status
    enabled_features: list[str] = []
    if settings.features.enable_auto_discovery:
        enabled_features.append("auto-discovery")
    if settings.features.enable_metrics:
        enabled_features.append("metrics")
    if settings.features.show_getting_started:
        enabled_features.append("getting-started")

    if enabled_features:
        info.append(f"Enabled features: {', '.join(enabled_features)}")

    # Resource information
    info.append(f"Memory limit: {settings.resources.max_memory_usage_mb}MB")
    info.append(f"Max concurrent updates: {settings.updates.max_concurrent_updates}")
    info.append(f"Database: {settings.database.database_type.value}")

    return info


# =============================================================================
# Environment Detection
# =============================================================================


def detect_and_analyze_environment() -> dict[str, Any]:
    """Detect and analyze current environment"""
    try:
        env_info = detect_environment()

        analysis: dict[str, Any] = {
            "environment": env_info,
            "recommendations": [],
            "warnings": [],
        }

        # Analyze platform
        platform = env_info["platform"]
        if platform["machine"] in ["aarch64", "arm64"]:
            analysis["recommendations"].append(
                "Consider enabling ARM image preferences"
            )

        if "arm" in platform["machine"].lower():
            analysis["recommendations"].append(
                "Raspberry Pi detected - consider raspberry-pi optimizations"
            )

        # Analyze resources
        resources = env_info["resources"]
        if resources["memory_gb"] < 1:
            analysis["warnings"].append(
                "Low memory detected - consider reducing concurrent operations"
            )
            analysis["recommendations"].append(
                "Set max_concurrent_updates=1 for low memory systems"
            )

        if resources["disk_free_gb"] < 5:
            analysis["warnings"].append(
                "Low disk space - consider shorter log retention"
            )

        # Docker analysis
        docker = env_info["docker"]
        if not docker["socket_exists"]:
            analysis["warnings"].append(
                "Docker socket not found - check Docker installation"
            )

        if docker["in_container"]:
            analysis["recommendations"].append(
                "Running in container - consider security implications"
            )

        return analysis

    except Exception as e:
        return {
            "environment": {},
            "recommendations": [],
            "warnings": [f"Environment detection failed: {e}"],
        }


# =============================================================================
# Output Formatting
# =============================================================================


def print_validation_results(results: dict[str, Any]) -> None:
    """Print validation results in a formatted way"""

    print("🛳️ Harbor Configuration Validation")
    print("=" * 50)
    print()

    # Profile and status
    profile = results["profile"]
    status = "✅ VALID" if results["valid"] else "❌ INVALID"
    print(f"Profile: {profile}")
    print(f"Status: {status}")
    print()

    # Configuration summary
    if "config_summary" in results:
        summary = results["config_summary"]
        print("📋 Configuration Summary:")
        print(f"  Version: {summary['app_version']}")
        print(f"  Database: {summary['database_type']}")
        print(f"  Log Level: {summary['log_level']}")
        print(f"  Max Updates: {summary['max_concurrent_updates']}")
        print(f"  Auto Discovery: {summary['auto_discovery_enabled']}")
        print()

    # Errors
    if results["errors"]:
        print("❌ Errors:")
        for error in results["errors"]:
            print(f"  - {error}")
        print()

    # Warnings
    if results["warnings"]:
        print("⚠️ Warnings:")
        for warning in results["warnings"]:
            print(f"  - {warning}")
        print()

    # Information
    if results["info"]:
        print("ℹ️ Information:")
        for info in results["info"]:
            print(f"  - {info}")
        print()


def print_environment_analysis(analysis: dict[str, Any]) -> None:
    """Print environment analysis results"""

    print("🔍 Environment Analysis")
    print("=" * 30)
    print()

    # Platform information
    env = analysis["environment"]
    if "platform" in env:
        platform = env["platform"]
        print("🖥️ Platform:")
        print(f"  System: {platform['system']}")
        print(f"  Architecture: {platform['machine']}")
        print(f"  Python: {platform['python_version']}")
        print()

    # Resources
    if "resources" in env:
        resources = env["resources"]
        print("💾 Resources:")
        print(f"  CPU Cores: {resources['cpu_count']}")
        print(f"  Memory: {resources['memory_gb']} GB")
        print(f"  Disk Free: {resources['disk_free_gb']} GB")
        print()

    # Docker
    if "docker" in env:
        docker = env["docker"]
        print("🐳 Docker:")
        print(f"  Socket Exists: {docker['socket_exists']}")
        print(f"  In Container: {docker['in_container']}")
        print()

    # Suggestions
    if "suggested_profile" in env:
        print(f"💡 Suggested Profile: {env['suggested_profile']}")
        print()

    # Recommendations
    if analysis["recommendations"]:
        print("🔍 Recommendations:")
        for rec in analysis["recommendations"]:
            print(f"  - {rec}")
        print()

    # Warnings
    if analysis["warnings"]:
        print("⚠️ Warnings:")
        for warning in analysis["warnings"]:
            print(f"  - {warning}")
        print()


# =============================================================================
# Main CLI Interface
# =============================================================================


def main() -> None:
    """Main CLI interface for configuration validation"""

    parser = argparse.ArgumentParser(
        description="Harbor Configuration Validator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/validate_config.py                     # Validate current config
  python scripts/validate_config.py --profile homelab   # Validate homelab profile
  python scripts/validate_config.py --env-only          # Environment check only
  python scripts/validate_config.py --export production # Export template
  python scripts/validate_config.py --summary           # Quick summary
        """,
    )

    parser.add_argument(
        "--profile",
        choices=["homelab", "development", "staging", "production"],
        help="Deployment profile to validate",
    )

    parser.add_argument(
        "--env-only",
        action="store_true",
        help="Only analyze environment, skip configuration validation",
    )

    parser.add_argument(
        "--export",
        choices=["homelab", "development", "staging", "production"],
        help="Export configuration template for profile",
    )

    parser.add_argument(
        "--summary", action="store_true", help="Show quick configuration summary"
    )

    parser.add_argument(
        "--json", action="store_true", help="Output results in JSON format"
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    try:
        # Handle export command
        if args.export:
            profile_enum = DeploymentProfile(args.export)
            template = export_config_template(profile_enum)

            if args.json:
                print(json.dumps({"template": template}, indent=2))
            else:
                print(template)
            return

        # Handle environment-only analysis
        if args.env_only:
            analysis = detect_and_analyze_environment()

            if args.json:
                print(json.dumps(analysis, indent=2, default=str))
            else:
                print_environment_analysis(analysis)
            return

        # Handle summary command
        if args.summary:
            summary = get_config_summary()

            if args.json:
                print(json.dumps(summary, indent=2, default=str))
            else:
                print("🛳️ Harbor Configuration Summary")
                print("=" * 40)
                for key, value in summary.items():
                    print(f"{key}: {value}")
            return

        # Main validation
        results = validate_configuration(args.profile)

        if args.json:
            # JSON output
            print(json.dumps(results, indent=2, default=str))
        else:
            # Human-readable output
            print_validation_results(results)

            if args.verbose:
                print()
                analysis = detect_and_analyze_environment()
                print_environment_analysis(analysis)

        # Exit with appropriate code
        sys.exit(0 if results["valid"] else 1)

    except KeyboardInterrupt:
        print("\n❌ Validation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


def test_all_profiles() -> bool:
    """Test all deployment profiles for validation"""

    print("🧪 Testing All Harbor Profiles")
    print("=" * 40)
    print()

    all_valid = True

    for profile in ["homelab", "development", "staging", "production"]:
        print(f"Testing {profile} profile...")

        # Save current environment
        original_mode = os.getenv("HARBOR_MODE")

        try:
            results = validate_configuration(profile)

            if results["valid"]:
                print(f"  ✅ {profile}: Valid")
            else:
                print(f"  ❌ {profile}: Invalid")
                for error in results["errors"]:
                    print(f"    - {error}")
                all_valid = False

        except Exception as e:
            print(f"  ❌ {profile}: Exception - {e}")
            all_valid = False

        finally:
            # Restore original environment
            if original_mode:
                os.environ["HARBOR_MODE"] = original_mode
            elif "HARBOR_MODE" in os.environ:
                del os.environ["HARBOR_MODE"]

    print()
    if all_valid:
        print("✅ All profiles valid!")
    else:
        print("❌ Some profiles have issues")

    return all_valid


def check_environment_compatibility() -> dict[str, Any]:
    """Check if current environment is compatible with Harbor"""

    env_analysis = detect_and_analyze_environment()
    env_info = env_analysis["environment"]

    compatibility: dict[str, Any] = {
        "compatible": True,
        "issues": [],
        "recommendations": env_analysis["recommendations"],
        "warnings": env_analysis["warnings"],
    }

    # Check Python version
    if "platform" in env_info:
        python_version = env_info["platform"]["python_version"]
        try:
            major, minor = map(int, python_version.split(".")[:2])

            if major < 3 or (major == 3 and minor < 11):
                compatibility["compatible"] = False
                compatibility["issues"].append(
                    f"Python {python_version} not supported (requires 3.11+)"
                )
        except ValueError:
            compatibility["issues"].append(
                f"Unable to parse Python version: {python_version}"
            )

    # Check resources
    if "resources" in env_info:
        resources = env_info["resources"]

        if resources["memory_gb"] < 0.5:
            compatibility["issues"].append(
                "Insufficient memory (requires at least 512MB)"
            )

        if resources["disk_free_gb"] < 1:
            compatibility["issues"].append(
                "Insufficient disk space (requires at least 1GB)"
            )

    # Check Docker
    if "docker" in env_info:
        docker = env_info["docker"]

        if not docker["socket_exists"]:
            compatibility["compatible"] = False
            compatibility["issues"].append("Docker socket not accessible")

    return compatibility


# =============================================================================
# Configuration Templates
# =============================================================================


def generate_quick_setup_guide(profile: str) -> str:
    """Generate quick setup guide for a profile"""

    profile_info = get_profile_recommendations(DeploymentProfile(profile))

    # Build the guide content using safer string operations
    guide_parts = [
        f"# Harbor Quick Setup - {profile.title()} Profile\n",
        f"{profile_info['deployment_focus']}\n\n",
        "## 🚀 Quick Start\n\n",
        "1. **Create environment file:**\n",
        "   ```bash\n",
        "   cp .env.example .env\n",
        "   ```\n\n",
        "2. **Generate secret key:**\n",
        "   ```bash\n",
        "   openssl rand -base64 32\n",  # nosec B607 - development script only
        "   ```\n\n",
        "3. **Edit .env file:**\n",
        "   ```bash\n",
        f"   # Set your profile\n   HARBOR_MODE={profile}\n\n",
        "   # Add your secret key\n",
        "   HARBOR_SECURITY_SECRET_KEY=your-generated-key-here\n",
        "   ```\n\n",
        "4. **Start Harbor:**\n",
        "   ```bash\n",
        "   docker-compose up -d\n",
        "   ```\n\n",
        "## ⚙️ Profile Characteristics\n\n",
        f"- **Focus**: {profile_info['deployment_focus']}\n",
        f"- **Security**: {profile_info['security_level']}\n",
        f"- **Resources**: {profile_info['resource_usage']}\n",
        f"- **Updates**: {profile_info['update_strategy']}\n\n",
        "## 🔍 Recommended Features\n\n",
        f"{profile_info['recommended_features']}\n\n",
        "## 🔧 Next Steps\n\n",
        "1. Access Harbor at http://localhost:8080\n",
        "2. Login with generated credentials\n",
        "3. Review discovered containers\n",
        "4. Configure update policies\n",
        "5. Set up monitoring (if applicable)\n\n",
        f"For detailed configuration options, see: docs/configuration/{profile}.md\n",
    ]

    return "".join(guide_parts)


# =============================================================================
# Development and Testing Utilities
# =============================================================================


def validate_configuration_files() -> dict[str, Any]:
    """Validate configuration files in config directory"""

    config_dir = Path("config")
    results: dict[str, Any] = {
        "valid": True,
        "files_checked": 0,
        "files_valid": 0,
        "errors": [],
        "warnings": [],
    }

    if not config_dir.exists():
        results["warnings"].append("Config directory not found")
        return results

    # Check YAML configuration files
    yaml_files = list(config_dir.glob("*.yaml")) + list(config_dir.glob("*.yml"))

    for yaml_file in yaml_files:
        results["files_checked"] += 1

        try:
            # Try to load YAML content
            import yaml

            with open(yaml_file, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)

            if content is None:
                results["warnings"].append(f"{yaml_file.name}: Empty YAML file")
            else:
                results["files_valid"] += 1

        except ImportError:
            results["warnings"].append("PyYAML not available for YAML validation")
            break
        except yaml.YAMLError as e:
            results["valid"] = False
            results["errors"].append(f"{yaml_file.name}: YAML syntax error - {e}")
        except Exception as e:
            results["errors"].append(f"{yaml_file.name}: Unexpected error - {e}")

    return results


def generate_environment_template(profile: str) -> str:
    """Generate .env template for a profile"""

    # Create a temporary settings instance to get defaults
    os.environ["HARBOR_MODE"] = profile
    settings = reload_settings()

    template_parts = [
        f"# Harbor Container Updater - {profile.title()} Profile Environment\n",
        f"# Generated template for Harbor configuration\n\n",
        "# ===== CORE CONFIGURATION =====\n",
        f"HARBOR_MODE={profile}\n",
        "# HARBOR_SECURITY_SECRET_KEY=  # Generate with: openssl rand -base64 32\n\n",
        "# ===== APPLICATION SETTINGS =====\n",
        f"HARBOR_DEBUG={str(settings.debug).lower()}\n",
        f"HARBOR_HOST={settings.host}\n",
        f"HARBOR_PORT={settings.port}\n\n",
        "# ===== SECURITY SETTINGS =====\n",
        f"HARBOR_SECURITY_REQUIRE_HTTPS={str(settings.security.require_https).lower()}\n",
        f"HARBOR_SECURITY_SESSION_TIMEOUT_HOURS={settings.security.session_timeout_hours}\n",
        f"HARBOR_SECURITY_API_KEY_REQUIRED={str(settings.security.api_key_required).lower()}\n",
        f"HARBOR_SECURITY_PASSWORD_MIN_LENGTH={settings.security.password_min_length}\n\n",
        "# ===== UPDATE SETTINGS =====\n",
        f"HARBOR_UPDATE_DEFAULT_CHECK_INTERVAL_SECONDS={settings.updates.default_check_interval_seconds}\n",
        f"HARBOR_UPDATE_DEFAULT_UPDATE_TIME={settings.updates.default_update_time}\n",
        f"HARBOR_UPDATE_MAX_CONCURRENT_UPDATES={settings.updates.max_concurrent_updates}\n\n",
        "# ===== LOGGING SETTINGS =====\n",
        f"HARBOR_LOG_LOG_LEVEL={settings.logging.log_level.value}\n",
        f"HARBOR_LOG_LOG_FORMAT={settings.logging.log_format.value}\n",
        f"HARBOR_LOG_LOG_RETENTION_DAYS={settings.logging.log_retention_days}\n\n",
        "# ===== FEATURE FLAGS =====\n",
        f"HARBOR_FEATURE_ENABLE_AUTO_DISCOVERY={str(settings.features.enable_auto_discovery).lower()}\n",
        f"HARBOR_FEATURE_SHOW_GETTING_STARTED={str(settings.features.show_getting_started).lower()}\n",
        f"HARBOR_FEATURE_ENABLE_SIMPLE_MODE={str(settings.features.enable_simple_mode).lower()}\n\n",
        "# ===== DOCKER SETTINGS =====\n",
        f"HARBOR_DOCKER_DOCKER_HOST={settings.docker.docker_host}\n",
        f"HARBOR_DOCKER_DOCKER_TIMEOUT={settings.docker.docker_timeout}\n",
        f"HARBOR_DOCKER_DISCOVERY_INTERVAL_SECONDS={settings.docker.discovery_interval_seconds}\n\n",
        "# ===== DATABASE SETTINGS =====\n",
        f"HARBOR_DB_DATABASE_TYPE={settings.database.database_type.value}\n",
        f"HARBOR_DB_POOL_SIZE={settings.database.pool_size}\n",
        "# HARBOR_DB_DATABASE_URL=  # Auto-generated for SQLite, required for PostgreSQL\n\n",
    ]

    return "".join(template_parts)


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    # Special commands that don't require argument parsing
    if len(sys.argv) > 1:
        if sys.argv[1] == "test-all":
            success = test_all_profiles()
            sys.exit(0 if success else 1)
        elif sys.argv[1] == "environment":
            analysis = detect_and_analyze_environment()
            print_environment_analysis(analysis)
            sys.exit(0)
        elif sys.argv[1] == "compatibility":
            compat = check_environment_compatibility()
            if compat["compatible"]:
                print("✅ Environment is compatible with Harbor")
            else:
                print("❌ Environment compatibility issues:")
                for issue in compat["issues"]:
                    print(f"  - {issue}")
            sys.exit(0 if compat["compatible"] else 1)
        elif sys.argv[1] == "quick-guide":
            profile = sys.argv[2] if len(sys.argv) > 2 else "homelab"
            guide = generate_quick_setup_guide(profile)
            print(guide)
            sys.exit(0)
        elif sys.argv[1] == "env-template":
            profile = sys.argv[2] if len(sys.argv) > 2 else "homelab"
            template = generate_environment_template(profile)
            print(template)
            sys.exit(0)
        elif sys.argv[1] == "validate-files":
            results = validate_configuration_files()
            print(
                f"Configuration files validation: {'✅ PASSED' if results['valid'] else '❌ FAILED'}"
            )
            print(f"Files checked: {results['files_checked']}")
            print(f"Files valid: {results['files_valid']}")
            if results["errors"]:
                print("Errors:")
                for error in results["errors"]:
                    print(f"  - {error}")
            if results["warnings"]:
                print("Warnings:")
                for warning in results["warnings"]:
                    print(f"  - {warning}")
            sys.exit(0 if results["valid"] else 1)

    # Default to main CLI interface
    main()
