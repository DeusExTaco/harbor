# app/middleware/__init__.py
"""
Harbor Middleware Components

Additional middleware for request processing and security.
"""

from app.middleware.authentication import AuthenticationMiddleware
from app.middleware.correlation import CorrelationMiddleware
from app.middleware.cors import setup_cors
from app.middleware.request_logging import RequestLoggingMiddleware


__all__ = [
    "AuthenticationMiddleware",
    "CorrelationMiddleware",
    "RequestLoggingMiddleware",
    "setup_cors",
]
