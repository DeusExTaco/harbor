#!/usr/bin/env python3
"""
Harbor Configuration Test CLI

This script provides a command-line interface for testing and validating
Harbor configuration settings. It can be run directly or via Docker.

Author: Harbor Team
License: MIT
"""

import sys
import os
from pathlib import Path

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Rich console
console = Console()


def test_basic_config():
    """Test basic configuration loading."""
    console.print("\n[bold blue]Testing Basic Configuration Loading...[/bold blue]")

    try:
        from app.config import get_settings, DeploymentProfile

        settings = get_settings()

        # Create summary table
        table = Table(title="Configuration Summary", box=box.ROUNDED)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Deployment Mode", settings.mode.value)
        table.add_row("Debug Mode", str(settings.debug))
        table.add_row("Host", settings.host)
        table.add_row("Port", str(settings.port))
        table.add_row("Data Directory", str(settings.data_dir))
        table.add_row("Database Type", settings.database.type)
        table.add_row(
            "Database URL", settings.database.database_url or "Auto-generated"
        )
        table.add_row("Docker Host", settings.docker.host)
        table.add_row("Log Level", settings.logging.level.value)
        table.add_row("Log Format", settings.logging.format.value)

        console.print(table)

        # Security settings
        security_table = Table(title="Security Settings", box=box.ROUNDED)
        security_table.add_column("Setting", style="cyan")
        security_table.add_column("Value", style="yellow")

        security_table.add_row("HTTPS Required", str(settings.security.require_https))
        security_table.add_row(
            "Session Timeout", f"{settings.security.session_timeout_hours} hours"
        )
        security_table.add_row(
            "API Key Required", str(settings.security.api_key_required)
        )
        security_table.add_row(
            "Min Password Length", str(settings.security.password_min_length)
        )
        security_table.add_row("MFA Enabled", str(settings.security.mfa_enabled))

        console.print(security_table)

        console.print("[bold green]✅ Configuration loaded successfully![/bold green]")
        return True

    except Exception as e:
        console.print(f"[bold red]❌ Failed to load configuration: {e}[/bold red]")
        logger.exception("Configuration loading error")
        return False


def test_feature_flags():
    """Test feature flags for current profile."""
    console.print("\n[bold blue]Testing Feature Flags...[/bold blue]")

    try:
        from app.config import get_settings
        from app.config.feature_flags import get_feature_flags, get_enabled_features

        settings = get_settings()
        flags = get_feature_flags(settings.mode)
        enabled = get_enabled_features(flags)

        # Create feature table
        table = Table(
            title=f"Feature Flags - {settings.mode.value.upper()} Profile",
            box=box.ROUNDED,
        )
        table.add_column("Category", style="cyan")
        table.add_column("Feature", style="magenta")
        table.add_column("Status", style="green")

        for category, features in enabled.items():
            for feature, is_enabled in features.items():
                if is_enabled:
                    table.add_row(category, feature, "✓ Enabled")

        console.print(table)

        # Show disabled future features
        future_table = Table(title="Future Features (Disabled)", box=box.SIMPLE)
        future_table.add_column("Feature", style="dim")
        future_table.add_column("Target Release", style="dim")

        # Check specific future features
        future_checks = [
            ("auth.enable_mfa", "M7+"),
            ("auth.enable_multi_user", "M8+"),
            ("runtime.enable_kubernetes", "M9+"),
            ("updates.enable_blue_green", "M7+"),
            ("integrations.enable_slack", "M7+"),
        ]

        for feature_path, target in future_checks:
            parts = feature_path.split(".")
            category_obj = getattr(flags, parts[0])
            feature_value = getattr(category_obj, parts[1])
            if not feature_value:
                future_table.add_row(feature_path, target)

        console.print(future_table)

        console.print(
            "[bold green]✅ Feature flags validated successfully![/bold green]"
        )
        return True

    except Exception as e:
        console.print(f"[bold red]❌ Failed to test feature flags: {e}[/bold red]")
        logger.exception("Feature flag error")
        return False


def test_profile_switching():
    """Test switching between deployment profiles."""
    console.print("\n[bold blue]Testing Profile Switching...[/bold blue]")

    try:
        from app.config import load_config, DeploymentProfile, reset_config

        profiles = [
            DeploymentProfile.HOMELAB,
            DeploymentProfile.DEVELOPMENT,
            DeploymentProfile.STAGING,
            DeploymentProfile.PRODUCTION,
        ]

        table = Table(title="Profile Configuration Differences", box=box.ROUNDED)
        table.add_column("Profile", style="cyan")
        table.add_column("HTTPS", style="yellow")
        table.add_column("Session (hrs)", style="yellow")
        table.add_column("Workers", style="yellow")
        table.add_column("Check Interval", style="yellow")

        for profile in profiles:
            # Reset configuration
            reset_config()
            os.environ["HARBOR_MODE"] = profile.value

            config = load_config(validate=False)

            table.add_row(
                profile.value,
                "✓" if config.security.require_https else "✗",
                str(config.security.session_timeout_hours),
                str(config.resources.get_worker_count()),
                f"{config.updates.default_check_interval_seconds}s",
            )

        console.print(table)

        # Reset to original
        reset_config()

        console.print("[bold green]✅ Profile switching works correctly![/bold green]")
        return True

    except Exception as e:
        console.print(f"[bold red]❌ Failed to test profile switching: {e}[/bold red]")
        logger.exception("Profile switching error")
        return False


