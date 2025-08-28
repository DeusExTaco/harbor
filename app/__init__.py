"""
Harbor Container Updater

A modern, open-source Docker container updater designed for both home lab
enthusiasts and enterprise environments.

Copyright (c) 2024 Harbor Contributors
Licensed under the MIT License
"""

from typing import TYPE_CHECKING, Any


__version__ = "0.1.0-alpha.2"
__description__ = "Automated Docker container updates for home labs and enterprises"
__author__ = "Harbor Contributors"
__license__ = "MIT"

# Harbor feature information
__features__ = {
    "home_lab_optimized": True,
    "zero_config": True,
    "enterprise_ready": True,
    "multi_architecture": True,
    "privacy_first": True,
}

# Deployment profile information
__profiles__ = ["homelab", "development", "staging", "production"]

# Development milestone (M0 = Foundation)
__milestone__ = "M0"
__status__ = "Pre-Alpha"

# Import key components for easy access
try:
    from app.config import (
        DeploymentProfile,  # noqa: F401
        get_config_summary,
        get_settings,
        is_development,
        is_homelab,
        is_production,
    )

    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False

    if TYPE_CHECKING:
        # For type checking, import the actual types
        from app.config import HarborSettings
    else:
        # At runtime, create a dummy class
        class HarborSettings:  # type: ignore[no-redef]
            pass

    # Define fallback functions with matching signatures
    def get_settings() -> Any:  # type: ignore[misc]
        """Fallback function when config is not available."""
        return None

    def get_config_summary() -> dict[str, Any]:
        """Fallback function when config is not available."""
        return {}

    def is_development() -> bool:
        """Fallback function when config is not available."""
        return False

    def is_production() -> bool:
        """Fallback function when config is not available."""
        return False

    def is_homelab() -> bool:
        """Fallback function when config is not available."""
        return True


# Export public API
__all__ = [
    "CONFIG_AVAILABLE",
    "__author__",
    "__description__",
    "__features__",
    "__license__",
    "__milestone__",
    "__profiles__",
    "__status__",
    "__version__",
    "get_config_summary",
    "get_settings",
    "is_development",
    "is_homelab",
    "is_production",
]

# Only add DeploymentProfile to exports if config is available
if CONFIG_AVAILABLE:
    __all__.insert(1, "DeploymentProfile")  # Insert after CONFIG_AVAILABLE


def get_version() -> str:
    """Get the Harbor version string."""
    return __version__


def get_app_info() -> dict[str, Any]:
    """Get application information."""
    return {
        "name": "Harbor Container Updater",
        "version": __version__,
        "author": __author__,
        "license": __license__,
        "description": __description__,
        "milestone": __milestone__,
        "status": __status__,
        "features": __features__,
        "profiles": __profiles__,
        "project_url": "https://github.com/DeusExTaco/harbor",
        "docs_url": "https://harbor-docs.dev",
    }
