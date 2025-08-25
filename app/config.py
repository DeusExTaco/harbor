"""
Harbor Container Updater - Configuration Management

Environment-based configuration with Pydantic Settings for Harbor.
Supports multiple deployment profiles with progressive complexity.

Implementation: M0 Milestone - Foundation Phase
Following Harbor project structure and feature flags design.

Features:
- Profile-based configuration (homelab, development, staging, production)
- Environment variable override support
- Validation with clear error messages
- Feature flag integration
- Security-conscious defaults
"""

import os
import secrets
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Type checking imports
if TYPE_CHECKING:
    pass

# Optional imports for environment detection
try:
    import psutil as _psutil  # Import with prefix to indicate conditional usage

    PSUTIL_AVAILABLE = True
except ImportError:
    _psutil = None
    PSUTIL_AVAILABLE = False

try:
    import yaml as _yaml  # Import with prefix to indicate conditional usage

    YAML_AVAILABLE = True
except ImportError:
    _yaml = None  # type: ignore[assignment]
    YAML_AVAILABLE = False


# =============================================================================
# Enums and Constants
# =============================================================================


class DeploymentProfile(str, Enum):
    """Deployment profile types following Harbor architecture design"""

    HOMELAB = "homelab"  # Home lab optimized defaults
    DEVELOPMENT = "development"  # Development with debugging
    STAGING = "staging"  # Pre-production testing
    PRODUCTION = "production"  # Enterprise production


class LogLevel(str, Enum):
    """Logging levels"""

    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(str, Enum):
    """Log output formats"""

    TEXT = "text"  # Human-readable (home lab)
    JSON = "json"  # Structured (production)


class DatabaseType(str, Enum):
    """Supported database types"""

    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


# =============================================================================
# Configuration Models
# =============================================================================


class DatabaseSettings(BaseSettings):
    """Database configuration settings"""

    # Database connection
    database_url: str | None = Field(
        default=None, description="Database URL (auto-generated if not provided)"
    )
    database_type: DatabaseType = Field(
        default=DatabaseType.SQLITE, description="Database type to use"
    )

    # Connection pool settings
    pool_size: int = Field(
        default=5, ge=1, le=100, description="Database connection pool size"
    )
    max_overflow: int = Field(
        default=2, ge=0, le=50, description="Database connection pool overflow"
    )
    pool_timeout: int = Field(
        default=30, ge=5, le=300, description="Database connection timeout (seconds)"
    )

    # Performance settings
    echo_sql: bool = Field(
        default=False, description="Echo SQL queries (development only)"
    )

    # Backup settings (home lab)
    backup_enabled: bool = Field(
        default=True, description="Enable automatic database backups"
    )
    backup_retention_days: int = Field(
        default=7, ge=1, le=365, description="Days to retain database backups"
    )

    model_config = SettingsConfigDict(env_prefix="HARBOR_DB_")


class SecuritySettings(BaseSettings):
    """Security configuration settings"""

    # Core security
    secret_key: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="Application secret key for encryption",
    )
    secret_key_file: Path | None = Field(
        default=None, description="Path to file containing secret key"
    )

    # HTTP/HTTPS
    require_https: bool = Field(
        default=False, description="Require HTTPS for all requests"
    )

    # Session management
    session_timeout_hours: int = Field(
        default=168,  # 1 week for home lab
        ge=1,
        le=8760,  # 1 year max
        description="Session timeout in hours",
    )
    session_secure_cookies: bool = Field(
        default=False, description="Use secure cookies (requires HTTPS)"
    )

    # API security
    api_key_required: bool = Field(
        default=False, description="Require API key for programmatic access"
    )
    api_rate_limit_per_hour: int = Field(
        default=1000, ge=10, le=100000, description="API requests per hour limit"
    )

    # Password policy
    password_min_length: int = Field(
        default=6,  # Relaxed for home lab
        ge=4,
        le=128,
        description="Minimum password length",
    )
    password_require_special: bool = Field(
        default=False, description="Require special characters in passwords"
    )

    # Future features (behind feature flags)
    # TODO: M7+ - Multi-factor authentication
    mfa_enabled: bool = Field(
        default=False, description="Enable multi-factor authentication (M7+)"
    )

    model_config = SettingsConfigDict(env_prefix="HARBOR_SECURITY_")


