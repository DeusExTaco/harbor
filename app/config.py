# app/config.py
"""
Harbor Configuration Management - FIXED TYPE ANNOTATIONS

Uses factory pattern to explicitly read environment variables and pass them
as initialization data to Pydantic. This bypasses Pydantic's environment
variable caching issues.
"""

import os
import platform
import sys
from enum import Enum
from pathlib import Path
from typing import Any


try:
    # Pydantic v2 - BaseSettings moved to pydantic-settings
    from pydantic_settings import BaseSettings, SettingsConfigDict

    PYDANTIC_V2 = True
except ImportError:
    # Fallback for Pydantic v1
    from pydantic import BaseSettings  # type: ignore[no-redef]

    PYDANTIC_V2 = False

from app.utils.logging import get_logger


logger = get_logger(__name__)


# =============================================================================
# Enums and Constants
# =============================================================================


class DeploymentProfile(str, Enum):
    """Deployment profile options"""

    HOMELAB = "homelab"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Logging level options"""

    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseType(str, Enum):
    """Database type options"""

    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


# =============================================================================
# Environment Variable Reader - THE CORE FIX
# =============================================================================


class EnvironmentReader:
    """
    Centralized environment variable reading with type conversion

    This is the key to fixing the Pydantic environment variable issues.
    We explicitly read environment variables and convert them to the
    correct types before passing to Pydantic.
    """

    @staticmethod
    def read_str(env_var: str, default: str) -> str:
        """Read string environment variable"""
        return os.getenv(env_var, default)

    @staticmethod
    def read_bool(env_var: str, default: bool) -> bool:
        """Read boolean environment variable"""
        value = os.getenv(env_var)
        if value is None:
            return default
        return value.lower() in ("true", "1", "yes", "on")

    @staticmethod
    def read_int(env_var: str, default: int) -> int:
        """Read integer environment variable"""
        value = os.getenv(env_var)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            logger.warning(
                f"Invalid integer value for {env_var}: {value}, using default: {default}"
            )
            return default

    @staticmethod
    def read_enum(env_var: str, enum_class: type, default: Any) -> Any:
        """Read enum environment variable"""
        value = os.getenv(env_var)
        if value is None:
            return default
        try:
            return enum_class(value)
        except ValueError:
            logger.warning(
                f"Invalid {enum_class.__name__} value for {env_var}: {value}, using default: {default}"
            )
            return default

    @staticmethod
    def read_path(env_var: str, default: str) -> Path:
        """Read path environment variable"""
        value = os.getenv(env_var, default)
        return Path(value)

    @staticmethod
    def read_list(env_var: str, default: list[str]) -> list[str]:
        """Read comma-separated list environment variable"""
        value = os.getenv(env_var)
        if value is None:
            return default
        return [item.strip() for item in value.split(",") if item.strip()]


# Global environment reader instance
env = EnvironmentReader()


# =============================================================================
# Settings Classes - REWRITTEN TO USE FACTORY PATTERN
# =============================================================================


class DatabaseSettings(BaseSettings):
    """Database configuration settings - uses factory pattern"""

    database_type: DatabaseType
    database_url: str | None
    sqlite_path: Path | None
    pool_size: int
    max_overflow: int
    pool_timeout: int

    if PYDANTIC_V2:
        model_config = SettingsConfigDict(extra="ignore")
    else:

        class Config:
            extra = "ignore"


def create_database_settings() -> DatabaseSettings:
    """Factory function for DatabaseSettings"""
    return DatabaseSettings(
        database_type=env.read_enum(
            "HARBOR_DATABASE_TYPE", DatabaseType, DatabaseType.SQLITE
        ),
        database_url=os.getenv("DATABASE_URL"),
        sqlite_path=env.read_path("HARBOR_SQLITE_PATH", "data/harbor.db")
        if not os.getenv("DATABASE_URL")
        else None,
        pool_size=env.read_int("HARBOR_DB_POOL_SIZE", 5),
        max_overflow=env.read_int("HARBOR_DB_MAX_OVERFLOW", 10),
        pool_timeout=env.read_int("HARBOR_DB_POOL_TIMEOUT", 30),
    )


class SecuritySettings(BaseSettings):
    """Security configuration settings - uses factory pattern"""

    require_https: bool
    api_key_required: bool
    session_timeout_hours: int
    api_rate_limit_per_hour: int
    password_min_length: int
    password_require_special: bool

    if PYDANTIC_V2:
        model_config = SettingsConfigDict(extra="ignore")
    else:

        class Config:
            extra = "ignore"


def create_security_settings(profile: DeploymentProfile) -> SecuritySettings:
    """Factory function for SecuritySettings with profile-aware defaults"""

    # Profile-specific defaults
    if profile == DeploymentProfile.HOMELAB:
        default_https = False
        default_session_timeout = 168  # 1 week
        default_password_length = 6
        default_require_special = False
    elif profile == DeploymentProfile.DEVELOPMENT:
        default_https = False
        default_session_timeout = 72  # 3 days
        default_password_length = 6
        default_require_special = False
    elif profile == DeploymentProfile.STAGING:
        default_https = True
        default_session_timeout = 24  # 1 day
        default_password_length = 8
        default_require_special = True
    else:  # PRODUCTION
        default_https = True
        default_session_timeout = 8  # 8 hours
        default_password_length = 12
        default_require_special = True

    return SecuritySettings(
        require_https=env.read_bool("HARBOR_REQUIRE_HTTPS", default_https),
        api_key_required=env.read_bool(
            "HARBOR_API_KEY_REQUIRED", profile == DeploymentProfile.PRODUCTION
        ),
        session_timeout_hours=env.read_int(
            "HARBOR_SESSION_TIMEOUT_HOURS", default_session_timeout
        ),
        api_rate_limit_per_hour=env.read_int("HARBOR_API_RATE_LIMIT_PER_HOUR", 1000),
        password_min_length=env.read_int(
            "HARBOR_SECURITY_PASSWORD_MIN_LENGTH", default_password_length
        ),
        password_require_special=env.read_bool(
            "HARBOR_SECURITY_PASSWORD_REQUIRE_SPECIAL", default_require_special
        ),
    )


class LoggingSettings(BaseSettings):
    """Logging configuration settings - uses factory pattern"""

    log_level: LogLevel
    log_format: str
    log_retention_days: int
    enable_file_logging: bool

    if PYDANTIC_V2:
        model_config = SettingsConfigDict(extra="ignore")
    else:

        class Config:
            extra = "ignore"


def create_logging_settings(profile: DeploymentProfile) -> LoggingSettings:
    """Factory function for LoggingSettings with profile-aware defaults"""

    # Profile-specific defaults
    if profile == DeploymentProfile.DEVELOPMENT:
        default_level = LogLevel.DEBUG
        default_retention = 7
    elif profile == DeploymentProfile.PRODUCTION:
        default_level = LogLevel.INFO
        default_retention = 90
    else:
        default_level = LogLevel.INFO
        default_retention = 14

    return LoggingSettings(
        log_level=env.read_enum("HARBOR_LOG_LOG_LEVEL", LogLevel, default_level),
        log_format=env.read_str("HARBOR_LOG_FORMAT", "text"),
        log_retention_days=env.read_int("HARBOR_LOG_RETENTION_DAYS", default_retention),
        enable_file_logging=env.read_bool("HARBOR_ENABLE_FILE_LOGGING", True),
    )


class FeatureSettings(BaseSettings):
    """Feature flag settings - uses factory pattern"""

    enable_auto_discovery: bool
    enable_metrics: bool
    enable_health_checks: bool
    enable_simple_mode: bool
    show_getting_started: bool
    enable_notifications: bool
    enable_rbac: bool

    if PYDANTIC_V2:
        model_config = SettingsConfigDict(extra="ignore")
    else:

        class Config:
            extra = "ignore"


def create_feature_settings(profile: DeploymentProfile) -> FeatureSettings:
    """Factory function for FeatureSettings with profile-aware defaults"""

    return FeatureSettings(
        enable_auto_discovery=env.read_bool("HARBOR_ENABLE_AUTO_DISCOVERY", True),
        enable_metrics=env.read_bool("HARBOR_ENABLE_METRICS", True),
        enable_health_checks=env.read_bool("HARBOR_ENABLE_HEALTH_CHECKS", True),
        enable_simple_mode=env.read_bool(
            "HARBOR_ENABLE_SIMPLE_MODE", profile != DeploymentProfile.PRODUCTION
        ),
        show_getting_started=env.read_bool(
            "HARBOR_SHOW_GETTING_STARTED", profile != DeploymentProfile.PRODUCTION
        ),
        enable_notifications=env.read_bool(
            "HARBOR_ENABLE_NOTIFICATIONS", False
        ),  # Future feature
        enable_rbac=env.read_bool("HARBOR_ENABLE_RBAC", False),  # Future feature
    )


class UpdateSettings(BaseSettings):
    """Update configuration settings - uses factory pattern"""

    default_check_interval_seconds: int
    default_update_time: str
    max_concurrent_updates: int
    default_cleanup_keep_images: int
    update_timeout_seconds: int

    if PYDANTIC_V2:
        model_config = SettingsConfigDict(extra="ignore")
    else:

        class Config:
            extra = "ignore"


def create_update_settings(profile: DeploymentProfile) -> UpdateSettings:
    """Factory function for UpdateSettings with profile-aware defaults"""

    # Profile-specific defaults
    if profile == DeploymentProfile.HOMELAB or profile == DeploymentProfile.DEVELOPMENT:
        default_concurrent = 2
    elif profile == DeploymentProfile.STAGING:
        default_concurrent = 5
    else:  # PRODUCTION
        default_concurrent = 10

    return UpdateSettings(
        default_check_interval_seconds=env.read_int(
            "HARBOR_DEFAULT_CHECK_INTERVAL_SECONDS", 86400
        ),
        default_update_time=env.read_str("HARBOR_DEFAULT_UPDATE_TIME", "03:00"),
        max_concurrent_updates=env.read_int(
            "HARBOR_UPDATE_MAX_CONCURRENT_UPDATES", default_concurrent
        ),
        default_cleanup_keep_images=env.read_int(
            "HARBOR_DEFAULT_CLEANUP_KEEP_IMAGES", 2
        ),
        update_timeout_seconds=env.read_int("HARBOR_UPDATE_TIMEOUT_SECONDS", 600),
    )


# =============================================================================
# Main Settings Class - FACTORY PATTERN
# =============================================================================


class HarborSettings(BaseSettings):
    """Main Harbor configuration settings - FACTORY PATTERN APPROACH"""

    # Application metadata
    app_name: str
    app_version: str
    debug: bool
    testing: bool
    deployment_profile: DeploymentProfile
    data_dir: Path
    logs_dir: Path
    timezone: str
    cors_origins: list[str]

    # Nested settings
    database: DatabaseSettings
    security: SecuritySettings
    logging: LoggingSettings
    features: FeatureSettings
    updates: UpdateSettings

    if PYDANTIC_V2:
        model_config = SettingsConfigDict(extra="ignore")
    else:

        class Config:
            extra = "ignore"

    def __post_init__(self) -> None:
        """Apply final validation and setup"""
        self._ensure_data_directory()
        self._validate_configuration()

    def _ensure_data_directory(self) -> None:
        """Ensure data directory exists"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "backups").mkdir(exist_ok=True)

    def _validate_configuration(self) -> None:
        """Validate configuration settings"""
        # Validate update time format
        if not self._is_valid_time_format(self.updates.default_update_time):
            raise ValueError(
                f"Invalid update time format: {self.updates.default_update_time}"
            )

        # Validate data directory is writable
        if not os.access(self.data_dir, os.W_OK):
            raise ValueError(f"Data directory not writable: {self.data_dir}")

    @staticmethod
    def _is_valid_time_format(time_str: str) -> bool:
        """Validate HH:MM time format"""
        try:
            parts = time_str.split(":")
            if len(parts) != 2:
                return False

            hours, minutes = int(parts[0]), int(parts[1])
            return 0 <= hours <= 23 and 0 <= minutes <= 59
        except (ValueError, IndexError):
            return False

    def to_dict(self) -> dict[str, Any]:
        """Convert settings to dictionary"""
        return {
            "app_name": self.app_name,
            "app_version": self.app_version,
            "debug": self.debug,
            "testing": self.testing,
            "deployment_profile": self.deployment_profile.value,
            "data_dir": str(self.data_dir),
            "logs_dir": str(self.logs_dir),
            "timezone": self.timezone,
            "database": {
                "database_type": self.database.database_type.value,
                "pool_size": self.database.pool_size,
                "max_overflow": self.database.max_overflow,
            },
            "security": {
                "require_https": self.security.require_https,
                "api_key_required": self.security.api_key_required,
                "session_timeout_hours": self.security.session_timeout_hours,
                "password_min_length": self.security.password_min_length,
            },
            "logging": {
                "log_level": self.logging.log_level.value,
                "log_format": self.logging.log_format,
                "log_retention_days": self.logging.log_retention_days,
            },
            "features": {
                "enable_auto_discovery": self.features.enable_auto_discovery,
                "enable_metrics": self.features.enable_metrics,
                "enable_health_checks": self.features.enable_health_checks,
                "enable_simple_mode": self.features.enable_simple_mode,
                "show_getting_started": self.features.show_getting_started,
            },
            "updates": {
                "default_check_interval_seconds": self.updates.default_check_interval_seconds,
                "default_update_time": self.updates.default_update_time,
                "max_concurrent_updates": self.updates.max_concurrent_updates,
                "default_cleanup_keep_images": self.updates.default_cleanup_keep_images,
            },
        }


