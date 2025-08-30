# app/api/dependencies/__init__.py
"""
Harbor API Dependencies

Common dependencies for FastAPI routes.
"""

from app.api.dependencies.auth import (
    api_key_header,
    get_current_user,
    http_basic,
    require_admin,
    require_auth,
)
from app.api.dependencies.rate_limit import check_rate_limit, endpoint_limiter


__all__ = [
    # Auth dependencies
    "api_key_header",
    "http_basic",
    "get_current_user",
    "require_auth",
    "require_admin",
    # Rate limit dependencies
    "check_rate_limit",
    "endpoint_limiter",
]
