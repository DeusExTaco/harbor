"""
Harbor Correlation ID Middleware

Enhances existing request logging with correlation ID support.
Works alongside RequestLoggingMiddleware.
"""

import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.utils.logging import get_logger, set_correlation_id


logger = get_logger(__name__)


class CorrelationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add correlation IDs to all requests.
    Designed to work with existing RequestLoggingMiddleware.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with correlation ID."""

        # Extract correlation ID from headers or generate new one
        correlation_id = (
            request.headers.get("X-Correlation-ID")
            or request.headers.get("X-Request-ID")
            or str(uuid.uuid4())
        )

        # Store in request state for other middleware and endpoints
        request.state.correlation_id = correlation_id
        request.state.request_id = correlation_id  # For compatibility

        # Set correlation ID in context for all logs in this request
        set_correlation_id(correlation_id)

        # Process request
        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Request-ID"] = correlation_id

        # Clear correlation ID after request (important for context cleanup)
        set_correlation_id("")

        return response
