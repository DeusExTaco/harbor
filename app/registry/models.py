# app/registry/models.py
"""
Harbor Registry Models

Data models for registry operations.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class ImageManifest:
    """Container image manifest."""

    digest: str
    media_type: str
    size: int
    created_at: datetime | None = None
    architecture: str | None = None
    os: str | None = None
    layers: list[dict[str, Any]] = None

    def __post_init__(self):
        """Initialize layers if not provided."""
        if self.layers is None:
            self.layers = []


@dataclass
class ImageReference:
    """Parsed image reference."""

    registry: str
    namespace: str | None
    repository: str
    tag: str | None
    digest: str | None

    @property
    def full_name(self) -> str:
        """Get full image name without tag/digest."""
        parts = [self.registry]
        if self.namespace:
            parts.append(self.namespace)
        parts.append(self.repository)
        return "/".join(parts)

    @property
    def full_reference(self) -> str:
        """Get full image reference with tag or digest."""
        ref = self.full_name
        if self.tag:
            ref += f":{self.tag}"
        if self.digest:
            ref += f"@{self.digest}"
        return ref


@dataclass
class RegistryCredentials:
    """Registry authentication credentials."""

    username: str
    password: str
    auth_type: str = "basic"
    token: str | None = None
    expires_at: datetime | None = None
