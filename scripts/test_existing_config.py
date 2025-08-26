#!/usr/bin/env python3
"""
Harbor Configuration Test Script - Works with existing app/config.py

This script tests the existing configuration system without requiring
additional modules.

Author: Harbor Team
License: MIT
"""

import sys
import os
from pathlib import Path

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
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
    """Test basic configuration loading from existing app/config.py."""
    console.print("\n[bold blue]Testing Existing Configuration System...[/bold blue]")

    try:
        from app.config import (
            get_settings,
            DeploymentProfile,
            get_config_summary,
            is_development,
            is_production,
            is_homelab,
        )

        settings = get_settings()

        # Create summary table
        table = Table(title="Configuration Summary", box=box.ROUNDED)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("App Name", settings.app_name)
        table.add_row("Version", settings.app_version)
        table.add_row("Deployment Profile", settings.deployment_profile.value)
        table.add_row("Debug Mode", str(settings.debug))
        table.add_row("Data Directory", str(settings.data_dir))
        table.add_row("Logs Directory", str(settings.logs_dir))
        table.add_row("Timezone", settings.timezone)

        console.print(table)

        # Database settings
        db_table = Table(title="Database Settings", box=box.ROUNDED)
        db_table.add_column("Setting", style="cyan")
        db_table.add_column("Value", style="yellow")

        db_table.add_row("Type", settings.database.database_type.value)
        db_table.add_row("URL", settings.database.database_url or "Auto-generated")
        db_table.add_row("Pool Size", str(settings.database.pool_size))
        db_table.add_row("Max Overflow", str(settings.database.max_overflow))

        console.print(db_table)

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
        security_table.add_row(
            "Require Special Chars", str(settings.security.password_require_special)
        )

        console.print(security_table)

        # Profile helpers
        console.print("\n[bold]Profile Check Functions:[/bold]")
        console.print(f"  is_development(): {is_development()}")
        console.print(f"  is_production(): {is_production()}")
        console.print(f"  is_homelab(): {is_homelab()}")

        console.print(
            "\n[bold green]✅ Configuration loaded successfully![/bold green]"
        )
        return True

    except Exception as e:
        console.print(f"[bold red]❌ Failed to load configuration: {e}[/bold red]")
        logger.exception("Configuration loading error")
        return False


def test_features():
    """Test feature flags from existing configuration."""
    console.print("\n[bold blue]Testing Feature Flags...[/bold blue]")

    try:
        from app.config import get_settings

        settings = get_settings()

        # Create feature table
        table = Table(
            title=f"Feature Flags - {settings.deployment_profile.value.upper()} Profile",
            box=box.ROUNDED,
        )
        table.add_column("Feature", style="cyan")
        table.add_column("Status", style="green")

        table.add_row(
            "Auto Discovery", "✅" if settings.features.enable_auto_discovery else "❌"
        )
        table.add_row("Metrics", "✅" if settings.features.enable_metrics else "❌")
        table.add_row(
            "Health Checks", "✅" if settings.features.enable_health_checks else "❌"
        )
        table.add_row(
            "Simple Mode", "✅" if settings.features.enable_simple_mode else "❌"
        )
        table.add_row(
            "Getting Started", "✅" if settings.features.show_getting_started else "❌"
        )
        table.add_row(
            "Notifications", "✅" if settings.features.enable_notifications else "❌"
        )
        table.add_row("RBAC", "✅" if settings.features.enable_rbac else "❌")

        console.print(table)

        console.print("[bold green]✅ Feature flags loaded successfully![/bold green]")
        return True

    except Exception as e:
        console.print(f"[bold red]❌ Failed to test features: {e}[/bold red]")
        logger.exception("Feature test error")
        return False


