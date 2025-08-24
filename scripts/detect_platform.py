#!/usr/bin/env python3
"""
Harbor Container Updater - Platform Detection and Optimization

This script detects the current platform and provides optimization recommendations
for Harbor deployment. Used both during Docker build and runtime.

Following Harbor Project Structure from foundational documents.
"""

import os
import platform
import sys
from pathlib import Path
from typing import Any


def detect_platform_info() -> dict[str, Any]:
    """
    Detect platform information and return structured data.

    Returns:
        Dict containing platform details and optimization recommendations
    """
    arch = platform.machine().lower()
    target_platform = os.getenv("HARBOR_TARGET_PLATFORM", "")
    python_platform = platform.platform()

    # Determine platform category
    if arch in ["x86_64", "amd64"] or "amd64" in target_platform:
        platform_category = "amd64"
        platform_name = "AMD64"
        emoji = "🖥️"
        description = "Intel/AMD processors"
    elif arch in ["aarch64", "arm64"] or "arm64" in target_platform:
        platform_category = "arm64"
        platform_name = "ARM64"
        emoji = "🎯"
        description = "Apple Silicon, Pi 4, ARM servers"
    elif arch.startswith("arm") or "arm/v7" in target_platform:
        platform_category = "armv7"
        platform_name = "ARMv7"
        emoji = "🥧"
        description = "Raspberry Pi 3, older ARM"
    else:
        platform_category = "unknown"
        platform_name = "Unknown"
        emoji = "❓"
        description = "Unknown architecture"

    return {
        "arch": arch,
        "platform_category": platform_category,
        "platform_name": platform_name,
        "emoji": emoji,
        "description": description,
        "target_platform": target_platform,
        "python_platform": python_platform,
        "python_version": sys.version,
    }


def get_optimization_settings(platform_info: dict[str, Any]) -> dict[str, Any]:
    """
    Get platform-specific optimization settings.

    Args:
        platform_info: Platform information from detect_platform_info()

    Returns:
        Dict containing optimization settings
    """
    category = platform_info["platform_category"]

    if category == "amd64":
        return {
            "workers": "auto",
            "max_concurrent_updates": 5,
            "database_pool_size": 10,
            "log_retention_days": 30,
            "registry_cache_ttl": 1800,
            "enable_metrics": True,
            "registry_timeout": 30,
            "pull_timeout_seconds": 600,
            "update_timeout_seconds": 300,
            "cleanup_keep_images": 3,
            "memory_optimization": "standard",
            "features": "all_enabled",
            "description": "Full performance with all features enabled",
        }
    elif category == "arm64":
        return {
            "workers": 2,
            "max_concurrent_updates": 1,
            "database_pool_size": 5,
            "log_retention_days": 14,
            "registry_cache_ttl": 3600,
            "enable_metrics": True,
            "registry_timeout": 45,
            "pull_timeout_seconds": 900,
            "update_timeout_seconds": 600,
            "cleanup_keep_images": 2,
            "memory_optimization": "balanced",
            "features": "all_enabled",
            "description": "Balanced performance with full features",
        }
    elif category == "armv7":
        return {
            "workers": 1,
            "max_concurrent_updates": 1,
            "database_pool_size": 2,
            "log_retention_days": 7,
            "registry_cache_ttl": 7200,
            "enable_metrics": False,
            "registry_timeout": 60,
            "pull_timeout_seconds": 1800,
            "update_timeout_seconds": 900,
            "cleanup_keep_images": 1,
            "memory_optimization": "aggressive",
            "features": "essential_only",
            "description": "Memory-optimized for Raspberry Pi 3",
        }
    else:
        # Default to conservative settings for unknown platforms
        return {
            "workers": 1,
            "max_concurrent_updates": 1,
            "database_pool_size": 3,
            "log_retention_days": 14,
            "registry_cache_ttl": 3600,
            "enable_metrics": True,
            "registry_timeout": 45,
            "pull_timeout_seconds": 900,
            "update_timeout_seconds": 600,
            "cleanup_keep_images": 2,
            "memory_optimization": "balanced",
            "features": "standard",
            "description": "Conservative settings for unknown platform",
        }