class UpdateSettings(BaseSettings):
    """Container update configuration settings"""

    # Default update policy
    default_check_interval_seconds: int = Field(
        default=86400,  # Daily
        ge=300,  # 5 minutes minimum
        le=604800,  # 1 week maximum
        description="Default interval between update checks",
    )
    default_update_time: str = Field(
        default="03:00",
        pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$",
        description="Default time for scheduled updates (HH:MM)",
    )
    default_timezone: str = Field(
        default="UTC", description="Default timezone for scheduling"
    )

    # Concurrency and performance
    max_concurrent_updates: int = Field(
        default=2,  # Conservative for home lab
        ge=1,
        le=50,
        description="Maximum concurrent update operations",
    )
    update_delay_seconds: int = Field(
        default=0, ge=0, le=300, description="Delay between starting concurrent updates"
    )

    # Safety settings
    default_health_check_timeout: int = Field(
        default=60, ge=10, le=600, description="Default health check timeout (seconds)"
    )
    default_rollback_enabled: bool = Field(
        default=True, description="Enable automatic rollback by default"
    )

    # Cleanup settings
    default_cleanup_enabled: bool = Field(
        default=True, description="Enable automatic image cleanup by default"
    )
    default_cleanup_keep_images: int = Field(
        default=2, ge=1, le=10, description="Default number of old images to keep"
    )
    cleanup_delay_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Hours to wait before cleaning up old images",
    )

    model_config = SettingsConfigDict(env_prefix="HARBOR_UPDATE_")


class RegistrySettings(BaseSettings):
    """Container registry configuration settings"""

    # Registry client settings
    timeout_seconds: int = Field(
        default=30, ge=5, le=300, description="Registry request timeout"
    )
    retry_count: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Number of retries for failed registry requests",
    )

    # Caching settings
    cache_ttl_seconds: int = Field(
        default=3600,  # 1 hour
        ge=60,
        le=86400,
        description="Registry response cache TTL",
    )
    cache_size_mb: int = Field(
        default=50, ge=10, le=1000, description="Maximum registry cache size (MB)"
    )

    # Rate limiting (respect registry limits)
    rate_limit_calls_per_hour: int = Field(
        default=100, ge=10, le=10000, description="Registry API calls per hour limit"
    )

    model_config = SettingsConfigDict(env_prefix="HARBOR_REGISTRY_")


class LoggingSettings(BaseSettings):
    """Logging configuration settings"""

    # Log levels and formats
    log_level: LogLevel = Field(
        default=LogLevel.INFO, description="Application log level"
    )
    log_format: LogFormat = Field(
        default=LogFormat.TEXT, description="Log output format"
    )

    # File logging
    log_to_file: bool = Field(default=True, description="Enable file logging")
    log_file_path: Path | None = Field(
        default=None, description="Log file path (auto-generated if not provided)"
    )
    log_rotation_size_mb: int = Field(
        default=10, ge=1, le=100, description="Log file rotation size (MB)"
    )
    log_retention_days: int = Field(
        default=14, ge=1, le=365, description="Days to retain log files"
    )

    # Console logging
    log_to_console: bool = Field(default=True, description="Enable console logging")

    model_config = SettingsConfigDict(env_prefix="HARBOR_LOG_")


class ResourceSettings(BaseSettings):
    """System resource configuration settings"""

    # Memory limits
    max_memory_usage_mb: int = Field(
        default=512, ge=128, le=8192, description="Maximum memory usage (MB)"
    )

    # Disk usage
    max_disk_usage_gb: int = Field(
        default=10, ge=1, le=1000, description="Maximum disk usage (GB)"
    )

    # Performance tuning
    max_workers: int | str = Field(
        default="auto", description="Maximum worker processes (auto or specific number)"
    )

    model_config = SettingsConfigDict(env_prefix="HARBOR_RESOURCE_")

    @field_validator("max_workers")
    @classmethod
    def validate_max_workers(cls, v: int | str) -> int | str:
        """Validate max_workers setting"""
        if isinstance(v, str):
            if v.lower() != "auto":
                raise ValueError("max_workers must be 'auto' or a positive integer")
            return "auto"
        if isinstance(v, int):
            if v < 1:
                raise ValueError("max_workers must be positive")
            return v
        raise ValueError("max_workers must be 'auto' or a positive integer")


