# app/auth/__init__.py
"""
Harbor Authentication Module

Provides secure authentication and authorization for Harbor.
Implements M0 milestone authentication requirements.
"""

from app.auth.api_keys import generate_api_key, hash_api_key, validate_api_key
from app.auth.csrf import get_csrf_protection
from app.auth.dependencies import (
    AdminUser,
    CurrentUser,
    get_admin_user,
    get_current_active_user,
    get_current_user,
)
from app.auth.manager import AuthenticationManager, get_auth_manager
from app.auth.password import (
    generate_password,
    hash_password,
    validate_password,
    verify_password,
)
from app.auth.sessions import SessionData, SessionManager, get_session_manager


__all__ = [
    # Manager
    "AuthenticationManager",
    "get_auth_manager",
    # Password utilities
    "hash_password",
    "verify_password",
    "validate_password",
    "generate_password",
    # Sessions
    "SessionManager",
    "SessionData",
    "get_session_manager",
    # API keys
    "generate_api_key",
    "hash_api_key",
    "validate_api_key",
    # CSRF
    "get_csrf_protection",
    # Dependencies
    "get_current_user",
    "get_current_active_user",
    "get_admin_user",
    "CurrentUser",
    "AdminUser",
]