# =============================================================================
# MAIN FACTORY FUNCTION - THE SOLUTION
# =============================================================================


def create_harbor_settings() -> HarborSettings:
    """Factory function to create HarborSettings with explicit environment variable reading"""

    # Read core settings from environment
    deployment_profile = env.read_enum(
        "HARBOR_MODE", DeploymentProfile, DeploymentProfile.HOMELAB
    )
    debug = env.read_bool(
        "HARBOR_DEBUG", deployment_profile == DeploymentProfile.DEVELOPMENT
    )

    # Log the profile we're using
    logger.debug(f"Creating Harbor settings for profile: {deployment_profile.value}")

    # Create nested settings with profile awareness
    database_settings = create_database_settings()
    security_settings = create_security_settings(deployment_profile)
    logging_settings = create_logging_settings(deployment_profile)
    feature_settings = create_feature_settings(deployment_profile)
    update_settings = create_update_settings(deployment_profile)

    # Create main settings
    settings = HarborSettings(
        app_name=env.read_str("HARBOR_APP_NAME", "Harbor Container Updater"),
        app_version=env.read_str("HARBOR_VERSION", "1.0.0"),
        debug=debug,
        testing=env.read_bool("TESTING", False),
        deployment_profile=deployment_profile,
        data_dir=env.read_path("HARBOR_DATA_DIR", "data"),
        logs_dir=env.read_path("HARBOR_LOGS_DIR", "data/logs"),
        timezone=env.read_str("HARBOR_TIMEZONE", "UTC"),
        cors_origins=env.read_list("HARBOR_CORS_ORIGINS", ["*"]),
        database=database_settings,
        security=security_settings,
        logging=logging_settings,
        features=feature_settings,
        updates=update_settings,
    )

    # Apply post-init validation
    settings.__post_init__()

    return settings