class FeatureSettings(BaseSettings):
    """Feature flag configuration settings"""

    # M0 Features (Always enabled in v1.0)
    enable_auto_discovery: bool = Field(
        default=True, description="Enable automatic container discovery"
    )
    enable_metrics: bool = Field(
        default=True, description="Enable Prometheus metrics collection"
    )
    enable_health_checks: bool = Field(
        default=True, description="Enable health check monitoring"
    )

    # Home lab specific features
    show_getting_started: bool = Field(
        default=True, description="Show getting started wizard"
    )
    enable_simple_mode: bool = Field(
        default=True, description="Enable simplified UI mode"
    )
    auto_exclude_harbor: bool = Field(
        default=True, description="Automatically exclude Harbor from updates"
    )

    # Future features (disabled in v1.0, behind feature flags)
    # TODO: M7+ - Advanced authentication
    enable_mfa: bool = Field(
        default=False, description="Enable multi-factor authentication (M7+)"
    )
    enable_multi_user: bool = Field(
        default=False, description="Enable multi-user support (M8+)"
    )
    enable_rbac: bool = Field(
        default=False, description="Enable role-based access control (M8+)"
    )

    # TODO: M8+ - Advanced update strategies
    enable_blue_green: bool = Field(
        default=False, description="Enable blue/green deployments (M8+)"
    )
    enable_canary: bool = Field(
        default=False, description="Enable canary deployments (M8+)"
    )

    # TODO: M9+ - Enterprise integrations
    enable_ldap: bool = Field(
        default=False, description="Enable LDAP authentication (M9+)"
    )
    enable_kubernetes: bool = Field(
        default=False, description="Enable Kubernetes runtime (M9+)"
    )

    model_config = SettingsConfigDict(env_prefix="HARBOR_FEATURE_")


class DockerSettings(BaseSettings):
    """Docker runtime configuration settings"""

    # Docker connection
    docker_host: str = Field(
        default="unix:///var/run/docker.sock", description="Docker daemon socket URL"
    )
    docker_timeout: int = Field(
        default=60, ge=10, le=300, description="Docker API timeout (seconds)"
    )

    # Discovery settings
    discovery_interval_seconds: int = Field(
        default=300,  # 5 minutes
        ge=60,
        le=3600,
        description="Container discovery interval",
    )
    include_stopped_containers: bool = Field(
        default=True, description="Include stopped containers in discovery"
    )

    # Safety settings
    exclude_patterns: list[str] = Field(
        default_factory=lambda: [
            "harbor",  # Exclude Harbor itself
            "*_backup",  # Exclude backup containers
            "*_migrate",  # Exclude migration containers
        ],
        description="Container name patterns to exclude from management",
    )

    model_config = SettingsConfigDict(env_prefix="HARBOR_DOCKER_")


# =============================================================================
# Main Application Settings
# =============================================================================