def create_platform_env_file(optimization_settings: dict[str, Any]) -> None:
    """
    Create platform-specific environment file.

    Args:
        optimization_settings: Settings from get_optimization_settings()
    """
    env_file = Path("/app/.env.platform")

    with open(env_file, "w") as f:
        f.write("# Platform-specific optimizations\n")
        f.write(f"HARBOR_MAX_WORKERS={optimization_settings['workers']}\n")
        f.write(
            f"MAX_CONCURRENT_UPDATES={optimization_settings['max_concurrent_updates']}\n"
        )
        f.write(f"DATABASE_POOL_SIZE={optimization_settings['database_pool_size']}\n")
        f.write(f"LOG_RETENTION_DAYS={optimization_settings['log_retention_days']}\n")
        f.write(f"REGISTRY_CACHE_TTL={optimization_settings['registry_cache_ttl']}\n")
        f.write(
            f"ENABLE_METRICS={str(optimization_settings['enable_metrics']).lower()}\n"
        )
        f.write(f"REGISTRY_TIMEOUT={optimization_settings['registry_timeout']}\n")
        f.write(
            f"PULL_TIMEOUT_SECONDS={optimization_settings['pull_timeout_seconds']}\n"
        )
        f.write(
            f"UPDATE_TIMEOUT_SECONDS={optimization_settings['update_timeout_seconds']}\n"
        )
        f.write(f"CLEANUP_KEEP_IMAGES={optimization_settings['cleanup_keep_images']}\n")

        # Additional optimizations based on platform
        if optimization_settings["memory_optimization"] == "aggressive":
            f.write("PYTHONOPTIMIZE=1\n")
            f.write("MALLOC_TRIM_THRESHOLD_=100000\n")
            f.write("DISABLE_BACKGROUND_TASKS=false\n")
        elif optimization_settings["memory_optimization"] == "balanced":
            f.write("PYTHONOPTIMIZE=0\n")


def display_platform_info() -> None:
    """Display comprehensive platform information and recommendations."""
    platform_info = detect_platform_info()
    optimization_settings = get_optimization_settings(platform_info)

    print("🔍 Harbor Platform Detection")
    print("============================")
    print("")
    print(f"{platform_info['emoji']} Platform: {platform_info['platform_name']}")
    print(f"   Architecture: {platform_info['arch']}")
    print(f"   Target Platform: {platform_info['target_platform'] or 'auto-detected'}")
    print(f"   Description: {platform_info['description']}")
    print(f"   Python: {platform_info['python_platform']}")
    print("")

    print("⚙️ Applied Optimizations:")
    print(f"   Workers: {optimization_settings['workers']}")
    print(f"   Concurrent Updates: {optimization_settings['max_concurrent_updates']}")
    print(f"   Database Pool: {optimization_settings['database_pool_size']}")
    print(f"   Log Retention: {optimization_settings['log_retention_days']} days")
    print(f"   Registry Cache: {optimization_settings['registry_cache_ttl']}s")
    print(
        f"   Metrics: {'Enabled' if optimization_settings['enable_metrics'] else 'Disabled'}"
    )
    print(f"   Memory Mode: {optimization_settings['memory_optimization']}")
    print(f"   Features: {optimization_settings['features']}")
    print("")

    print(f"📝 Description: {optimization_settings['description']}")

    # Platform-specific recommendations
    if platform_info["platform_category"] == "armv7":
        print("")
        print("🥧 Raspberry Pi 3 Recommendations:")
        print("   • Use the provided Raspberry Pi Docker Compose file")
        print("   • Ensure adequate SD card space (8GB+ recommended)")
        print("   • Monitor memory usage with 'docker stats'")
        print("   • Consider using Docker socket proxy for enhanced security")
        print("   • Schedule updates during low-usage periods")
    elif platform_info["platform_category"] == "arm64":
        print("")
        print("🎯 ARM64 Recommendations:")
        print("   • Excellent performance on Raspberry Pi 4 (4GB+ RAM)")
        print("   • Native performance on Apple Silicon Macs")
        print("   • Consider enabling all features if resources allow")
        print("   • ARM64 cloud instances work great with Harbor")
    elif platform_info["platform_category"] == "amd64":
        print("")
        print("🖥️ AMD64 Recommendations:")
        print("   • Full performance and feature set available")
        print("   • Consider using PostgreSQL for larger deployments")
        print("   • Enable monitoring and metrics for observability")
        print("   • Use Docker Compose with all optional services")


def check_system_resources() -> dict[str, Any]:
    """
    Check available system resources and provide recommendations.

    Returns:
        Dict containing resource information and recommendations
    """
    import shutil

    # Get disk space
    try:
        disk_usage = shutil.disk_usage("/app/data")
        disk_free_gb = disk_usage.free / (1024**3)
        disk_total_gb = disk_usage.total / (1024**3)
        disk_used_percent = (
            (disk_usage.total - disk_usage.free) / disk_usage.total
        ) * 100
    except:
        disk_free_gb = 0
        disk_total_gb = 0
        disk_used_percent = 0

    # Check memory (approximate from /proc/meminfo if available)
    try:
        with open("/proc/meminfo") as f:
            meminfo = f.read()
        mem_total_kb = int(
            [line for line in meminfo.split("\n") if "MemTotal:" in line][0].split()[1]
        )
        mem_available_kb = int(
            [line for line in meminfo.split("\n") if "MemAvailable:" in line][
                0
            ].split()[1]
        )
        mem_total_gb = mem_total_kb / (1024**2)
        mem_available_gb = mem_available_kb / (1024**2)
        mem_used_percent = ((mem_total_kb - mem_available_kb) / mem_total_kb) * 100
    except:
        mem_total_gb = 0
        mem_available_gb = 0
        mem_used_percent = 0

    return {
        "disk_free_gb": disk_free_gb,
        "disk_total_gb": disk_total_gb,
        "disk_used_percent": disk_used_percent,
        "mem_total_gb": mem_total_gb,
        "mem_available_gb": mem_available_gb,
        "mem_used_percent": mem_used_percent,
    }