def test_environment_detection():
    """Test environment detection functionality."""
    console.print("\n[bold blue]Testing Environment Detection...[/bold blue]")

    try:
        from app.config import detect_environment

        env_info = detect_environment()

        # Platform info
        platform_table = Table(title="Platform Information", box=box.ROUNDED)
        platform_table.add_column("Property", style="cyan")
        platform_table.add_column("Value", style="yellow")

        platform_info = env_info.get("platform", {})
        platform_table.add_row("System", platform_info.get("system", "Unknown"))
        platform_table.add_row("Machine", platform_info.get("machine", "Unknown"))
        platform_table.add_row("Release", platform_info.get("release", "Unknown")[:50])

        console.print(platform_table)

        # Environment info
        env_table = Table(title="Environment Details", box=box.ROUNDED)
        env_table.add_column("Property", style="cyan")
        env_table.add_column("Value", style="green")

        environment = env_info.get("environment", {})
        env_table.add_row(
            "Python Version", environment.get("python_version", "Unknown").split()[0]
        )
        env_table.add_row(
            "Is Container", "✅" if environment.get("is_container") else "❌"
        )
        env_table.add_row("Is Cloud", "✅" if environment.get("is_cloud") else "❌")
        env_table.add_row("CPU Count", str(environment.get("cpu_count", 0)))
        env_table.add_row("Memory (GB)", f"{environment.get('memory_gb', 0):.1f}")

        console.print(env_table)

        # Recommendations
        console.print(f"\n[bold]Profile Recommendations:[/bold]")
        console.print(
            f"  Suggested Profile: [green]{env_info.get('suggested_profile')}[/green]"
        )
        console.print(
            f"  Current Profile: [yellow]{env_info.get('current_profile')}[/yellow]"
        )
        console.print(
            f"  Docker Available: {'✅' if env_info.get('docker_available') else '❌'}"
        )

        console.print("\n[bold green]✅ Environment detection successful![/bold green]")
        return True

    except Exception as e:
        console.print(f"[bold red]❌ Failed to detect environment: {e}[/bold red]")
        logger.exception("Environment detection error")
        return False


def test_config_summary():
    """Test configuration summary generation."""
    console.print("\n[bold blue]Testing Configuration Summary...[/bold blue]")

    try:
        from app.config import get_config_summary

        summary = get_config_summary()

        table = Table(title="Configuration Summary", box=box.ROUNDED)
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="yellow")

        for key, value in summary.items():
            if not isinstance(value, dict):
                table.add_row(key, str(value))

        console.print(table)

        console.print("[bold green]✅ Configuration summary generated![/bold green]")
        return True

    except Exception as e:
        console.print(f"[bold red]❌ Failed to get config summary: {e}[/bold red]")
        logger.exception("Config summary error")
        return False


def test_validation():
    """Test runtime requirement validation."""
    console.print("\n[bold blue]Testing Runtime Validation...[/bold blue]")

    try:
        from app.config import validate_runtime_requirements

        errors = validate_runtime_requirements()

        if errors:
            console.print("[yellow]⚠️  Validation Issues:[/yellow]")
            for error in errors:
                console.print(f"  - {error}")
        else:
            console.print("[bold green]✅ No validation errors found![/bold green]")

        return len(errors) == 0

    except Exception as e:
        console.print(f"[bold red]❌ Failed to validate: {e}[/bold red]")
        logger.exception("Validation error")
        return False


def test_profile_switching():
    """Test changing deployment profiles."""
    console.print("\n[bold blue]Testing Profile Switching...[/bold blue]")

    try:
        from app.config import (
            clear_settings_cache,
            reload_settings,
            create_fresh_settings,
            DeploymentProfile,
        )

        profiles = [
            DeploymentProfile.HOMELAB,
            DeploymentProfile.DEVELOPMENT,
            DeploymentProfile.STAGING,
            DeploymentProfile.PRODUCTION,
        ]

        table = Table(title="Profile Configurations", box=box.ROUNDED)
        table.add_column("Profile", style="cyan")
        table.add_column("Debug", style="yellow")
        table.add_column("HTTPS", style="yellow")
        table.add_column("Session (hrs)", style="yellow")
        table.add_column("Password Min", style="yellow")

        for profile in profiles:
            # Set environment and reload
            os.environ["HARBOR_MODE"] = profile.value
            settings = reload_settings()

            table.add_row(
                profile.value,
                "✅" if settings.debug else "❌",
                "✅" if settings.security.require_https else "❌",
                str(settings.security.session_timeout_hours),
                str(settings.security.password_min_length),
            )

        console.print(table)

        # Reset to original
        clear_settings_cache()

        console.print("[bold green]✅ Profile switching works![/bold green]")
        return True

    except Exception as e:
        console.print(f"[bold red]❌ Failed to test profiles: {e}[/bold red]")
        logger.exception("Profile test error")
        return False


def main():
    """Main entry point for configuration testing."""
    console.print(
        Panel.fit(
            "[bold cyan]Harbor Configuration Test Suite[/bold cyan]\n"
            "Testing the existing configuration system (app/config.py)",
            box=box.DOUBLE,
        )
    )

    # Track test results
    results = []

    # Run tests
    tests = [
        ("Basic Configuration", test_basic_config),
        ("Feature Flags", test_features),
        ("Environment Detection", test_environment_detection),
        ("Configuration Summary", test_config_summary),
        ("Runtime Validation", test_validation),
        ("Profile Switching", test_profile_switching),
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
        console.print("\nYour existing configuration system is working perfectly!")
        sys.exit(0)
    else:
        console.print("\n[bold red]❌ Some configuration tests failed![/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
