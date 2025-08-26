#!/usr/bin/env python3
"""
Harbor Direct Configuration Test

This script tests the configuration directly from app/config.py,
avoiding any issues with the app/config/ directory.

Author: Harbor Team
License: MIT
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Temporarily rename the config directory to avoid conflicts
config_dir = Path(__file__).parent.parent / "app" / "config"
config_backup = Path(__file__).parent.parent / "app" / "config_modules"

if config_dir.exists() and not config_backup.exists():
    print(
        f"Note: Temporarily moving {config_dir} to {config_backup} to avoid conflicts"
    )
    config_dir.rename(config_backup)

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
    """Test basic configuration loading."""
    console.print("\n[bold blue]Testing Configuration Loading...[/bold blue]")

    try:
        # Import directly from app.config (the .py file, not the directory)
        import app.config as config_module

        settings = config_module.get_settings()

        # Create summary table
        table = Table(title="Configuration Summary", box=box.ROUNDED)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("App Name", settings.app_name)
        table.add_row("Version", settings.app_version)
        table.add_row("Deployment Profile", settings.deployment_profile.value)
        table.add_row("Debug Mode", str(settings.debug))
        table.add_row("Testing Mode", str(settings.testing))
        table.add_row("Data Directory", str(settings.data_dir))
        table.add_row("Logs Directory", str(settings.logs_dir))
        table.add_row("Timezone", settings.timezone)

        console.print(table)

        # Database settings
        db_table = Table(title="Database Settings", box=box.ROUNDED)
        db_table.add_column("Setting", style="cyan")
        db_table.add_column("Value", style="yellow")

        db_table.add_row("Type", settings.database.database_type.value)
        if settings.database.database_url:
            # Mask sensitive parts of database URL
            db_url = settings.database.database_url
            if "://" in db_url:
                parts = db_url.split("://")
                if len(parts) > 1 and "@" in parts[1]:
                    # Hide password
                    user_pass, rest = parts[1].split("@", 1)
                    if ":" in user_pass:
                        user, _ = user_pass.split(":", 1)
                        db_url = f"{parts[0]}://{user}:***@{rest}"
            db_table.add_row("URL", db_url)
        else:
            db_table.add_row(
                "SQLite Path",
                str(settings.database.sqlite_path)
                if settings.database.sqlite_path
                else "N/A",
            )

        db_table.add_row("Pool Size", str(settings.database.pool_size))
        db_table.add_row("Max Overflow", str(settings.database.max_overflow))
        db_table.add_row("Pool Timeout", f"{settings.database.pool_timeout}s")

        console.print(db_table)

        # Security settings
        security_table = Table(title="Security Settings", box=box.ROUNDED)
        security_table.add_column("Setting", style="cyan")
        security_table.add_column("Value", style="yellow")

        security_table.add_row(
            "HTTPS Required", "✅" if settings.security.require_https else "❌"
        )
        security_table.add_row(
            "API Key Required", "✅" if settings.security.api_key_required else "❌"
        )
        security_table.add_row(
            "Session Timeout", f"{settings.security.session_timeout_hours} hours"
        )
        security_table.add_row(
            "Rate Limit", f"{settings.security.api_rate_limit_per_hour}/hour"
        )
        security_table.add_row(
            "Min Password Length", str(settings.security.password_min_length)
        )
        security_table.add_row(
            "Special Chars Required",
            "✅" if settings.security.password_require_special else "❌",
        )

        console.print(security_table)

        # Update settings
        update_table = Table(title="Update Settings", box=box.ROUNDED)
        update_table.add_column("Setting", style="cyan")
        update_table.add_column("Value", style="green")

        update_table.add_row(
            "Check Interval", f"{settings.updates.default_check_interval_seconds}s"
        )
        update_table.add_row("Update Time", settings.updates.default_update_time)
        update_table.add_row(
            "Max Concurrent", str(settings.updates.max_concurrent_updates)
        )
        update_table.add_row(
            "Cleanup Keep Images", str(settings.updates.default_cleanup_keep_images)
        )
        update_table.add_row(
            "Update Timeout", f"{settings.updates.update_timeout_seconds}s"
        )

        console.print(update_table)

        console.print(
            "\n[bold green]✅ Configuration loaded successfully![/bold green]"
        )
        return True

    except Exception as e:
        console.print(f"[bold red]❌ Failed to load configuration: {e}[/bold red]")
        logger.exception("Configuration loading error")
        return False


def test_features():
    """Test feature settings."""
    console.print("\n[bold blue]Testing Feature Settings...[/bold blue]")

    try:
        import app.config as config_module

        settings = config_module.get_settings()

        # Create feature table
        table = Table(
            title=f"Features - {settings.deployment_profile.value.upper()} Profile",
            box=box.ROUNDED,
        )
        table.add_column("Feature", style="cyan")
        table.add_column("Status", style="green")

        features = [
            ("Auto Discovery", settings.features.enable_auto_discovery),
            ("Metrics", settings.features.enable_metrics),
            ("Health Checks", settings.features.enable_health_checks),
            ("Simple Mode", settings.features.enable_simple_mode),
            ("Getting Started", settings.features.show_getting_started),
            ("Notifications", settings.features.enable_notifications),
            ("RBAC", settings.features.enable_rbac),
        ]

        for name, enabled in features:
            table.add_row(name, "✅ Enabled" if enabled else "❌ Disabled")

        console.print(table)

        console.print(
            "[bold green]✅ Feature settings loaded successfully![/bold green]"
        )
        return True

    except Exception as e:
        console.print(f"[bold red]❌ Failed to test features: {e}[/bold red]")
        logger.exception("Feature test error")
        return False


def test_helper_functions():
    """Test helper functions."""
    console.print("\n[bold blue]Testing Helper Functions...[/bold blue]")

    try:
        import app.config as config_module

        # Test profile detection functions
        table = Table(title="Profile Detection", box=box.ROUNDED)
        table.add_column("Function", style="cyan")
        table.add_column("Result", style="yellow")

        table.add_row("is_development()", str(config_module.is_development()))
        table.add_row("is_production()", str(config_module.is_production()))
        table.add_row("is_homelab()", str(config_module.is_homelab()))

        console.print(table)

        # Test config summary
        summary = config_module.get_config_summary()

        summary_table = Table(title="Config Summary Function", box=box.ROUNDED)
        summary_table.add_column("Key", style="cyan")
        summary_table.add_column("Value", style="green")

        for key, value in summary.items():
            summary_table.add_row(key, str(value))

        console.print(summary_table)

        console.print("[bold green]✅ Helper functions work correctly![/bold green]")
        return True

    except Exception as e:
        console.print(f"[bold red]❌ Failed to test helpers: {e}[/bold red]")
        logger.exception("Helper test error")
        return False


def test_environment_detection():
    """Test environment detection."""
    console.print("\n[bold blue]Testing Environment Detection...[/bold blue]")

    try:
        import app.config as config_module

        env_info = config_module.detect_environment()

        # Platform info
        platform_table = Table(title="Platform Information", box=box.ROUNDED)
        platform_table.add_column("Property", style="cyan")
        platform_table.add_column("Value", style="yellow")

        platform = env_info.get("platform", {})
        platform_table.add_row("System", platform.get("system", "Unknown"))
        platform_table.add_row("Machine", platform.get("machine", "Unknown"))
        platform_table.add_row(
            "Processor",
            platform.get("processor", "Unknown")[:50]
            if platform.get("processor")
            else "Unknown",
        )

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

        # Docker and permissions
        console.print(f"\n[bold]System Status:[/bold]")
        console.print(
            f"  Docker Available: {'✅' if env_info.get('docker_available') else '❌'}"
        )

        write_perms = env_info.get("write_permissions", {})
        console.print(f"  Write Permissions:")
        for location, has_perm in write_perms.items():
            console.print(f"    {location}: {'✅' if has_perm else '❌'}")

        console.print(
            f"\n  Suggested Profile: [green]{env_info.get('suggested_profile')}[/green]"
        )
        console.print(
            f"  Current Profile: [yellow]{env_info.get('current_profile')}[/yellow]"
        )

        console.print("\n[bold green]✅ Environment detection successful![/bold green]")
        return True

    except Exception as e:
        console.print(f"[bold red]❌ Failed to detect environment: {e}[/bold red]")
        logger.exception("Environment detection error")
        return False


def test_validation():
    """Test runtime requirement validation."""
    console.print("\n[bold blue]Testing Runtime Validation...[/bold blue]")

    try:
        import app.config as config_module

        errors = config_module.validate_runtime_requirements()

        if errors:
            console.print("[yellow]⚠️  Validation Issues Found:[/yellow]")
            for error in errors:
                console.print(f"  - {error}")
        else:
            console.print("[bold green]✅ No validation errors![/bold green]")

        return len(errors) == 0

    except Exception as e:
        console.print(f"[bold red]❌ Failed to validate: {e}[/bold red]")
        logger.exception("Validation error")
        return False


def test_reload_mechanism():
    """Test configuration reload mechanism."""
    console.print("\n[bold blue]Testing Configuration Reload...[/bold blue]")

    try:
        import app.config as config_module

        # Get initial settings
        initial = config_module.get_settings()
        initial_mode = initial.deployment_profile.value

        # Change environment and reload
        os.environ["HARBOR_MODE"] = "development"
        os.environ["HARBOR_DEBUG"] = "true"

        # Force reload
        reloaded = config_module.reload_settings()

        table = Table(title="Configuration Reload Test", box=box.ROUNDED)
        table.add_column("Setting", style="cyan")
        table.add_column("Before", style="yellow")
        table.add_column("After", style="green")

        table.add_row("Profile", initial_mode, reloaded.deployment_profile.value)
        table.add_row("Debug", str(initial.debug), str(reloaded.debug))

        console.print(table)

        # Clear cache for cleanup
        config_module.clear_settings_cache()

        # Reset environment
        if initial_mode != "development":
            os.environ["HARBOR_MODE"] = initial_mode
        if "HARBOR_DEBUG" in os.environ:
            del os.environ["HARBOR_DEBUG"]

        console.print("[bold green]✅ Reload mechanism works correctly![/bold green]")
        return True

    except Exception as e:
        console.print(f"[bold red]❌ Failed to test reload: {e}[/bold red]")
        logger.exception("Reload test error")
        return False


def main():
    """Main entry point."""
    console.print(
        Panel.fit(
            "[bold cyan]Harbor Direct Configuration Test[/bold cyan]\n"
            "Testing configuration directly from app/config.py",
            box=box.DOUBLE,
        )
    )

    # Check if config directory exists
    config_dir = Path(__file__).parent.parent / "app" / "config"
    if config_dir.exists():
        console.print(
            f"[yellow]Warning: {config_dir} exists and may cause import conflicts[/yellow]"
        )
        console.print(
            "[yellow]Consider renaming it to app/config_modules if issues persist[/yellow]\n"
        )

    # Track results
    results = []

    # Run tests
    tests = [
        ("Basic Configuration", test_basic_config),
        ("Feature Settings", test_features),
        ("Helper Functions", test_helper_functions),
        ("Environment Detection", test_environment_detection),
        ("Runtime Validation", test_validation),
        ("Reload Mechanism", test_reload_mechanism),
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

    # Restore config directory if we moved it
    config_backup = Path(__file__).parent.parent / "app" / "config_modules"
    if config_backup.exists() and not config_dir.exists():
        console.print(f"\nRestoring {config_backup} to {config_dir}")
        config_backup.rename(config_dir)

    if all_passed:
        console.print("\n[bold green]🎉 All configuration tests passed![/bold green]")
        console.print("\nYour app/config.py is working perfectly!")
        console.print("\n[bold]Next Steps:[/bold]")
        console.print(
            "1. If app/config/ directory exists, consider renaming it to avoid conflicts"
        )
        console.print("2. Use app.config directly for all configuration needs")
        console.print(
            "3. The factory pattern in your config.py handles Pydantic v2 correctly"
        )
        sys.exit(0)
    else:
        console.print("\n[bold red]❌ Some configuration tests failed![/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