# =============================================================================
# Settings Management - REWRITTEN FOR FACTORY PATTERN
# =============================================================================


class SettingsManager:
    """Settings manager that properly handles environment changes"""

    def __init__(self) -> None:
        self._cached_settings: HarborSettings | None = None
        self._env_snapshot: dict[str, str | None] | None = None

    def get_settings(self, force_reload: bool = False) -> HarborSettings:
        """Get settings with proper environment change detection"""
        current_env = self._get_env_snapshot()

        # Check if we need to reload
        if (
            force_reload
            or self._cached_settings is None
            or current_env != self._env_snapshot
        ):
            logger.debug(
                f"Creating new settings. Force: {force_reload}, Env changed: {current_env != self._env_snapshot}"
            )

            # Create settings using factory function
            self._cached_settings = create_harbor_settings()
            self._env_snapshot = current_env

            logger.debug(
                f"Created settings with profile: {self._cached_settings.deployment_profile.value}"
            )

        return self._cached_settings

    def clear_cache(self) -> None:
        """Clear cached settings"""
        self._cached_settings = None
        self._env_snapshot = None
        logger.debug("Settings cache cleared")

    def _get_env_snapshot(self) -> dict[str, str | None]:
        """Get snapshot of relevant environment variables"""
        env_vars = [
            "HARBOR_MODE",
            "HARBOR_DEBUG",
            "HARBOR_SECURITY_PASSWORD_MIN_LENGTH",
            "HARBOR_UPDATE_MAX_CONCURRENT_UPDATES",
            "HARBOR_LOG_LOG_LEVEL",
            "DATABASE_URL",
            "TESTING",
        ]

        return {var: os.getenv(var) for var in env_vars}