def display_resource_info() -> None:
    """Display system resource information and recommendations."""
    resources = check_system_resources()

    print("📊 System Resources:")
    print(
        f"   Disk: {resources['disk_free_gb']:.1f}GB free / {resources['disk_total_gb']:.1f}GB total ({resources['disk_used_percent']:.1f}% used)"
    )
    if resources["mem_total_gb"] > 0:
        print(
            f"   RAM: {resources['mem_available_gb']:.1f}GB available / {resources['mem_total_gb']:.1f}GB total ({resources['mem_used_percent']:.1f}% used)"
        )

    # Resource recommendations
    print("")
    if resources["disk_free_gb"] < 2:
        print(f"⚠️  Warning: Low disk space ({resources['disk_free_gb']:.1f}GB free)")
        print("   Consider reducing LOG_RETENTION_DAYS or CLEANUP_KEEP_IMAGES")
    elif resources["disk_free_gb"] < 5:
        print(f"💡 Note: Moderate disk space ({resources['disk_free_gb']:.1f}GB free)")
        print("   Current settings should work well")
    else:
        print(f"✅ Disk space: Excellent ({resources['disk_free_gb']:.1f}GB free)")

    if resources["mem_total_gb"] > 0:
        if resources["mem_total_gb"] < 1:
            print(f"⚠️  Warning: Low RAM ({resources['mem_total_gb']:.1f}GB total)")
            print("   Harbor may struggle with default settings")
            print("   Consider using ARMv7 optimizations even on other platforms")
        elif resources["mem_total_gb"] < 2:
            print(f"💡 Note: Limited RAM ({resources['mem_total_gb']:.1f}GB total)")
            print("   ARM optimizations are recommended")
        else:
            print(f"✅ RAM: Sufficient ({resources['mem_total_gb']:.1f}GB total)")


def main() -> None:
    """Main entry point for platform detection."""
    # Create platform environment file if we're in a container
    if os.path.exists("/app"):
        platform_info = detect_platform_info()
        optimization_settings = get_optimization_settings(platform_info)
        create_platform_env_file(optimization_settings)

        print("🗏️ Harbor Platform Detection & Optimization")
        print("=" * 50)
        print("")

        display_platform_info()
        print("")
        display_resource_info()
        print("")

        print("📋 Environment File Created:")
        print("   /app/.env.platform contains platform-specific optimizations")
        print("   These settings will be loaded automatically by Harbor")
        print("")

        # Show the created environment file
        env_file = Path("/app/.env.platform")
        if env_file.exists():
            print("🔧 Applied Settings:")
            with open(env_file) as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        print(f"   {line.strip()}")

        print("")
        print("🚀 Harbor is ready to start with platform optimizations!")
    else:
        # Running outside container - just show detection
        platform_info = detect_platform_info()
        optimization_settings = get_optimization_settings(platform_info)

        print("🔍 Platform Detection (Development Mode)")
        print("=" * 40)
        print("")

        display_platform_info()
        print("")

        print("💡 Recommended Docker Run Command:")
        if platform_info["platform_category"] == "armv7":
            print("   docker run -d -p 8080:8080 \\")
            print("     -e HARBOR_MAX_WORKERS=1 \\")
            print("     -e MAX_CONCURRENT_UPDATES=1 \\")
            print("     -e LOG_RETENTION_DAYS=7 \\")
            print("     -e ENABLE_METRICS=false \\")
            print("     -v /var/run/docker.sock:/var/run/docker.sock:ro \\")
            print("     ghcr.io/deusextaco/harbor:latest")
        elif platform_info["platform_category"] == "arm64":
            print("   docker run -d -p 8080:8080 \\")
            print("     -e HARBOR_MAX_WORKERS=2 \\")
            print("     -e MAX_CONCURRENT_UPDATES=1 \\")
            print("     -v /var/run/docker.sock:/var/run/docker.sock:ro \\")
            print("     ghcr.io/deusextaco/harbor:latest")
        else:
            print("   docker run -d -p 8080:8080 \\")
            print("     -v /var/run/docker.sock:/var/run/docker.sock:ro \\")
            print("     ghcr.io/deusextaco/harbor:latest")


if __name__ == "__main__":
    main()