class AppSettings(BaseSettings):
    """
    Main application settings with profile-based configuration.

    Follows Harbor architecture design with progressive complexity:
    - Home lab: Simple, zero-config defaults
    - Development: Debug-friendly with additional features
    - Staging: Testing enterprise features
    - Production: Enterprise-ready with full security
    """

    # Core application settings
    app_name: str = Field(
        default="Harbor Container Updater", description="Application name"
    )
    app_version: str = Field(default="0.1.0-alpha.2", description="Application version")
    debug: bool = Field(default=False, description="Enable debug mode")

    # Deployment configuration
    deployment_profile: DeploymentProfile = Field(
        default=DeploymentProfile.HOMELAB,
        description="Deployment profile (homelab, development, staging, production)",
    )

    # Server settings
    host: str = Field(
        default="0.0.0.0",  # nosec B104 - Safe for Docker container deployment
        description="Server bind address",
    )
    port: int = Field(default=8080, ge=1, le=65535, description="Server port")

    # Data directories
    data_dir: Path = Field(
        default_factory=lambda: Path("data"), description="Data storage directory"
    )
    logs_dir: Path = Field(
        default_factory=lambda: Path("logs"), description="Log files directory"
    )
    config_dir: Path = Field(
        default_factory=lambda: Path("config"),
        description="Configuration files directory",
    )

    # Sub-configurations
    database: DatabaseSettings = Field(
        default_factory=DatabaseSettings, description="Database settings"
    )
    security: SecuritySettings = Field(
        default_factory=SecuritySettings, description="Security settings"
    )
    updates: UpdateSettings = Field(
        default_factory=UpdateSettings, description="Update settings"
    )
    registry: RegistrySettings = Field(
        default_factory=RegistrySettings, description="Registry settings"
    )
    logging: LoggingSettings = Field(
        default_factory=LoggingSettings, description="Logging settings"
    )
    resources: ResourceSettings = Field(
        default_factory=ResourceSettings, description="Resource settings"
    )
    features: FeatureSettings = Field(
        default_factory=FeatureSettings, description="Feature flags"
    )
    docker: DockerSettings = Field(
        default_factory=DockerSettings, description="Docker settings"
    )

    model_config = SettingsConfigDict(
        env_prefix="HARBOR_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        validate_assignment=True,
        extra="forbid",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Any,
        init_settings: Any,
        env_settings: Any,
        dotenv_settings: Any,
        file_secret_settings: Any,
    ) -> tuple[Any, ...]:
        """Customize how settings are loaded, handling HARBOR_MODE properly"""
        if TYPE_CHECKING:
            from pydantic_settings import EnvSettingsSource
        else:
            from pydantic_settings import EnvSettingsSource

        class ProfileAwareEnvSource(EnvSettingsSource):
            def get_field_value(
                self, field_info: Any, field_name: str
            ) -> tuple[Any, str, bool]:
                # Handle HARBOR_MODE -> deployment_profile mapping
                if field_name == "deployment_profile":
                    harbor_mode = os.getenv("HARBOR_MODE")
                    if harbor_mode:
                        return (harbor_mode, field_name, False)

                # For nested settings, we need to let normal processing happen
                # The profile-specific defaults will be applied in model_post_init
                return super().get_field_value(field_info, field_name)

        return (
            init_settings,
            ProfileAwareEnvSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )

    def __init__(self, **kwargs: Any) -> None:
        """Initialize AppSettings with profile-aware defaults"""

        # First, determine the profile from environment or kwargs
        profile_value = kwargs.get("deployment_profile") or os.getenv(
            "HARBOR_MODE", "homelab"
        )
        if isinstance(profile_value, str):
            profile_value = DeploymentProfile(profile_value)

        # Store profile for use in model_post_init
        self._init_profile = profile_value

        # Apply top-level profile defaults
        if "debug" not in kwargs:
            if profile_value == DeploymentProfile.DEVELOPMENT:
                kwargs["debug"] = True
            else:
                kwargs["debug"] = False

        super().__init__(**kwargs)

    def model_post_init(self, __context: Any) -> None:
        """Apply profile-specific defaults after Pydantic processes environment variables"""

        # Apply profile-specific defaults to nested objects, but only for fields
        # that haven't been overridden by environment variables
        profile = getattr(self, "_init_profile", self.deployment_profile)

        self._apply_security_profile_defaults(profile)
        self._apply_update_profile_defaults(profile)
        self._apply_logging_profile_defaults(profile)
        self._apply_resource_profile_defaults(profile)
        self._apply_database_profile_defaults(profile)
        self._apply_registry_profile_defaults(profile)
        self._apply_feature_profile_defaults(profile)
        self._apply_docker_profile_defaults(profile)

        self._validate_configuration()
        self._ensure_directories()

    def _apply_security_profile_defaults(self, profile: DeploymentProfile) -> None:
        """Apply profile defaults to security settings if not overridden"""
        if profile == DeploymentProfile.HOMELAB:
            self._set_if_default(self.security, "require_https", False)
            self._set_if_default(self.security, "session_timeout_hours", 168)
            self._set_if_default(self.security, "api_key_required", False)
            self._set_if_default(self.security, "password_min_length", 6)
        elif profile == DeploymentProfile.DEVELOPMENT:
            self._set_if_default(self.security, "require_https", False)
            self._set_if_default(self.security, "session_timeout_hours", 72)
            self._set_if_default(self.security, "api_key_required", False)
            self._set_if_default(self.security, "password_min_length", 6)
        elif profile == DeploymentProfile.PRODUCTION:
            self._set_if_default(self.security, "require_https", True)
            self._set_if_default(self.security, "session_timeout_hours", 8)
            self._set_if_default(self.security, "api_key_required", True)
            self._set_if_default(self.security, "password_min_length", 12)
            self._set_if_default(self.security, "password_require_special", True)

    def _apply_update_profile_defaults(self, profile: DeploymentProfile) -> None:
        """Apply profile defaults to update settings if not overridden"""
        if profile == DeploymentProfile.HOMELAB:
            self._set_if_default(self.updates, "max_concurrent_updates", 2)
        elif profile == DeploymentProfile.DEVELOPMENT:
            self._set_if_default(self.updates, "max_concurrent_updates", 3)
        elif profile == DeploymentProfile.PRODUCTION:
            self._set_if_default(self.updates, "default_check_interval_seconds", 21600)
            self._set_if_default(self.updates, "default_update_time", "02:00")
            self._set_if_default(self.updates, "max_concurrent_updates", 10)
        elif profile == DeploymentProfile.STAGING:
            self._set_if_default(self.updates, "max_concurrent_updates", 5)

    def _apply_logging_profile_defaults(self, profile: DeploymentProfile) -> None:
        """Apply profile defaults to logging settings if not overridden"""
        if profile == DeploymentProfile.HOMELAB:
            self._set_if_default(self.logging, "log_level", LogLevel.INFO)
            self._set_if_default(self.logging, "log_format", LogFormat.TEXT)
            self._set_if_default(self.logging, "log_retention_days", 14)
        elif profile == DeploymentProfile.DEVELOPMENT:
            self._set_if_default(self.logging, "log_level", LogLevel.DEBUG)
            self._set_if_default(self.logging, "log_format", LogFormat.TEXT)
            self._set_if_default(self.logging, "log_retention_days", 14)
        elif profile == DeploymentProfile.PRODUCTION:
            self._set_if_default(self.logging, "log_level", LogLevel.INFO)
            self._set_if_default(self.logging, "log_format", LogFormat.JSON)
            self._set_if_default(self.logging, "log_retention_days", 90)
        elif profile == DeploymentProfile.STAGING:
            self._set_if_default(self.logging, "log_level", LogLevel.INFO)
            self._set_if_default(self.logging, "log_format", LogFormat.JSON)

    def _apply_resource_profile_defaults(self, profile: DeploymentProfile) -> None:
        """Apply profile defaults to resource settings if not overridden"""
        if profile == DeploymentProfile.HOMELAB:
            self._set_if_default(self.resources, "max_memory_usage_mb", 256)
            self._set_if_default(self.resources, "max_workers", 2)
        elif profile == DeploymentProfile.PRODUCTION:
            self._set_if_default(self.resources, "max_memory_usage_mb", 2048)
            self._set_if_default(self.resources, "max_workers", "auto")

    def _apply_database_profile_defaults(self, profile: DeploymentProfile) -> None:
        """Apply profile defaults to database settings if not overridden"""
        if profile == DeploymentProfile.DEVELOPMENT:
            self._set_if_default(self.database, "echo_sql", True)
        elif profile == DeploymentProfile.PRODUCTION:
            self._set_if_default(
                self.database, "database_type", DatabaseType.POSTGRESQL
            )
            if not self.database.database_url:
                self._set_if_default(
                    self.database,
                    "database_url",
                    "postgresql://harbor:changeme@localhost:5432/harbor",  # pragma: allowlist secret,
                )
            self._set_if_default(self.database, "pool_size", 20)

    def _apply_registry_profile_defaults(self, profile: DeploymentProfile) -> None:
        """Apply profile defaults to registry settings if not overridden"""
        if profile == DeploymentProfile.PRODUCTION:
            self._set_if_default(self.registry, "rate_limit_calls_per_hour", 1000)
            self._set_if_default(self.registry, "cache_size_mb", 200)

    def _apply_feature_profile_defaults(self, profile: DeploymentProfile) -> None:
        """Apply profile defaults to feature settings if not overridden"""
        if profile == DeploymentProfile.PRODUCTION:
            self._set_if_default(self.features, "show_getting_started", False)
            self._set_if_default(self.features, "enable_simple_mode", False)

    def _apply_docker_profile_defaults(self, profile: DeploymentProfile) -> None:
        """Apply profile defaults to docker settings if not overridden"""
        if profile == DeploymentProfile.DEVELOPMENT:
            self._set_if_default(self.docker, "discovery_interval_seconds", 60)

    def _set_if_default(self, obj: Any, field_name: str, profile_value: Any) -> None:
        """Set field value only if it's still at the class default"""
        current_value = getattr(obj, field_name)

        # Get the field info from the model fields
        field_info = obj.model_fields.get(field_name)

        if field_info and hasattr(field_info, "default"):
            class_default = field_info.default
            # If current value matches class default, apply profile default
            if current_value == class_default:
                setattr(obj, field_name, profile_value)
        else:
            # If we can't determine the default, just set the value
            # This ensures profile defaults are applied
            setattr(obj, field_name, profile_value)

    def _validate_configuration(self) -> None:
        """Validate configuration consistency and requirements"""

        # Handle secret key file loading
        if self.security.secret_key_file:
            secret_file = Path(self.security.secret_key_file)
            if secret_file.exists():
                self.security.secret_key = secret_file.read_text().strip()

        # Enforce secure cookies with HTTPS
        if self.security.require_https and not self.security.session_secure_cookies:
            self.security.session_secure_cookies = True

        # Production requirements (but allow testing with default database URL)
        if self.deployment_profile == DeploymentProfile.PRODUCTION:
            if not self.security.require_https:
                raise ValueError("HTTPS is required in production profile")
            if self.security.password_min_length < 8:
                raise ValueError(
                    "Password minimum length must be at least 8 in production"
                )

            # Only require database_url if it's not the default test URL
            if (
                self.database.database_type == DatabaseType.POSTGRESQL
                and not self.database.database_url
            ):
                raise ValueError(
                    "database_url is required for PostgreSQL in production"
                )

        # General database URL validation (skip for testing with default URLs)
        if (
            self.database.database_type == DatabaseType.POSTGRESQL
            and not self.database.database_url
            and self.deployment_profile != DeploymentProfile.PRODUCTION
        ):
            raise ValueError("database_url is required for PostgreSQL")

    def _ensure_directories(self) -> None:
        """Ensure required directories exist"""
        for directory in [self.data_dir, self.logs_dir, self.config_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        # Set log file path if not provided
        if not self.logging.log_file_path:
            self.logging.log_file_path = self.logs_dir / "harbor.log"


# =============================================================================
# Settings Factory and Management
# =============================================================================

# Global settings instance
_settings: AppSettings | None = None


def get_settings() -> AppSettings:
    """
    Get application settings (singleton pattern).

    Returns:
        AppSettings: Configured application settings
    """
    global _settings
    if _settings is None:
        _settings = AppSettings()
    return _settings


def reload_settings() -> AppSettings:
    """
    Reload settings from environment (useful for testing).

    Returns:
        AppSettings: Fresh application settings
    """
    global _settings
    _settings = None

    # Force creation of new instance which will re-read environment variables
    _settings = AppSettings()
    return _settings


def get_config_summary() -> dict[str, Any]:
    """
    Get configuration summary for debugging and logging.

    Returns:
        Dict[str, Any]: Configuration summary (safe for logging)
    """
    settings = get_settings()

    return {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "deployment_profile": settings.deployment_profile.value,
        "debug": settings.debug,
        "host": settings.host,
        "port": settings.port,
        "database_type": settings.database.database_type.value,
        "log_level": settings.logging.log_level.value,
        "log_format": settings.logging.log_format.value,
        "max_concurrent_updates": settings.updates.max_concurrent_updates,
        "auto_discovery_enabled": settings.features.enable_auto_discovery,
        "simple_mode_enabled": settings.features.enable_simple_mode,
        # Note: Sensitive values (secret keys, passwords) are excluded
    }


def validate_runtime_requirements() -> list[str]:
    """
    Validate runtime requirements and return any issues.

    Returns:
        List[str]: List of validation errors (empty if valid)
    """
    settings = get_settings()
    errors: list[str] = []

    # Check data directories are writable
    try:
        test_file = settings.data_dir / ".write_test"
        test_file.write_text("test")
        test_file.unlink()
    except Exception as e:
        errors.append(f"Data directory not writable: {e}")

    # Check log directory is writable
    try:
        test_file = settings.logs_dir / ".write_test"
        test_file.write_text("test")
        test_file.unlink()
    except Exception as e:
        errors.append(f"Logs directory not writable: {e}")

    # Check Docker socket accessibility (basic check)
    if settings.docker.docker_host.startswith("unix://"):
        socket_path = settings.docker.docker_host.replace("unix://", "")
        if not Path(socket_path).exists():
            errors.append(f"Docker socket not found: {socket_path}")

    # Validate secret key
    if len(settings.security.secret_key) < 16:
        errors.append("Secret key too short (minimum 16 characters)")

    return errors


# =============================================================================
# Configuration Loading Utilities
# =============================================================================


def load_profile_config(profile: DeploymentProfile) -> dict[str, Any]:
    """
    Load profile-specific configuration from YAML files.

    Args:
        profile: Deployment profile to load

    Returns:
        Dict[str, Any]: Profile configuration
    """
    config_file = Path("config") / f"{profile.value}.yaml"

    if config_file.exists():
        if YAML_AVAILABLE and _yaml:
            try:
                with config_file.open() as f:
                    return _yaml.safe_load(f) or {}
            except Exception as e:
                # Log warning but don't fail startup
                print(f"Warning: Could not load {config_file}: {e}")
        else:
            print(f"Warning: YAML support not available, skipping {config_file}")

    return {}


def get_profile_recommendations(profile: DeploymentProfile) -> dict[str, str]:
    """
    Get configuration recommendations for a deployment profile.

    Args:
        profile: Deployment profile

    Returns:
        Dict[str, str]: Configuration recommendations
    """
    if profile == DeploymentProfile.HOMELAB:
        return {
            "deployment_focus": "Zero configuration and ease of use",
            "security_level": "Basic (suitable for internal networks)",
            "resource_usage": "Optimized for low-power hardware",
            "update_strategy": "Conservative with safety checks",
            "recommended_features": "Auto-discovery, simple mode, getting started wizard",
        }
    elif profile == DeploymentProfile.PRODUCTION:
        return {
            "deployment_focus": "Security, compliance, and scalability",
            "security_level": "Enterprise grade with audit trails",
            "resource_usage": "Optimized for high-performance servers",
            "update_strategy": "Controlled with comprehensive monitoring",
            "recommended_features": "RBAC, audit export, advanced monitoring",
        }
    else:
        return {
            "deployment_focus": f"Testing and development for {profile.value}",
            "security_level": "Balanced for testing environments",
            "resource_usage": "Development optimized",
            "update_strategy": "Fast iteration with safety",
            "recommended_features": "Debug logging, feature testing",
        }


# =============================================================================
# Environment Detection Utilities
# =============================================================================


def detect_environment() -> dict[str, Any]:
    """
    Detect current environment characteristics.

    Returns:
        Dict[str, Any]: Environment information
    """
    import platform

    env_info: dict[str, Any] = {
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python_version": platform.python_version(),
        },
        "docker": {
            "socket_exists": Path("/var/run/docker.sock").exists(),
            "in_container": Path("/.dockerenv").exists(),
        },
        "suggested_profile": _suggest_deployment_profile(),
    }

    # Add resource information if psutil is available
    if PSUTIL_AVAILABLE and _psutil:
        try:
            env_info["resources"] = {
                "cpu_count": _psutil.cpu_count(),
                "memory_gb": round(_psutil.virtual_memory().total / (1024**3), 1),
                "disk_free_gb": round(_psutil.disk_usage("/").free / (1024**3), 1),
            }
        except Exception:
            # If psutil fails, add placeholder values
            env_info["resources"] = {
                "cpu_count": 1,
                "memory_gb": 1.0,
                "disk_free_gb": 10.0,
            }
    else:
        # Fallback values when psutil is not available
        env_info["resources"] = {
            "cpu_count": 1,
            "memory_gb": 1.0,
            "disk_free_gb": 10.0,
        }

    return env_info


