"""
Request logging and audit trail middleware.

Logs all requests for audit and debugging purposes.
"""

import time
from collections.abc import Awaitable, Callable
from typing import ClassVar

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.config import get_settings
from app.utils.logging import get_correlation_id, get_logger


logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests for audit trail and debugging."""

    SENSITIVE_PATHS: ClassVar[list[str]] = [
        "/api/v1/auth/login",
        "/api/v1/auth/change-password",
    ]

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Log request and response information."""

        # Get correlation ID from request state (set by CorrelationMiddleware)
        # or from context if available
        if hasattr(request.state, "correlation_id"):
            request_id = request.state.correlation_id
        else:
            # Fallback to getting from context or generating new
            request_id = get_correlation_id()
            request.state.correlation_id = request_id
            request.state.request_id = request_id

        # Get client info
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path

        # Check if path contains sensitive data
        is_sensitive = any(path.startswith(p) for p in self.SENSITIVE_PATHS)

        # Log request (don't log body for sensitive endpoints)
        start_time = time.time()

        if not is_sensitive:
            # Use standard logging format with extra dict
            logger.info(
                f"Request started - ID: {request_id}, Method: {method}, Path: {path}, IP: {client_ip}",
                extra={
                    "request_id": request_id,
                    "correlation_id": request_id,
                    "method": method,
                    "path": path,
                    "client_ip": client_ip,
                    "user_agent": request.headers.get("user-agent", "unknown"),
                },
            )
        else:
            logger.info(
                f"Request started (sensitive endpoint) - ID: {request_id}, Method: {method}, Path: {path}",
                extra={
                    "request_id": request_id,
                    "correlation_id": request_id,
                    "method": method,
                    "path": path,
                    "client_ip": client_ip,
                },
            )

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"Request failed with exception - ID: {request_id}, Duration: {duration_ms}ms, Error: {e!s}",
                extra={
                    "request_id": request_id,
                    "correlation_id": request_id,
                    "duration_ms": duration_ms,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

        # Log response
        duration_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"Request completed - ID: {request_id}, Status: {response.status_code}, Duration: {duration_ms}ms",
            extra={
                "request_id": request_id,
                "correlation_id": request_id,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        # Add request ID to response headers (if not already added by CorrelationMiddleware)
        if "X-Request-ID" not in response.headers:
            response.headers["X-Request-ID"] = request_id
        if "X-Correlation-ID" not in response.headers:
            response.headers["X-Correlation-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms}ms"

        return response