# Global settings manager
_settings_manager = SettingsManager()


# =============================================================================
# Public API Functions - UNCHANGED INTERFACE
# =============================================================================


def get_settings() -> HarborSettings:
    """Get Harbor settings instance"""
    return _settings_manager.get_settings()


def clear_settings_cache() -> None:
    """Clear settings cache completely"""
    _settings_manager.clear_cache()
    logger.debug("All settings caches cleared")


def reload_settings() -> HarborSettings:
    """Force reload settings from current environment"""
    logger.debug("Force reloading settings from environment")
    return _settings_manager.get_settings(force_reload=True)


def create_fresh_settings() -> HarborSettings:
    """Create a completely fresh settings instance bypassing all caches"""
    return create_harbor_settings()


# =============================================================================
# Helper Functions - UNCHANGED
# =============================================================================


def get_config_summary() -> dict[str, Any]:
    """Get configuration summary for debugging/status"""
    settings = get_settings()

    return {
        "deployment_profile": settings.deployment_profile.value,
        "database_type": settings.database.database_type.value,
        "data_dir": str(settings.data_dir),
        "debug": settings.debug,
        "testing": settings.testing,
        "log_level": settings.logging.log_level.value,
        "auto_discovery_enabled": settings.features.enable_auto_discovery,
        "simple_mode_enabled": settings.features.enable_simple_mode,
        "https_required": settings.security.require_https,
        "api_key_required": settings.security.api_key_required,
        "max_concurrent_updates": settings.updates.max_concurrent_updates,
    }


