# app/registry/resolver.py
"""
Harbor Image Reference Resolver

Parse and resolve image references.
"""

import re
from typing import Optional

from app.registry.models import ImageReference
from app.utils.logging import get_logger


logger = get_logger(__name__)


class ImageResolver:
    """Parse and resolve image references."""

    # Default registry if none specified
    DEFAULT_REGISTRY = "docker.io"
    DEFAULT_TAG = "latest"

    # Regex for parsing image references
    IMAGE_REGEX = re.compile(
        r"^(?:(?P<registry>[^/]+\.[^/]+)/)?"
        r"(?:(?P<namespace>[^/]+)/)?"
        r"(?P<repository>[^:@]+)"
        r"(?::(?P<tag>[^@]+))?"
        r"(?:@(?P<digest>sha256:[a-f0-9]{64}))?$"
    )

    @classmethod
    def parse(cls, image_ref: str) -> ImageReference:
        """
        Parse an image reference string.

        Args:
            image_ref: Image reference (e.g., "nginx:latest", "gcr.io/project/image:tag")

        Returns:
            Parsed ImageReference

        Raises:
            ValueError: If image reference is invalid
        """
        match = cls.IMAGE_REGEX.match(image_ref)
        if not match:
            raise ValueError(f"Invalid image reference: {image_ref}")

        groups = match.groupdict()

        # Apply defaults
        registry = groups.get("registry") or cls.DEFAULT_REGISTRY
        namespace = groups.get("namespace")
        repository = groups["repository"]
        tag = groups.get("tag") or (
            cls.DEFAULT_TAG if not groups.get("digest") else None
        )
        digest = groups.get("digest")

        # Special case for Docker Hub official images
        if registry == cls.DEFAULT_REGISTRY and not namespace:
            namespace = "library"

        return ImageReference(
            registry=registry,
            namespace=namespace,
            repository=repository,
            tag=tag,
            digest=digest,
        )
