# app/services/health.py
"""
Harbor Health Monitoring Service

Provides comprehensive health checks for all system components.
Part of M0 - Foundation milestone.
"""

import asyncio
import os
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from app.utils.logging import get_logger


logger = get_logger(__name__)


class HealthStatus(str, Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthCheck:
    """Base class for health checks."""

    def __init__(self, name: str, timeout: float = 5.0):
        """
        Initialize health check.

        Args:
            name: Name of the health check
            timeout: Timeout in seconds
        """
        self.name = name
        self.timeout = timeout

    async def check(self) -> dict[str, Any]:
        """
        Perform health check.

        Returns:
            Health check result
        """
        start_time = time.time()

        try:
            # Run check with timeout
            result = await asyncio.wait_for(self._perform_check(), timeout=self.timeout)

            duration_ms = (time.time() - start_time) * 1000

            return {
                "name": self.name,
                "status": result.get("status", HealthStatus.HEALTHY),
                "message": result.get("message", "Check passed"),
                "duration_ms": duration_ms,
                "timestamp": datetime.utcnow().isoformat(),
                "details": result.get("details", {}),
            }

        except TimeoutError:
            duration_ms = (time.time() - start_time) * 1000

            return {
                "name": self.name,
                "status": HealthStatus.UNHEALTHY,
                "message": f"Health check timed out after {self.timeout}s",
                "duration_ms": duration_ms,
                "timestamp": datetime.utcnow().isoformat(),
                "details": {},
            }

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            logger.error(f"Health check {self.name} failed", exc_info=True)

            return {
                "name": self.name,
                "status": HealthStatus.UNHEALTHY,
                "message": f"Health check failed: {e!s}",
                "duration_ms": duration_ms,
                "timestamp": datetime.utcnow().isoformat(),
                "details": {"error": str(e)},
            }

    async def _perform_check(self) -> dict[str, Any]:
        """
        Perform the actual health check.

        Returns:
            Check result with status, message, and optional details
        """
        raise NotImplementedError


class DatabaseHealthCheck(HealthCheck):
    """Database connectivity and performance check."""

    def __init__(self):
        super().__init__("database", timeout=3.0)

    async def _perform_check(self) -> dict[str, Any]:
        """Check database health."""
        try:
            from sqlalchemy import text

            from app.db.session import get_session

            async with get_session() as session:
                # Test basic connectivity
                start = time.time()
                result = await session.execute(text("SELECT 1"))
                query_time_ms = (time.time() - start) * 1000

                if result.scalar() != 1:
                    return {
                        "status": HealthStatus.UNHEALTHY,
                        "message": "Database query returned unexpected result",
                    }

                # Check performance
                if query_time_ms > 100:
                    return {
                        "status": HealthStatus.DEGRADED,
                        "message": f"Database response slow ({query_time_ms:.1f}ms)",
                        "details": {"query_time_ms": query_time_ms},
                    }

                return {
                    "status": HealthStatus.HEALTHY,
                    "message": "Database connection OK",
                    "details": {"query_time_ms": query_time_ms},
                }

        except ImportError:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": "Database module not available",
            }


class DiskSpaceHealthCheck(HealthCheck):
    """Disk space availability check."""

    def __init__(self, min_free_gb: float = 1.0):
        super().__init__("disk_space", timeout=2.0)
        self.min_free_gb = min_free_gb

    async def _perform_check(self) -> dict[str, Any]:
        """Check disk space."""
        try:
            import shutil

            # Check data directory
            data_dir = Path("data")
            if not data_dir.exists():
                data_dir = Path()

            total, used, free = shutil.disk_usage(data_dir)

            free_gb = free / (1024**3)
            used_percent = (used / total) * 100

            details = {
                "free_gb": round(free_gb, 2),
                "used_percent": round(used_percent, 1),
                "total_gb": round(total / (1024**3), 2),
            }

            if free_gb < self.min_free_gb:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": f"Low disk space: {free_gb:.1f}GB free",
                    "details": details,
                }

            if used_percent > 90:
                return {
                    "status": HealthStatus.DEGRADED,
                    "message": f"Disk usage high: {used_percent:.1f}%",
                    "details": details,
                }

            return {
                "status": HealthStatus.HEALTHY,
                "message": f"Sufficient disk space: {free_gb:.1f}GB free",
                "details": details,
            }

        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Could not check disk space: {e!s}",
            }