def test_validation():
    """Test configuration validation."""
    console.print("\n[bold blue]Testing Configuration Validation...[/bold blue]")

    try:
        from app.config import get_settings, validate_config

        settings = get_settings()
        validation = validate_config(settings)

        # Display validation results
        if validation["valid"]:
            console.print(
                f"[bold green]✅ Configuration is valid for {validation['profile']} profile[/bold green]"
            )
        else:
            console.print(
                f"[bold red]❌ Configuration is invalid for {validation['profile']} profile[/bold red]"
            )

        if validation["warnings"]:
            console.print("\n[yellow]⚠️  Warnings:[/yellow]")
            for warning in validation["warnings"]:
                console.print(f"  - {warning}")

        if validation["errors"]:
            console.print("\n[red]❌ Errors:[/red]")
            for error in validation["errors"]:
                console.print(f"  - {error}")

        return validation["valid"]

    except Exception as e:
        console.print(f"[bold red]❌ Failed to validate configuration: {e}[/bold red]")
        logger.exception("Validation error")
        return False


def test_environment_overrides():
    """Test environment variable overrides."""
    console.print("\n[bold blue]Testing Environment Variable Overrides...[/bold blue]")

    try:
        from app.config import load_config, reset_config

        # Test with custom environment variables
        test_vars = {
            "HARBOR_DEBUG": "true",
            "HARBOR_PORT": "9999",
            "LOG_LEVEL": "DEBUG",
            "HARBOR_SECURITY_REQUIRE_HTTPS": "true",
            "HARBOR_UPDATE_MAX_CONCURRENT_UPDATES": "10",
        }

        # Set test variables
        for key, value in test_vars.items():
            os.environ[key] = value

        # Reset and reload config
        reset_config()
        config = load_config(validate=False)

        # Check overrides
        table = Table(title="Environment Override Test", box=box.ROUNDED)
        table.add_column("Variable", style="cyan")
        table.add_column("Expected", style="yellow")
        table.add_column("Actual", style="green")
        table.add_column("Result", style="magenta")

        checks = [
            ("HARBOR_DEBUG", True, config.debug),
            ("HARBOR_PORT", 9999, config.port),
            ("LOG_LEVEL", "DEBUG", config.logging.level.value),
            ("HARBOR_SECURITY_REQUIRE_HTTPS", True, config.security.require_https),
            (
                "HARBOR_UPDATE_MAX_CONCURRENT_UPDATES",
                10,
                config.updates.max_concurrent_updates,
            ),
        ]

        all_passed = True
        for var_name, expected, actual in checks:
            passed = expected == actual
            all_passed &= passed
            table.add_row(
                var_name, str(expected), str(actual), "✅" if passed else "❌"
            )

        console.print(table)

        # Clean up test variables
        for key in test_vars:
            del os.environ[key]

        # Reset config
        reset_config()

        if all_passed:
            console.print(
                "[bold green]✅ Environment overrides work correctly![/bold green]"
            )
        else:
            console.print("[bold red]❌ Some environment overrides failed![/bold red]")

        return all_passed

    except Exception as e:
        console.print(
            f"[bold red]❌ Failed to test environment overrides: {e}[/bold red]"
        )
        logger.exception("Environment override error")
        return False


def main():
    """Main entry point for configuration testing."""
    console.print(
        Panel.fit(
            "[bold cyan]Harbor Configuration Test Suite[/bold cyan]\n"
            "Testing configuration loading, validation, and features",
            box=box.DOUBLE,
        )
    )

    # Track test results
    results = []

    # Run tests
    tests = [
        ("Basic Configuration", test_basic_config),
        ("Feature Flags", test_feature_flags),
        ("Profile Switching", test_profile_switching),
        ("Configuration Validation", test_validation),
        ("Environment Overrides", test_environment_overrides),
    ]

    for test_name, test_func in tests:
        console.rule(f"[bold]{test_name}[/bold]")
        success = test_func()
        results.append((test_name, success))

    # Summary
    console.rule("[bold]Test Summary[/bold]")

    summary_table = Table(title="Test Results", box=box.ROUNDED)
    summary_table.add_column("Test", style="cyan")
    summary_table.add_column("Result", style="green")

    all_passed = True
    for test_name, success in results:
        all_passed &= success
        summary_table.add_row(
            test_name, "[green]✅ PASSED[/green]" if success else "[red]❌ FAILED[/red]"
        )

    console.print(summary_table)

    if all_passed:
        console.print("\n[bold green]🎉 All configuration tests passed![/bold green]")
        sys.exit(0)
    else:
        console.print("\n[bold red]❌ Some configuration tests failed![/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
