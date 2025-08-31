# app/api/health.py
"""
Harbor Health Check API Endpoints

Provides health and readiness endpoints for monitoring.
Part of M0 - Foundation milestone.
"""

from typing import Any  # ADD THIS IMPORT

from fastapi import APIRouter, Response

from app.services.health import HealthStatus, health_monitor
from app.utils.logging import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("/healthz")
async def health_check() -> dict[str, Any]:
    """
    Liveness probe endpoint.

    Simple check that the application is running.
    Always returns 200 if the app is up.
    """
    return {
        "status": "ok",
        "service": "harbor",
    }


@router.get("/health")
async def detailed_health(response: Response) -> dict[str, Any]:
    """
    Detailed health check endpoint.

    Returns comprehensive health information for all components.
    Sets appropriate HTTP status based on health.
    """
    health = await health_monitor.get_health()

    # Set HTTP status based on health
    if health["status"] == HealthStatus.UNHEALTHY:
        response.status_code = 503
    elif health["status"] == HealthStatus.DEGRADED:
        response.status_code = 200  # Still operational but degraded

    return health


@router.get("/readyz")
async def readiness_check(response: Response) -> dict[str, Any]:
    """
    Readiness probe endpoint.

    Indicates if the service is ready to accept requests.
    Used by orchestrators to determine when to route traffic.
    """
    readiness = await health_monitor.get_readiness()

    if not readiness["ready"]:
        response.status_code = 503

    return readiness