class MemoryHealthCheck(HealthCheck):
    """Memory usage health check."""

    def __init__(self, max_usage_percent: float = 90.0):
        super().__init__("memory", timeout=2.0)
        self.max_usage_percent = max_usage_percent

    async def _perform_check(self) -> dict[str, Any]:
        """Check memory usage."""
        try:
            import psutil

            memory = psutil.virtual_memory()

            details = {
                "used_percent": round(memory.percent, 1),
                "available_mb": round(memory.available / (1024**2), 1),
                "total_mb": round(memory.total / (1024**2), 1),
            }

            if memory.percent > self.max_usage_percent:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": f"High memory usage: {memory.percent:.1f}%",
                    "details": details,
                }

            if memory.percent > 80:
                return {
                    "status": HealthStatus.DEGRADED,
                    "message": f"Elevated memory usage: {memory.percent:.1f}%",
                    "details": details,
                }

            return {
                "status": HealthStatus.HEALTHY,
                "message": f"Memory usage normal: {memory.percent:.1f}%",
                "details": details,
            }

        except ImportError:
            # psutil not available, basic check
            return {
                "status": HealthStatus.HEALTHY,
                "message": "Memory check unavailable (psutil not installed)",
                "details": {},
            }


class DockerHealthCheck(HealthCheck):
    """Docker socket connectivity check."""

    def __init__(self):
        super().__init__("docker", timeout=5.0)

    async def _perform_check(self) -> dict[str, Any]:
        """Check Docker availability."""
        docker_host = os.environ.get("DOCKER_HOST", "/var/run/docker.sock")

        if docker_host.startswith("tcp://"):
            # Socket proxy check
            return {
                "status": HealthStatus.HEALTHY,
                "message": f"Docker socket proxy configured: {docker_host}",
                "details": {"docker_host": docker_host},
            }

        # Direct socket check
        socket_path = Path(docker_host)

        if not socket_path.exists():
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Docker socket not found: {docker_host}",
                "details": {"docker_host": docker_host},
            }

        if not os.access(socket_path, os.R_OK):
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Docker socket not readable: {docker_host}",
                "details": {"docker_host": docker_host},
            }

        return {
            "status": HealthStatus.HEALTHY,
            "message": "Docker socket accessible",
            "details": {"docker_host": docker_host},
        }


class HealthMonitor:
    """
    Central health monitoring service.

    Aggregates health checks from all components.
    """

    def __init__(self):
        """Initialize health monitor with default checks."""
        self.checks: list[HealthCheck] = [
            DatabaseHealthCheck(),
            DiskSpaceHealthCheck(),
            MemoryHealthCheck(),
            DockerHealthCheck(),
        ]

    async def get_health(self) -> dict[str, Any]:
        """
        Get overall system health.

        Returns:
            Comprehensive health status
        """
        # Run all checks concurrently
        results = await asyncio.gather(
            *[check.check() for check in self.checks], return_exceptions=True
        )

        # Process results
        checks = {}
        unhealthy_count = 0
        degraded_count = 0

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Health check failed with exception: {result}")
                continue

            # Type guard - result is now known to be dict[str, Any]
            if isinstance(result, dict):
                check_name = result["name"]
                checks[check_name] = result

                if result["status"] == HealthStatus.UNHEALTHY:
                    unhealthy_count += 1
                elif result["status"] == HealthStatus.DEGRADED:
                    degraded_count += 1

        # Determine overall status
        if unhealthy_count > 0:
            overall_status = HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks,
            "summary": {
                "healthy": len(checks) - unhealthy_count - degraded_count,
                "degraded": degraded_count,
                "unhealthy": unhealthy_count,
                "total": len(checks),
            },
        }

    async def get_readiness(self) -> dict[str, Any]:
        """
        Check if system is ready to serve requests.

        Returns:
            Readiness status
        """
        health = await self.get_health()

        # System is ready if database is healthy
        db_check = health["checks"].get("database", {})
        db_healthy = db_check.get("status") == HealthStatus.HEALTHY

        return {
            "ready": db_healthy and health["status"] != HealthStatus.UNHEALTHY,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "database": db_healthy,
                "system": health["status"] != HealthStatus.UNHEALTHY,
            },
        }


# Global health monitor instance
health_monitor = HealthMonitor()