def validate_runtime_requirements() -> list[str]:
    """Validate runtime requirements and return list of errors"""
    errors = []

    try:
        settings = get_settings()

        # Check data directory
        if not settings.data_dir.exists():
            errors.append(f"Data directory does not exist: {settings.data_dir}")
        elif not os.access(settings.data_dir, os.W_OK):
            errors.append(f"Data directory not writable: {settings.data_dir}")

        # Check database configuration
        if settings.database.database_type == DatabaseType.POSTGRESQL:
            if not settings.database.database_url:
                if not os.getenv("DATABASE_URL"):
                    errors.append("PostgreSQL selected but no DATABASE_URL provided")

        # Check required environment variables for production
        if settings.deployment_profile == DeploymentProfile.PRODUCTION:
            required_vars = ["HARBOR_SECRET_KEY"]
            for var in required_vars:
                if not os.getenv(var):
                    errors.append(
                        f"Production deployment requires {var} environment variable"
                    )

        # Validate update time format
        if not HarborSettings._is_valid_time_format(
            settings.updates.default_update_time
        ):
            errors.append(
                f"Invalid update time format: {settings.updates.default_update_time}"
            )

    except Exception as e:
        errors.append(f"Configuration validation error: {e!s}")

    return errors


def is_development() -> bool:
    """Check if running in development mode"""
    settings = get_settings()
    return (
        settings.deployment_profile == DeploymentProfile.DEVELOPMENT or settings.debug
    )


def is_production() -> bool:
    """Check if running in production mode"""
    settings = get_settings()
    return settings.deployment_profile == DeploymentProfile.PRODUCTION


def is_homelab() -> bool:
    """Check if running in home lab mode"""
    settings = get_settings()
    return settings.deployment_profile == DeploymentProfile.HOMELAB


# =============================================================================
# Environment Detection and Other Helpers - UNCHANGED
# =============================================================================


