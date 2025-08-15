"""
Harbor Container Updater - Main Application Entry Point

This module provides the FastAPI application factory for Harbor.
Currently implements M0 milestone - Foundation phase.

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
from typing import Any

from fastapi import FastAPI

# Import Harbor version info
from app import __description__, __milestone__, __status__, __version__


def create_app() -> FastAPI:
    """
    Application factory for Harbor Container Updater.

    Returns:
        FastAPI: Configured FastAPI application instance

    Note:
        This is a minimal M0 implementation. Full functionality will be
        added in subsequent milestones.
    """

    # Get deployment profile from environment
    deployment_profile = os.getenv("HARBOR_MODE", "homelab")
    # log_level = os.getenv("LOG_LEVEL", "INFO")

    app = FastAPI(
        title="Harbor Container Updater",
        description=__description__,
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Health check endpoint (required for Docker health checks)
    @app.get("/healthz")  # type: ignore[misc]
    def health_check() -> dict[str, Any]:
        """Basic health check endpoint for container orchestration."""
        return {
            "status": "healthy",
            "version": __version__,
            "milestone": __milestone__,
            "deployment_profile": deployment_profile,
            "python_version": sys.version,
        }

    # Readiness check endpoint
    @app.get("/readyz")  # type: ignore[misc]
    def readiness_check() -> dict[str, Any]:
        """Readiness check endpoint for container orchestration."""
        return {
            "ready": True,
            "version": __version__,
            "milestone": __milestone__,
            "status": __status__,
        }

    # Basic info endpoint
    @app.get("/")  # type: ignore[misc]
    def root() -> dict[str, Any]:
        """Root endpoint with Harbor information."""
        return {
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

    # Version endpoint
    @app.get("/version")  # type: ignore[misc]
    def version_info() -> dict[str, Any]:
        """Version information endpoint."""
        return {
            "version": __version__,
            "milestone": __milestone__,
            "status": __status__,
            "python_version": sys.version,
            "deployment_profile": deployment_profile,
        }

    return app


def main() -> None:
    """
    Main entry point for Harbor CLI.

    TODO: Implement CLI interface in later milestones.
    Currently just shows Harbor information.
    """
    print(f"Harbor Container Updater v{__version__}")
    print(f"Status: {__status__} (M0 Milestone)")
    print(f"Description: {__description__}")
    print()
    print("To run Harbor:")
    print("  uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8080")
    print()
    print("For development:")
    print("  uvicorn app.main:create_app --factory --reload")


if __name__ == "__main__":
    main()
