"""
Harbor Container Updater - Main Application Entry Point

This module provides the FastAPI application factory for Harbor.
Currently implements M0 milestone - Foundation phase with configuration system.

TODO: Implement full Harbor functionality according to milestone roadmap:
- M1: Container Discovery & Registry Integration
- M2: Safe Update Engine with Rollback
- M3: Automation & Scheduling
- M4: Observability & Monitoring
- M5: Production Readiness
- M6: Release & Launch
"""

import os
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

# Import Harbor version info
from app import __description__, __milestone__, __status__, __version__


# Import configuration system (M0 implementation)
try:
    from app.config import (
        get_config_summary,
        get_settings,
        validate_runtime_requirements,
    )

    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[Any]:
    """
    Application lifespan manager for startup and shutdown tasks.

    Args:
        app: FastAPI application instance
    """
    # Startup tasks
    print(f"🛳️ Starting Harbor Container Updater v{__version__}")
    print(f"🎯 Milestone: {__milestone__} ({__status__})")

    if CONFIG_AVAILABLE:
        try:
            settings = get_settings()
            config_summary = get_config_summary()

            print(f"⚙️ Profile: {config_summary['deployment_profile']}")
            print(f"🗃️ Database: {config_summary['database_type']}")
            print(f"📊 Log Level: {config_summary['log_level']}")

            # Validate runtime requirements
            errors = validate_runtime_requirements()
            if errors:
                print("⚠️ Configuration issues detected:")
                for error in errors:
                    print(f"  - {error}")
            else:
                print("✅ Configuration validated successfully")

            # Show data directory
            print(f"📁 Data directory: {settings.data_dir}")

        except Exception as e:
            print(f"⚠️ Configuration system error: {e}")
    else:
        print("⚠️ Configuration system not available - using defaults")

    print("🌐 Starting server...")

    yield

    # Shutdown tasks
    print("🛑 Shutting down Harbor Container Updater...")


def create_app() -> FastAPI:
    """
    Application factory for Harbor Container Updater.

    Returns:
        FastAPI: Configured FastAPI application instance

    Note:
        This is a minimal M0 implementation. Full functionality will be
        added in subsequent milestones.
    """

    # Get configuration if available
    if CONFIG_AVAILABLE:
        try:
            settings = get_settings()
            deployment_profile = settings.deployment_profile.value
            debug_mode = settings.debug
        except Exception:
            deployment_profile = os.getenv("HARBOR_MODE", "homelab")
            debug_mode = False
    else:
        deployment_profile = os.getenv("HARBOR_MODE", "homelab")
        debug_mode = False

    app = FastAPI(
        title="Harbor Container Updater",
        description=__description__,
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        debug=debug_mode,
        lifespan=lifespan,
    )

    # Health check endpoint (required for Docker health checks)
    @app.get("/healthz")
    def health_check() -> dict[str, Any]:
        """Basic health check endpoint for container orchestration."""
        try:
            health_data: dict[str, Any] = {
                "status": "healthy",
                "version": __version__,
                "milestone": __milestone__,
                "deployment_profile": deployment_profile,
                "python_version": sys.version,
            }

            # Add configuration info if available
            if CONFIG_AVAILABLE:
                try:
                    settings = get_settings()
                    health_data.update(
                        {
                            "database_type": settings.database.database_type.value,
                            "features_enabled": {
                                "auto_discovery": settings.features.enable_auto_discovery,
                                "metrics": settings.features.enable_metrics,
                                "health_checks": settings.features.enable_health_checks,
                            },
                        }
                    )
                except Exception:  # nosec B110 - Non-critical configuration error handling
                    # Gracefully handle configuration errors in health check
                    # This is non-critical - health check can still return basic info
                    health_data["config_status"] = "error"

            # Add timestamp (basic implementation for M0)
            import datetime

            health_data["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"

            return health_data

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "version": __version__,
                "milestone": __milestone__,
            }

    # Readiness check endpoint
    @app.get("/readyz")
    def readiness_check() -> dict[str, Any]:
        """Readiness check endpoint for container orchestration."""
        ready_data: dict[str, Any] = {
            "ready": True,
            "version": __version__,
            "milestone": __milestone__,
            "status": __status__,
        }

        # Check configuration availability
        if CONFIG_AVAILABLE:
            try:
                settings = get_settings()
                errors = validate_runtime_requirements()
                ready_data.update(
                    {
                        "config_valid": len(errors) == 0,
                        "deployment_profile": settings.deployment_profile.value,
                    }
                )
                if errors:
                    ready_data["ready"] = False
                    ready_data["config_errors"] = errors
            except Exception as e:
                ready_data["ready"] = False
                ready_data["config_error"] = str(e)

        return ready_data

    # Basic info endpoint
    @app.get("/")
    def root() -> dict[str, Any]:
        """Root endpoint with Harbor information."""
        root_data: dict[str, Any] = {
            "name": "Harbor Container Updater",
            "version": __version__,
            "description": __description__,
            "milestone": __milestone__,
            "status": __status__,
            "deployment_profile": deployment_profile,
            "documentation": "/docs",
            "health": "/healthz",
            "readiness": "/readyz",
        }

        # Add configuration summary if available
        if CONFIG_AVAILABLE:
            try:
                config_summary = get_config_summary()
                root_data["configuration"] = {
                    "database_type": config_summary["database_type"],
                    "auto_discovery": config_summary["auto_discovery_enabled"],
                    "simple_mode": config_summary.get("simple_mode_enabled", False),
                }
            except Exception:
                root_data["configuration"] = {"status": "error"}

        return root_data

    # Version endpoint
    @app.get("/version")
    def version_info() -> dict[str, Any]:
        """Version information endpoint."""
        version_data: dict[str, Any] = {
            "version": __version__,
            "milestone": __milestone__,
            "status": __status__,
            "python_version": sys.version,
            "deployment_profile": deployment_profile,
        }

        # Add build information if available
        if CONFIG_AVAILABLE:
            try:
                settings = get_settings()
                version_data.update(
                    {
                        "app_name": settings.app_name,
                        "debug_mode": settings.debug,
                    }
                )
            except Exception:
                pass

        return version_data

    # Configuration endpoint (for debugging)
    if debug_mode and CONFIG_AVAILABLE:

        @app.get("/config")
        def config_info() -> dict[str, Any]:
            """Configuration information endpoint (debug only)."""
            try:
                return get_config_summary()
            except Exception as e:
                return {"error": str(e)}

    return app


def main() -> None:
    """
    Main entry point for Harbor CLI.

    TODO: Implement CLI interface in later milestones.
    Currently just shows Harbor information.
    """
    print(f"🛳️ Harbor Container Updater v{__version__}")
    print(f"🎯 Status: {__status__} ({__milestone__} Milestone)")
    print(f"📖 Description: {__description__}")
    print()

    # Show configuration info if available
    if CONFIG_AVAILABLE:
        try:
            settings = get_settings()
            print("⚙️ Current Configuration:")
            print(f"  Profile: {settings.deployment_profile.value}")
            print(f"  Database: {settings.database.database_type.value}")
            print(f"  Data directory: {settings.data_dir}")
            print(f"  Debug mode: {settings.debug}")
            print()
        except Exception as e:
            print(f"⚠️ Configuration error: {e}")
            print()

    print("🚀 To run Harbor:")
    print("  uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8080")
    print()
    print("🔧 For development:")
    print("  uvicorn app.main:create_app --factory --reload")
    print()
    print("📚 Documentation:")
    print("  http://localhost:8080/docs (when running)")


if __name__ == "__main__":
    main()