def detect_environment() -> dict[str, Any]:
    """Detect environment information and suggest deployment profile"""
    # Get platform information
    system_info = platform.uname()

    # Detect if we're in a container - FIX: Use context manager
    is_container = os.path.exists("/.dockerenv")
    if not is_container and os.path.exists("/proc/1/cgroup"):
        try:
            with open(
                "/proc/1/cgroup"
            ) as f:  # Use context manager to ensure file is closed
                cgroup_content = f.read()
                is_container = "docker" in cgroup_content
        except OSError:
            is_container = False

    # Detect if we're in cloud environment
    is_cloud = any(
        [
            os.getenv("AWS_EXECUTION_ENV"),
            os.getenv("GOOGLE_CLOUD_PROJECT"),
            os.getenv("AZURE_FUNCTIONS_ENVIRONMENT"),
            os.getenv("KUBERNETES_SERVICE_HOST"),
        ]
    )

    cpu_count = os.cpu_count() or 1

    # Memory detection (basic) - FIX: Also use context manager here
    try:
        with open("/proc/meminfo") as f:  # Use context manager
            meminfo = f.read()
            mem_total_kb = int(
                [
                    line.split()[1]
                    for line in meminfo.split("\n")
                    if "MemTotal:" in line
                ][0]
            )
            mem_total_gb = mem_total_kb / 1024 / 1024
    except (OSError, IndexError, ValueError):
        mem_total_gb = 1  # Default fallback

    # Suggest profile based on environment
    if is_cloud or os.getenv("HARBOR_MODE") == "production":
        suggested_profile = "production"
    elif os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
        suggested_profile = "development"
    elif cpu_count <= 2 and mem_total_gb <= 4:
        suggested_profile = "homelab"  # Raspberry Pi or small systems
    elif os.getenv("HARBOR_MODE") == "development" or is_development():
        suggested_profile = "development"
    else:
        suggested_profile = "homelab"  # Default to home lab

    return {
        "platform": {
            "system": system_info.system,
            "machine": system_info.machine,
            "processor": system_info.processor,
            "release": system_info.release,
            "version": system_info.version,
        },
        "environment": {
            "python_version": sys.version,
            "is_container": is_container,
            "is_cloud": is_cloud,
            "cpu_count": cpu_count,
            "memory_gb": mem_total_gb,
        },
        "suggested_profile": suggested_profile,
        "current_profile": os.getenv("HARBOR_MODE", "homelab"),
        "docker_available": _check_docker_available(),
        "write_permissions": _check_write_permissions(),
    }


def _check_docker_available() -> bool:
    """Check if Docker is available

    Uses subprocess safely with controlled commands and no user input.
    """
    try:
        import shutil
        import subprocess  # nosec B404

        # First try to find docker using shutil.which (safer)
        docker_path = shutil.which("docker")
        if not docker_path:
            return False

        # Use the found path with subprocess
        result = subprocess.run(  # nosec B603
            [docker_path, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,  # Don't raise on non-zero exit
            # Restrict environment for additional security
            env={"PATH": "/usr/local/bin:/usr/bin:/bin", "LC_ALL": "C"},
        )
        return result.returncode == 0

    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return False


def _check_write_permissions() -> dict[str, bool]:
    """Check write permissions for required directories

    Uses Python's tempfile module for secure temporary file operations.
    """
    import tempfile

    permissions = {}

    # Use secure temp directory from tempfile
    test_dirs = [
        ("current_dir", "."),
        ("data_dir", "data"),
        ("tmp_dir", tempfile.gettempdir()),  # Secure temp directory
    ]

    for name, path in test_dirs:
        try:
            test_path = Path(path)
            test_path.mkdir(exist_ok=True, mode=0o755)

            # Use tempfile for secure temporary file creation
            with tempfile.NamedTemporaryFile(
                dir=str(test_path),
                prefix=".harbor_test_",
                suffix=".tmp",
                delete=True,  # Auto-cleanup
            ) as temp_file:
                temp_file.write(b"test")
                temp_file.flush()
                permissions[name] = True

        except (OSError, Exception):
            permissions[name] = False

    return permissions