def _suggest_deployment_profile() -> str:
    """Suggest deployment profile based on environment detection"""

    # Check for production indicators
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        return "production"  # Running in Kubernetes

    if os.getenv("NODE_ENV") == "production":
        return "production"

    # Check for development indicators
    if os.getenv("NODE_ENV") == "development" or os.getenv("DEBUG"):
        return "development"

    # Check resource constraints (likely Raspberry Pi or home lab)
    if PSUTIL_AVAILABLE and _psutil:
        try:
            memory_gb = _psutil.virtual_memory().total / (1024**3)
            if memory_gb < 2:
                return "homelab"  # Low memory suggests home lab
        except Exception:
            # Silently handle psutil errors - this is environment detection, not critical
            pass  # nosec B110

    # Default to home lab for unknown environments
    return "homelab"


# =============================================================================
# Configuration Export and Import
# =============================================================================


def export_config_template(profile: DeploymentProfile) -> str:
    """
    Export configuration template for a deployment profile.

    Args:
        profile: Deployment profile

    Returns:
        str: Environment variable template
    """
    # Create settings with profile defaults
    temp_settings = AppSettings(deployment_profile=profile)

    template_lines = [
        f"# Harbor Configuration Template - {profile.value.title()} Profile",
        f"# Generated for Harbor v{temp_settings.app_version}",
        "",
        "# ===== CORE CONFIGURATION =====",
        f"HARBOR_MODE={profile.value}",
        f"HARBOR_DEBUG={str(temp_settings.debug).lower()}",
        "",
        "# ===== SECURITY =====",
        f"HARBOR_SECURITY_REQUIRE_HTTPS={str(temp_settings.security.require_https).lower()}",
        f"HARBOR_SECURITY_SESSION_TIMEOUT_HOURS={temp_settings.security.session_timeout_hours}",
        f"HARBOR_SECURITY_API_KEY_REQUIRED={str(temp_settings.security.api_key_required).lower()}",
        "# HARBOR_SECURITY_SECRET_KEY=  # Generate with: openssl rand -base64 32",
        "",
        "# ===== UPDATES =====",
        f"HARBOR_UPDATE_DEFAULT_CHECK_INTERVAL_SECONDS={temp_settings.updates.default_check_interval_seconds}",
        f"HARBOR_UPDATE_DEFAULT_UPDATE_TIME={temp_settings.updates.default_update_time}",
        f"HARBOR_UPDATE_MAX_CONCURRENT_UPDATES={temp_settings.updates.max_concurrent_updates}",
        "",
        "# ===== LOGGING =====",
        f"HARBOR_LOG_LOG_LEVEL={temp_settings.logging.log_level.value}",
        f"HARBOR_LOG_LOG_FORMAT={temp_settings.logging.log_format.value}",
        f"HARBOR_LOG_LOG_RETENTION_DAYS={temp_settings.logging.log_retention_days}",
        "",
        "# ===== FEATURES =====",
        f"HARBOR_FEATURE_ENABLE_AUTO_DISCOVERY={str(temp_settings.features.enable_auto_discovery).lower()}",
        f"HARBOR_FEATURE_SHOW_GETTING_STARTED={str(temp_settings.features.show_getting_started).lower()}",
        f"HARBOR_FEATURE_ENABLE_SIMPLE_MODE={str(temp_settings.features.enable_simple_mode).lower()}",
        "",
    ]

    return "\n".join(template_lines)


if __name__ == "__main__":
    """Configuration testing and utilities"""
    import json

    print("🛳️ Harbor Configuration System")
    print("=" * 40)

    # Show current configuration
    settings = get_settings()
    summary = get_config_summary()

    print(f"Profile: {settings.deployment_profile.value}")
    print(f"Version: {settings.app_version}")
    print(f"Data directory: {settings.data_dir}")
    print(f"Database: {settings.database.database_type.value}")
    print(f"Log level: {settings.logging.log_level.value}")
    print()

    # Validate runtime requirements
    errors = validate_runtime_requirements()
    if errors:
        print("⚠️ Configuration Issues:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✅ Configuration valid")

    print()
    print("Configuration Summary:")
    print(json.dumps(summary, indent=2, default=str))
