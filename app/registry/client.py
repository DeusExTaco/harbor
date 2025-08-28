# app/registry/client.py
"""
Harbor Registry Client

OCI Registry v2 client implementation.
M0: Stub implementation
M1: Full implementation with Docker Hub, GHCR, etc.
"""

from typing import Any

from app.utils.logging import get_logger


logger = get_logger(__name__)


class RegistryClient:
    """
    Client for interacting with OCI-compliant container registries.

    This is a stub implementation for M0. Full implementation
    will be completed in M1 (Discovery & Registry Integration).
    """

    def __init__(self, registry_url: str = "https://registry-1.docker.io"):
        """
        Initialize registry client.

        Args:
            registry_url: Base URL of the registry
        """
        self.registry_url = registry_url
        logger.info(f"Registry client initialized (stub) for {registry_url}")

    async def get_manifest(self, image: str, tag: str) -> dict[str, Any] | None:
        """
        Get manifest for an image:tag.

        Args:
            image: Image name (e.g., "library/nginx")
            tag: Image tag (e.g., "latest")

        Returns:
            Manifest data or None

        Note:
            Stub implementation - returns None
        """
        logger.debug(f"get_manifest called for {image}:{tag} (stub)")
        # TODO: Implement in M1
        return None

    async def get_digest(self, image: str, tag: str) -> str | None:
        """
        Get digest for an image:tag.

        Args:
            image: Image name
            tag: Image tag

        Returns:
            Digest string or None

        Note:
            Stub implementation - returns None
        """
        logger.debug(f"get_digest called for {image}:{tag} (stub)")
        # TODO: Implement in M1
        return None

    async def list_tags(self, image: str) -> list[str]:
        """
        List available tags for an image.

        Args:
            image: Image name

        Returns:
            List of available tags

        Note:
            Stub implementation - returns empty list
        """
        logger.debug(f"list_tags called for {image} (stub)")
        # TODO: Implement in M1
        return []
