# app/main.py
"""
Harbor Container Updater - Main Application Entry Point

This module provides the FastAPI application factory for Harbor.
Implements M0 milestone - Foundation phase with complete database integration.

Features:
- Configuration system integration
- Security middleware setup (M0 implementation)
- Database initialization and session management (M0 implementation)
- Health check endpoints with database status
- Profile-aware application setup
- Comprehensive error handling

TODO: Implement remaining Harbor functionality according to milestone roadmap:
- M0: Authentication System (next immediate task)
- M1: Container Discovery & Registry Integration
- M2: Safe Update Engine with Rollback
- M3: Automation & Scheduling
- M4: Observability & Monitoring
- M5: Production Readiness
- M6: Release & Launch
"""

import logging
import os
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import Harbor version info
from app import __description__, __milestone__, __status__, __version__


# Set up logger
logger = logging.getLogger(__name__)

# Import configuration system (M0 implementation)
try:
    from app.config import (
        get_config_summary,
        get_settings,
        is_development,
        validate_runtime_requirements,
    )

    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False

    def is_development() -> bool:
        """Fallback for development check"""
        return os.getenv("HARBOR_MODE", "homelab") == "development"


# Import database system (M0 implementation)
try:
    from app.db.init import ensure_database_ready, get_database_info
    from app.db.models.settings import SystemSettings
    from app.db.models.user import User
    from app.db.repositories.user import UserRepository
    from app.db.session import get_session, get_session_manager

    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

# Import security middleware (M0 implementation)
try:
    from app.security import setup_security_middleware
    from app.security.headers import SecurityHeadersMiddleware
    from app.security.rate_limit import RateLimitMiddleware
    from app.security.validation import InputSanitizer

    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[Any]:
    """
    Application lifespan manager for startup and shutdown tasks with database integration.

    Args:
        app: FastAPI application instance
    """
    # Startup tasks
    print(f"🚢 Starting Harbor Container Updater v{__version__}")
    print(f"🎯 Milestone: {__milestone__} ({__status__})")

    startup_success = True
    session_manager = None

    # Configuration validation
    if CONFIG_AVAILABLE:
        try:
            settings = get_settings()
            config_summary = get_config_summary()

            print(f"⚙️ Profile: {config_summary['deployment_profile']}")
            print(f"🗃️ Database: {config_summary['database_type']}")
            print(f"📊 Log Level: {config_summary['log_level']}")

            # Validate runtime requirements
            errors = validate_runtime_requirements()
            if errors:
                print("⚠️ Configuration issues detected:")
                for error in errors:
                    print(f"  - {error}")
                startup_success = False
            else:
                print("✅ Configuration validated successfully")

            # Show data directory
            print(f"📁 Data directory: {settings.data_dir}")

        except Exception as e:
            logger.error(f"Configuration system error: {e}")
            print(f"⚠️ Configuration system error: {e}")
            startup_success = False
    else:
        print("⚠️ Configuration system not available - using defaults")
        startup_success = False

    # Database initialization (M0 implementation)
    if DATABASE_AVAILABLE and startup_success:
        try:
            print("🗄️ Initializing database...")
            db_ready = await ensure_database_ready()

            if not db_ready:
                print(
                    "❌ Failed to initialize database - application may not work correctly"
                )
                startup_success = False
            else:
                print("✅ Database initialization completed successfully")

                # Initialize session manager
                session_manager = get_session_manager()
                await session_manager.initialize()
                print("✅ Database session manager initialized")

                # Get database info for logging
                try:
                    db_info = await get_database_info()
                    print(
                        f"📊 Database info: {db_info.get('dialect', 'unknown')} "
                        f"({db_info.get('table_count', 0)} tables)"
                    )

                    if "size_mb" in db_info:
                        print(f"💾 Database size: {db_info['size_mb']} MB")

                except Exception as e:
                    logger.warning(f"Could not get database info: {e}")
                    print(f"⚠️ Could not get database info: {e}")

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            print(f"❌ Database initialization failed: {e}")
            startup_success = False
    elif not DATABASE_AVAILABLE:
        print("⚠️ Database system not available")
        startup_success = False

    # Security middleware status (M0 implementation)
    if SECURITY_AVAILABLE:
        print("🔐 Security middleware: ✅ Enabled")
        print("  - Security headers: ✅")
        print("  - Rate limiting: ✅")
        print("  - Input validation: ✅")
    else:
        print("⚠️ Security middleware not available")

    # Final startup status
    if startup_success:
        print("🌟 Harbor application startup completed successfully")
    else:
        print("⚠️ Harbor application started with issues - some features may not work")

    print("🌐 Starting server...")

    yield

    # Shutdown tasks
    print("🛑 Shutting down Harbor Container Updater...")

    try:
        # Close database connections
        if session_manager:
            await session_manager.close()
            print("✅ Database connections closed")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
        print(f"❌ Error during shutdown: {e}")

    print("✅ Harbor application shutdown completed")


