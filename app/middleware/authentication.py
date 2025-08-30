# app/middleware/authentication.py
"""
Authentication enforcement middleware.

Enforces authentication on protected routes.
"""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.config import get_settings
from app.core.security import SecurityConfig
from app.utils.logging import get_logger


logger = get_logger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce authentication on protected routes.

    Note: This is a placeholder for future session-based auth.
    Current auth is handled via dependencies.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings()
        self.public_paths = SecurityConfig.get_public_paths()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request and check authentication if needed."""

        # Check if path is public
        path = request.url.path
        is_public = any(path == p or path.startswith(p) for p in self.public_paths)

        if is_public:
            # Public path, no auth needed
            return await call_next(request)

        # TODO: M0 - Implement session checking
        # For now, auth is handled by dependencies

        # Add request metadata
        request.state.auth_required = True

        return await call_next(request)
