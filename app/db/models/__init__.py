# app/db/models/__init__.py
"""
Harbor Database Models

Import all models in the correct order to avoid circular dependencies.
This ensures all models are available when needed.
"""

# Import base first
from app.db.base import BaseModel
from app.db.models.api_key import APIKey
from app.db.models.audit import AuditLog
from app.db.models.container import Container
from app.db.models.job import Job
from app.db.models.policy import ContainerPolicy
from app.db.models.registry import Registry
from app.db.models.settings import SystemSettings

# Import models in dependency order
from app.db.models.user import User


__all__ = [
    "APIKey",
    "AuditLog",
    "BaseModel",
    "Container",
    "ContainerPolicy",
    "Job",
    "Registry",
    "SystemSettings",
    "User",
]