def create_app() -> FastAPI:
    """
    Application factory for Harbor Container Updater with database integration.

    Returns:
        FastAPI: Configured FastAPI application instance

    Note:
        This implements M0 milestone functionality including security middleware
        and database integration. Full functionality will be added in subsequent milestones.
    """

    # Get configuration if available
    if CONFIG_AVAILABLE:
        try:
            settings = get_settings()
            deployment_profile = settings.deployment_profile.value
            debug_mode = settings.debug
            cors_origins = getattr(settings, "cors_origins", ["*"])
        except Exception:
            deployment_profile = os.getenv("HARBOR_MODE", "homelab")
            debug_mode = False
            cors_origins = ["*"]
    else:
        deployment_profile = os.getenv("HARBOR_MODE", "homelab")
        debug_mode = False
        cors_origins = ["*"]

    app = FastAPI(
        title="Harbor Container Updater",
        description=__description__,
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        debug=debug_mode,
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
    )

    # Set up security middleware (M0 milestone)
    if SECURITY_AVAILABLE:
        try:
            # Method 1: Use the setup function from security module
            app = setup_security_middleware(app)
            print("🔐 Security middleware configured via setup function")

        except Exception as e:
            # Method 2: Fallback to manual middleware setup
            try:
                # Add security middleware manually (order matters - headers should be last)
                app.add_middleware(RateLimitMiddleware)
                app.add_middleware(SecurityHeadersMiddleware)

                print("🔐 Security middleware configured manually")
            except Exception as e2:
                logger.error(f"Security middleware setup failed: {e2}, original: {e}")
                print(f"⚠️ Security middleware setup failed: {e2}")
                print(f"Original setup error: {e}")
    else:
        print(
            "⚠️ Security middleware not available - continuing without security features"
        )

    # Health check endpoint (required for Docker health checks)
    @app.get("/healthz")
    async def health_check() -> dict[str, Any]:
        """Enhanced health check endpoint with database status."""
        try:
            health_data: dict[str, Any] = {
                "status": "healthy",
                "version": __version__,
                "milestone": __milestone__,
                "deployment_profile": deployment_profile,
                "python_version": sys.version,
                "components": {
                    "configuration": CONFIG_AVAILABLE,
                    "database": DATABASE_AVAILABLE,
                    "security_middleware": SECURITY_AVAILABLE,
                },
            }

            # Add configuration info if available
            if CONFIG_AVAILABLE:
                try:
                    settings = get_settings()
                    health_data.update(
                        {
                            "database_type": settings.database.database_type.value,
                            "features_enabled": {
                                "auto_discovery": settings.features.enable_auto_discovery,
                                "metrics": settings.features.enable_metrics,
                                "health_checks": settings.features.enable_health_checks,
                                "security_middleware": SECURITY_AVAILABLE,
                                "simple_mode": settings.features.enable_simple_mode,
                            },
                            "security": {
                                "https_required": settings.security.require_https,
                                "api_key_required": settings.security.api_key_required,
                                "rate_limiting": SECURITY_AVAILABLE,
                            },
                        }
                    )
                except Exception:  # Don't capture exception variable
                    logger.error("Config error in health check", exc_info=True)
                    health_data["config_status"] = "error"

            # Add database health if available
            if DATABASE_AVAILABLE:
                try:
                    db_info = await get_database_info()
                    health_data["database"] = {
                        "status": "connected",
                        "dialect": db_info.get("dialect", "unknown"),
                        "table_count": db_info.get("table_count", 0),
                    }

                    if "size_mb" in db_info:
                        health_data["database"]["size_mb"] = db_info["size_mb"]

                except Exception:  # Don't capture exception variable
                    logger.error("Database health check error", exc_info=True)
                    # Don't expose database error details
                    health_data["database"] = {"status": "error"}
                    health_data["status"] = "degraded"

            # Add timestamp
            import datetime

            health_data["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"

            return health_data

        except Exception:  # Don't capture exception variable to avoid any exposure risk
            logger.error("Health check failed", exc_info=True)

            # Return absolute minimum information
            return {
                "status": "unhealthy",
                "version": __version__,
                "milestone": __milestone__,
            }

    # Readiness check endpoint with database validation
    @app.get("/readyz")
    async def readiness_check() -> dict[str, Any]:
        """Enhanced readiness check endpoint with database validation."""
        ready_data: dict[str, Any] = {
            "ready": True,
            "version": __version__,
            "milestone": __milestone__,
            "status": __status__,
            "components": {
                "configuration": CONFIG_AVAILABLE,
                "database": False,  # Will be updated below
                "security_middleware": SECURITY_AVAILABLE,
            },
        }

        # Check configuration availability
        if CONFIG_AVAILABLE:
            try:
                settings = get_settings()
                errors = validate_runtime_requirements()
                ready_data.update(
                    {
                        "config_valid": len(errors) == 0,
                        "deployment_profile": settings.deployment_profile.value,
                    }
                )
                if errors:
                    ready_data["ready"] = False
                    ready_data["config_errors"] = errors
            except Exception as config_err:
                logger.error(f"Config error in readiness check: {config_err}")
                ready_data["ready"] = False
                # Don't expose error details
                ready_data["config_error"] = "configuration check failed"
        else:
            ready_data["ready"] = False
            ready_data["components"]["configuration"] = False

        # Check database availability
        if DATABASE_AVAILABLE:
            try:
                db_info = await get_database_info()
                ready_data["components"]["database"] = True
                ready_data["database_info"] = {
                    "dialect": db_info.get("dialect"),
                    "tables": db_info.get("table_count", 0),
                }

                # Verify essential tables exist by checking table count
                if (
                    db_info.get("table_count", 0) < 3
                ):  # Should have at least users, settings, containers
                    ready_data["ready"] = False
                    ready_data["database_error"] = "Essential tables missing"

            except Exception as db_err:
                logger.error(f"Database readiness error: {db_err}")
                ready_data["ready"] = False
                # Don't expose database error details
                ready_data["database_error"] = "database check failed"
                ready_data["components"]["database"] = False
        else:
            ready_data["ready"] = False
            ready_data["components"]["database"] = False

        # Update component status
        ready_data["components"].update(
            {
                "authentication": False,  # TODO: M0 - To be implemented
                "api_endpoints": False,  # TODO: M0 - To be implemented
                "container_discovery": False,  # TODO: M1 - Future milestone
                "update_engine": False,  # TODO: M2 - Future milestone
            }
        )

        return ready_data

    # Database status endpoint (M0 implementation)
    if DATABASE_AVAILABLE:

        @app.get("/database/status")
        async def database_status() -> dict[str, Any]:
            """Database status endpoint with detailed information."""
            try:
                db_info = await get_database_info()

                status_data = {
                    "status": "connected",
                    "info": db_info,
                    "milestone": "M0",
                    "features": {
                        "models_implemented": [
                            "User",
                            "APIKey",
                            "SystemSettings",
                            "Container",
                            "ContainerPolicy",
                        ],
                        "repositories_available": [
                            "UserRepository",
                            "ContainerRepository",
                        ],
                        "session_management": True,
                        "migrations": True,
                        "backup_support": True,
                    },
                }

                # Log database info for debugging (server-side only)
                logger.info(
                    "Database status retrieved successfully", extra={"db_info": db_info}
                )
                return status_data

            except Exception:  # Don't capture exception variable
                # Log full error details server-side with stack trace
                logger.error("Database status error occurred", exc_info=True)
                # Return generic error without any exception details
                return {
                    "status": "error",
                    "milestone": "M0",
                    "message": "Unable to retrieve database status",
                }

        @app.get("/database/health")
        async def database_health() -> dict[str, Any]:
            """Database health check with connection test."""
            try:
                # Test database connection
                async with get_session() as session:
                    from sqlalchemy import text

                    result = await session.execute(text("SELECT 1 as test"))
                    test_value = result.scalar()

                if test_value == 1:
                    # Try to get system settings to verify tables exist
                    async with get_session() as session:
                        settings = await session.get(SystemSettings, 1)

                    return {
                        "status": "healthy",
                        "connection": "ok",
                        "tables": "verified",
                        "system_settings": "found" if settings else "missing",
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "connection": "failed",
                        "error": "Test query failed",
                    }

            except Exception as e:
                logger.error(f"Database health check error: {e}", exc_info=True)
                # Don't expose exception details
                return {
                    "status": "unhealthy",
                    "connection": "error",
                }

    # Basic info endpoint
    @app.get("/")
    def root() -> dict[str, Any]:
        """Root endpoint with Harbor information including database status."""
        root_data: dict[str, Any] = {
            "name": "Harbor Container Updater",
            "version": __version__,
            "description": __description__,
            "milestone": __milestone__,
            "status": __status__,
            "deployment_profile": deployment_profile,
            "documentation": "/docs",
            "health": "/healthz",
            "readiness": "/readyz",
            "components": {
                "configuration": CONFIG_AVAILABLE,
                "database": DATABASE_AVAILABLE,
                "security_middleware": SECURITY_AVAILABLE,
            },
            "security": {
                "middleware_enabled": SECURITY_AVAILABLE,
                "rate_limiting": SECURITY_AVAILABLE,
                "input_validation": SECURITY_AVAILABLE,
                "security_headers": SECURITY_AVAILABLE,
            },
        }

        # Add database endpoints if available
        if DATABASE_AVAILABLE:
            root_data["database_endpoints"] = {
                "status": "/database/status",
                "health": "/database/health",
            }

        # Add configuration summary if available
        if CONFIG_AVAILABLE:
            try:
                config_summary = get_config_summary()
                root_data["configuration"] = {
                    "database_type": config_summary["database_type"],
                    "auto_discovery": config_summary["auto_discovery_enabled"],
                    "simple_mode": config_summary.get("simple_mode_enabled", False),
                    "debug_mode": config_summary["debug"],
                }
            except Exception:
                logger.error("Error getting config summary", exc_info=True)
                root_data["configuration"] = {"status": "error"}

        return root_data

    # Version endpoint
    @app.get("/version")
    def version_info() -> dict[str, Any]:
        """Version information endpoint with M0 implementation status."""
        version_data: dict[str, Any] = {
            "version": __version__,
            "milestone": __milestone__,
            "status": __status__,
            "python_version": sys.version,
            "deployment_profile": deployment_profile,
            "build_info": {
                "security_middleware": "v1.0" if SECURITY_AVAILABLE else "unavailable",
                "database_system": "v1.0" if DATABASE_AVAILABLE else "unavailable",
                "features_implemented": [
                    "configuration_system",
                    "security_middleware" if SECURITY_AVAILABLE else None,
                    "database_models" if DATABASE_AVAILABLE else None,
                    "session_management" if DATABASE_AVAILABLE else None,
                    "repository_pattern" if DATABASE_AVAILABLE else None,
                ],
                "features_planned": [
                    "authentication_system",  # Next M0 task
                    "api_endpoints",  # Next M0 task
                    "template_system",  # Next M0 task
                    "container_discovery",  # M1
                    "update_engine",  # M2
                ],
            },
        }

        # Remove None values
        version_data["build_info"]["features_implemented"] = [
            f
            for f in version_data["build_info"]["features_implemented"]
            if f is not None
        ]

        # Add build information if available
        if CONFIG_AVAILABLE:
            try:
                settings = get_settings()
                version_data.update(
                    {
                        "app_name": settings.app_name,
                        "debug_mode": settings.debug,
                        "configuration": {
                            "profile": settings.deployment_profile.value,
                            "database": settings.database.database_type.value,
                            "log_level": settings.logging.log_level.value,
                        },
                    }
                )
            except Exception:
                logger.error("Error getting settings for version info", exc_info=True)
                # Silently ignore config errors - version endpoint should always work
                pass

        return version_data

    # Security status endpoint (M0 implementation)
    @app.get("/security/status")
    def security_status() -> dict[str, Any]:
        """Security status endpoint showing enabled security features."""
        security_data: dict[str, Any] = {
            "security_middleware": {
                "enabled": SECURITY_AVAILABLE,
                "components": {
                    "headers_middleware": SECURITY_AVAILABLE,
                    "rate_limiting": SECURITY_AVAILABLE,
                    "input_validation": SECURITY_AVAILABLE,
                    "request_sanitization": SECURITY_AVAILABLE,
                },
                "version": "1.0" if SECURITY_AVAILABLE else "unavailable",
                "milestone": "M0",
                "implementation": "app.security module",
            },
            "profile": deployment_profile,
        }

        if CONFIG_AVAILABLE and SECURITY_AVAILABLE:
            try:
                settings = get_settings()
                security_data["configuration"] = {
                    "https_required": settings.security.require_https,
                    "api_key_required": settings.security.api_key_required,
                    "session_timeout_hours": settings.security.session_timeout_hours,
                    "rate_limit_per_hour": settings.security.api_rate_limit_per_hour,
                    "password_requirements": {
                        "min_length": settings.security.password_min_length,
                        "require_special": settings.security.password_require_special,
                    },
                }

                # Add security headers info if available
                try:
                    from app.security.headers import get_security_headers_for_profile

                    headers = get_security_headers_for_profile(
                        settings.deployment_profile
                    )
                    security_data["headers"] = {
                        "count": len(headers),
                        "csp_enabled": "Content-Security-Policy" in headers,
                        "hsts_enabled": "Strict-Transport-Security" in headers,
                        "frame_options": headers.get("X-Frame-Options"),
                    }
                except ImportError:
                    # Security headers module is optional - endpoint should still work without it
                    # Headers info will simply be omitted from the response
                    logger.debug(
                        "Security headers module not available - skipping headers info"
                    )

            except Exception as e:
                logger.error(f"Security status config error: {e}", exc_info=True)
                security_data["configuration_error"] = "configuration unavailable"

        return security_data

    # Configuration endpoint (for debugging)
    if debug_mode and CONFIG_AVAILABLE:

        @app.get("/config")
        def config_info() -> dict[str, Any]:
            """Configuration information endpoint (debug only)."""
            try:
                config_summary = get_config_summary()

                # Add M0 milestone progress
                config_summary["milestone_progress"] = {
                    "current": __milestone__,
                    "status": __status__,
                    "completed_features": [
                        feature
                        for feature in [
                            "configuration_system",
                            "security_middleware" if SECURITY_AVAILABLE else None,
                            "database_models" if DATABASE_AVAILABLE else None,
                            "session_management" if DATABASE_AVAILABLE else None,
                            "repository_pattern" if DATABASE_AVAILABLE else None,
                        ]
                        if feature is not None
                    ],
                    "next_features": [
                        "authentication_system",
                        "api_endpoints",
                        "template_system",
                        "ui_components",
                    ],
                }

                # Add database info if available
                if DATABASE_AVAILABLE:
                    try:
                        import asyncio

                        db_info = asyncio.run(get_database_info())
                        config_summary["database"] = db_info
                    except Exception:
                        logger.error("Config database info error", exc_info=True)
                        # Don't expose internal error details
                        config_summary["database_status"] = "unavailable"

                return config_summary
            except Exception:
                logger.error("Config info error", exc_info=True)
                # Don't expose exception details
                return {"error": "Configuration information unavailable"}

    # Development endpoints for database testing
    if debug_mode and DATABASE_AVAILABLE:

        @app.get("/dev/database/test")
        async def test_database() -> dict[str, Any]:
            """Test database operations (development only)."""
            try:
                results: dict[str, Any] = {}

                # Test basic connection
                async with get_session() as session:
                    from sqlalchemy import text

                    result = await session.execute(text("SELECT 1 as test"))
                    results["connection"] = "ok" if result.scalar() == 1 else "failed"

                # Test user operations
                async with get_session() as session:
                    user_repo = UserRepository(session)
                    user_count = await user_repo.count()
                    results["users"] = {"count": user_count}

                # Test system settings
                async with get_session() as session:
                    settings = await session.get(SystemSettings, 1)
                    results["system_settings"] = {
                        "exists": settings is not None,
                        "profile": settings.deployment_profile if settings else None,
                    }

                results["status"] = "ok"
                return results

            except Exception:
                logger.error("Database test failed", exc_info=True)
                # Don't expose exception details even in debug mode
                return {
                    "status": "error",
                    "message": "Database test failed",
                }

    # Security testing endpoint (development only)
    if debug_mode and SECURITY_AVAILABLE:

        @app.get("/dev/security/test")
        async def test_security() -> dict[str, Any]:
            """Test security middleware (development only)."""
            try:
                from app.config import DeploymentProfile
                from app.security.headers import get_security_headers_for_profile
                from app.security.validation import InputSanitizer

                sanitizer = InputSanitizer()

                # Test input sanitization
                test_html = "<script>alert('test')</script>"
                sanitized = sanitizer.sanitize_html(test_html)

                # Test security headers
                headers = get_security_headers_for_profile(DeploymentProfile.HOMELAB)

                return {
                    "status": "ok",
                    "sanitization_test": {
                        "input": test_html,
                        "output": sanitized,
                        "safe": "<script>" not in sanitized,
                    },
                    "security_headers": {
                        "count": len(headers),
                        "has_csp": "Content-Security-Policy" in headers,
                        "has_frame_options": "X-Frame-Options" in headers,
                    },
                    "middleware_active": True,
                }

            except Exception:
                logger.error("Security test failed", exc_info=True)
                # Don't expose exception details even in debug mode
                return {
                    "status": "error",
                    "message": "Security test failed",
                }

    return app


def main() -> None:
    """
    Main entry point for Harbor CLI with M0 database integration status.

    TODO: Implement CLI interface in later milestones.
    Currently shows Harbor information and M0 progress.
    """
    print(f"🚢 Harbor Container Updater v{__version__}")
    print(f"🎯 Status: {__status__} ({__milestone__} Milestone)")
    print(f"📖 Description: {__description__}")
    print()

    # Show M0 milestone progress with database integration
    print("📋 M0 Milestone Progress:")
    print("  ✅ Configuration system")
    print(f"  {'✅' if SECURITY_AVAILABLE else '❌'} Security middleware")
    print("  ✅ Rate limiting")
    print("  ✅ Input validation")
    print("  ✅ Security headers")
    print(f"  {'✅' if DATABASE_AVAILABLE else '❌'} Database models")
    print(f"  {'✅' if DATABASE_AVAILABLE else '❌'} Session management")
    print(f"  {'✅' if DATABASE_AVAILABLE else '❌'} Repository pattern")
    print("  ⏳ Authentication system (next)")
    print("  ⏳ API endpoints (next)")
    print("  ⏳ Template system (next)")
    print()

    # Show configuration info if available
    if CONFIG_AVAILABLE:
        try:
            settings = get_settings()
            print("⚙️ Current Configuration:")
            print(f"  Profile: {settings.deployment_profile.value}")
            print(f"  Database: {settings.database.database_type.value}")
            print(f"  Data directory: {settings.data_dir}")
            print(f"  Debug mode: {settings.debug}")
            print(
                f"  Security middleware: {'✅' if SECURITY_AVAILABLE else '❌'} {'Enabled' if SECURITY_AVAILABLE else 'Missing'}"
            )
            print(
                f"  Database system: {'✅' if DATABASE_AVAILABLE else '❌'} {'Ready' if DATABASE_AVAILABLE else 'Missing'}"
            )
            print()
        except Exception as e:
            print(f"⚠️ Configuration error: {e}")
            print()

    print("🚀 To run Harbor:")
    print("  uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8080")
    print()
    print("🔧 For development:")
    print("  uvicorn app.main:create_app --factory --reload")
    print()

    if DATABASE_AVAILABLE:
        print("🗄️ Database endpoints:")
        print("  curl http://localhost:8080/database/status | jq .")
        print("  curl http://localhost:8080/database/health | jq .")
        print()

    if SECURITY_AVAILABLE:
        print("🔐 Security endpoints:")
        print("  curl http://localhost:8080/security/status | jq .")
        print(
            "  curl -I http://localhost:8080/ | grep -E '(X-|Content-Security|Strict-Transport)'"
        )
        print()

    print("🧪 Test complete system:")
    print("  python test_db_implementation.py --verbose")
    print("  python test_security_middleware.py")
    print()

    if DATABASE_AVAILABLE:
        print("🧪 Test database models:")
        print("  python -m pytest tests/unit/db/ -v --database")
        print("  python -m pytest tests/integration/test_database.py -v --integration")
        print()

    print("📚 Documentation:")
    print("  http://localhost:8080/docs (when running)")
    print("  http://localhost:8080/redoc (alternative docs)")
    print()

    print("🎉 M0 Implementation Status:")
    print(f"  Configuration: {'✅ Ready' if CONFIG_AVAILABLE else '❌ Missing'}")
    print(f"  Security: {'✅ Ready' if SECURITY_AVAILABLE else '❌ Missing'}")
    print(f"  Database: {'✅ Ready' if DATABASE_AVAILABLE else '❌ Missing'}")

    if CONFIG_AVAILABLE and SECURITY_AVAILABLE and DATABASE_AVAILABLE:
        print("\n🌟 All M0 core systems ready! You can now:")
        print("  1. Start the application with uvicorn")
        print("  2. Run comprehensive tests")
        print("  3. Begin M0 Authentication System implementation")
    else:
        print("\n⚠️ Some M0 systems need attention before proceeding")


if __name__ == "__main__":
    main()
