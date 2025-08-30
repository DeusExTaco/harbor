# app/middleware/cors.py
"""
CORS configuration for Harbor.

Provides profile-aware CORS setup.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import DeploymentProfile, get_settings
from app.core.security import SecurityConfig
from app.utils.logging import get_logger


logger = get_logger(__name__)


def setup_cors(app: FastAPI) -> None:
    """
    Configure CORS middleware for the application.

    Args:
        app: FastAPI application instance
    """
    settings = get_settings()
    security_config = SecurityConfig.get_security_config()
    cors_config = security_config["cors"]

    if not cors_config["enabled"]:
        logger.info("CORS is disabled")
        return

    # Fix: Use proper logging format with extra dict
    origins_preview = (
        cors_config["origins"][:3]
        if len(cors_config["origins"]) > 3
        else cors_config["origins"]
    )
    logger.info(
        f"Setting up CORS for {settings.deployment_profile.value} profile",
        extra={
            "origins": origins_preview,
            "profile": settings.deployment_profile.value,
        },
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_config["origins"],
        allow_credentials=cors_config["allow_credentials"],
        allow_methods=cors_config["allow_methods"],
        allow_headers=cors_config["allow_headers"],
    )
