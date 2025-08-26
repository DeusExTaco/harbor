"""
Harbor Configuration System - Base Configuration Module

This module provides the core configuration system for Harbor, supporting:
- Profile-based configuration (homelab, development, staging, production)
- Environment variable overrides with HARBOR_ prefix
- Validation with clear error messages
- Secrets management integration
- Hot reload capability for development

Author: Harbor Team
License: MIT
"""

import logging
import os
import secrets
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import (
    Field,
    SecretStr,
    field_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


# Configure logging
logger = logging.getLogger(__name__)


# =============================================================================
# Deployment Profiles
# =============================================================================


class DeploymentProfile(str, Enum):
    """
    Deployment profile enumeration.

    Each profile optimizes Harbor for different use cases:
    - HOMELAB: Zero-config home lab deployment with sensible defaults
    - DEVELOPMENT: Local development with debugging and hot reload
    - STAGING: Pre-production testing environment
    - PRODUCTION: Enterprise production with security hardening
    """

    HOMELAB = "homelab"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Log level enumeration."""

    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(str, Enum):
    """Log format enumeration."""

    TEXT = "text"
    JSON = "json"


# =============================================================================
# Nested Configuration Models
# =============================================================================


class SecuritySettings(BaseSettings):
    """Security configuration settings."""

    # Core security - all fields now have defaults
    secret_key: SecretStr | None = Field(default=None)
    secret_key_file: Path | None = Field(default=None)
    require_https: bool = Field(default=False)

    # Session management
    session_timeout_hours: int = Field(default=168)  # 1 week default
    session_secure_cookies: bool = Field(default=False)

    # Authentication
    api_key_required: bool = Field(default=False)
    password_min_length: int = Field(default=6)
    password_require_special: bool = Field(default=False)

    # Rate limiting
    api_rate_limit_per_hour: int = Field(default=1000)

    # Future features (disabled in v1.0)
    mfa_enabled: bool = Field(default=False)  # TODO: M7+

    model_config = SettingsConfigDict(
        env_prefix="HARBOR_SECURITY_", case_sensitive=False, extra="ignore"
    )

    def get_secret_key(self) -> str:
        """Get the secret key from configuration or file."""
        if self.secret_key:
            return self.secret_key.get_secret_value()
        elif self.secret_key_file and self.secret_key_file.exists():
            return self.secret_key_file.read_text().strip()
        else:
            # Generate a random key for development/testing
            generated_key = secrets.token_urlsafe(32)
            logger.warning(
                "No secret key configured, using generated key (not for production)"
            )
            return generated_key


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    type: str = Field("sqlite", alias="database_type")
    database_url: str | None = Field(None)

    # Connection pool settings
    pool_size: int = Field(5)
    max_overflow: int = Field(2)
    pool_timeout: int = Field(30)
    echo_sql: bool = Field(False)

    # Backup settings
    backup_enabled: bool = Field(True)
    backup_retention_days: int = Field(7)
    backup_schedule: str = Field("0 2 * * *")

    model_config = SettingsConfigDict(
        env_prefix="HARBOR_DB_",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    def get_database_url(self, data_dir: Path) -> str:
        """Get the database URL based on configuration."""
        if self.database_url:
            return self.database_url
        elif self.type == "sqlite":
            db_path = data_dir / "harbor.db"
            return f"sqlite:///{db_path}"
        else:
            raise ValueError("Database URL must be specified for non-SQLite databases")


class DockerSettings(BaseSettings):
    """Docker runtime configuration settings."""

    host: str = Field("unix:///var/run/docker.sock")
    timeout: int = Field(60)

    # Discovery settings
    discovery_interval_seconds: int = Field(300)
    include_stopped_containers: bool = Field(True)

    # Safety patterns
    exclude_patterns: list[str] = Field(
        default_factory=lambda: ["harbor*", "*_backup", "*_migrate"]
    )

    model_config = SettingsConfigDict(
        env_prefix="HARBOR_DOCKER_", case_sensitive=False, extra="ignore"
    )

    @field_validator("exclude_patterns", mode="before")
    @classmethod
    def parse_exclude_patterns(cls, v):
        """Parse exclude patterns from environment variable."""
        if isinstance(v, str):
            return [p.strip() for p in v.split(",") if p.strip()]
        return v


class UpdateSettings(BaseSettings):
    """Container update configuration settings."""

    # Scheduling
    default_check_interval_seconds: int = Field(86400)  # 24 hours
    default_update_time: str = Field("03:00")
    default_timezone: str = Field("UTC")

    # Concurrency
    max_concurrent_updates: int = Field(2)
    update_delay_seconds: int = Field(0)

    # Safety settings
    default_health_check_timeout: int = Field(60)
    default_rollback_enabled: bool = Field(True)
    rollback_timeout_seconds: int = Field(300)

    # Cleanup settings
    default_cleanup_enabled: bool = Field(True)
    default_cleanup_keep_images: int = Field(2)
    cleanup_delay_hours: int = Field(24)

    model_config = SettingsConfigDict(
        env_prefix="HARBOR_UPDATE_", case_sensitive=False, extra="ignore"
    )


class RegistrySettings(BaseSettings):
    """Container registry configuration settings."""

    timeout_seconds: int = Field(30)
    retry_count: int = Field(3)

    # Caching
    cache_ttl_seconds: int = Field(3600)
    cache_size_mb: int = Field(50)

    # Rate limiting
    rate_limit_calls_per_hour: int = Field(100)

    model_config = SettingsConfigDict(
        env_prefix="HARBOR_REGISTRY_", case_sensitive=False, extra="ignore"
    )


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""

    level: LogLevel = Field(LogLevel.INFO, alias="log_level")
    format: LogFormat = Field(LogFormat.TEXT, alias="log_format")

    # File logging
    to_file: bool = Field(True)
    file_path: Path | None = Field(None)
    rotation_size_mb: int = Field(10)
    retention_days: int = Field(14)

    # Console logging
    to_console: bool = Field(True)

    model_config = SettingsConfigDict(
        env_prefix="HARBOR_LOG_",
        case_sensitive=False,
        use_enum_values=True,
        extra="ignore",
        populate_by_name=True,
    )


class ResourceSettings(BaseSettings):
    """Resource limit configuration settings."""

    max_memory_usage_mb: int = Field(512)
    max_disk_usage_gb: int = Field(10)
    max_workers: int | str = Field("auto")

    model_config = SettingsConfigDict(
        env_prefix="HARBOR_RESOURCE_", case_sensitive=False, extra="ignore"
    )

    def get_worker_count(self) -> int:
        """Get the number of worker processes."""
        if isinstance(self.max_workers, int):
            return self.max_workers
        elif self.max_workers == "auto":
            import multiprocessing

            return min(multiprocessing.cpu_count(), 4)
        else:
            try:
                return int(self.max_workers)
            except ValueError:
                return 2  # Default fallback


class FeatureFlags(BaseSettings):
    """Feature flag configuration settings."""

    # v1.0 Core features (M0-M6) - Always enabled
    enable_auto_discovery: bool = Field(True)
    enable_metrics: bool = Field(True)
    enable_health_checks: bool = Field(True)

    # Home lab UX features
    show_getting_started: bool = Field(True)
    enable_simple_mode: bool = Field(True)
    auto_exclude_harbor: bool = Field(True)

    # Future features (v1.1+) - Behind feature flags
    enable_mfa: bool = Field(False)  # TODO: M7+
    enable_multi_user: bool = Field(False)  # TODO: M8+
    enable_rbac: bool = Field(False)  # TODO: M8+
    enable_blue_green: bool = Field(False)  # TODO: M8+
    enable_canary: bool = Field(False)  # TODO: M8+
    enable_ldap: bool = Field(False)  # TODO: M9+
    enable_kubernetes: bool = Field(False)  # TODO: M9+
    enable_slack: bool = Field(False)  # TODO: M7+
    enable_email: bool = Field(False)  # TODO: M7+

    model_config = SettingsConfigDict(
        env_prefix="HARBOR_FEATURE_", case_sensitive=False, extra="ignore"
    )


# =============================================================================
# Main Configuration Class
# =============================================================================


class HarborConfig(BaseSettings):
    """
    Main Harbor configuration class.

    This class manages all configuration for Harbor, including:
    - Environment variable overrides
    - Profile-based configuration
    - Configuration validation
    - Secret management
    """

    # Core settings
    mode: DeploymentProfile = Field(DeploymentProfile.HOMELAB)
    debug: bool = Field(False)
    host: str = Field("0.0.0.0")
    port: int = Field(8080)

    # Application metadata
    app_name: str = Field("Harbor Container Updater")
    version: str = Field("0.1.0")

    # Directory paths
    data_dir: Path = Field(Path("/app/data"))
    logs_dir: Path = Field(Path("/app/logs"))
    config_dir: Path = Field(Path("/app/config"))

    # Nested configuration - No default factories, these will be set during initialization
    security: SecuritySettings
    database: DatabaseSettings
    docker: DockerSettings
    updates: UpdateSettings
    registry: RegistrySettings
    logging: LoggingSettings
    resources: ResourceSettings
    features: FeatureFlags

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="HARBOR_",
        extra="ignore",
    )

    def __init__(self, **data):
        """Initialize configuration with profile-based defaults."""
        super().__init__(**data)

        # Create directories if they don't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Apply profile-based configuration
        self._apply_profile_defaults()

    def _apply_profile_defaults(self):
        """Apply profile-specific default values."""
        if self.mode == DeploymentProfile.HOMELAB:
            self._apply_homelab_defaults()
        elif self.mode == DeploymentProfile.DEVELOPMENT:
            self._apply_development_defaults()
        elif self.mode == DeploymentProfile.STAGING:
            self._apply_staging_defaults()
        elif self.mode == DeploymentProfile.PRODUCTION:
            self._apply_production_defaults()

    def _apply_homelab_defaults(self):
        """Apply home lab optimized defaults."""
        # Security: Relaxed for ease of use
        if not os.getenv("HARBOR_SECURITY_REQUIRE_HTTPS"):
            self.security.require_https = False
        if not os.getenv("HARBOR_SECURITY_SESSION_TIMEOUT_HOURS"):
            self.security.session_timeout_hours = 168  # 1 week

        # Updates: Conservative and safe
        if not os.getenv("HARBOR_UPDATE_DEFAULT_CHECK_INTERVAL_SECONDS"):
            self.updates.default_check_interval_seconds = 86400  # Daily
        if not os.getenv("HARBOR_UPDATE_MAX_CONCURRENT_UPDATES"):
            self.updates.max_concurrent_updates = 2

        # Resources: Efficient for home hardware
        if not os.getenv("HARBOR_RESOURCE_MAX_MEMORY_USAGE_MB"):
            self.resources.max_memory_usage_mb = 256

        # Logging: Simple
        if not os.getenv("HARBOR_LOG_LOG_FORMAT"):
            self.logging.format = LogFormat.TEXT

    def _apply_development_defaults(self):
        """Apply development environment defaults."""
        # Enable debugging
        self.debug = True

        # Security: Very relaxed
        self.security.require_https = False
        self.security.session_timeout_hours = 72  # 3 days
        self.security.api_key_required = False

        # Updates: Frequent for testing
        self.updates.default_check_interval_seconds = 300  # 5 minutes
        self.updates.max_concurrent_updates = 3

        # Database: Enable SQL logging
        self.database.echo_sql = True

        # Logging: Verbose
        self.logging.level = LogLevel.DEBUG

    def _apply_staging_defaults(self):
        """Apply staging environment defaults."""
        # Security: Moderate
        self.security.require_https = True
        self.security.session_timeout_hours = 24

        # Updates: Production-like
        self.updates.default_check_interval_seconds = 21600  # 6 hours
        self.updates.max_concurrent_updates = 5

        # Logging: JSON format
        self.logging.format = LogFormat.JSON

    def _apply_production_defaults(self):
        """Apply production environment defaults."""
        # Security: Strict
        self.security.require_https = True
        self.security.session_timeout_hours = 8
        self.security.api_key_required = True
        self.security.password_min_length = 12

        # Updates: Production scale
        self.updates.default_check_interval_seconds = 21600  # 6 hours
        self.updates.max_concurrent_updates = 10

        # Database: Production settings
        self.database.pool_size = 20
        self.database.max_overflow = 10

        # Resources: Production scale
        self.resources.max_memory_usage_mb = 2048

        # Logging: Production format
        self.logging.format = LogFormat.JSON
        self.logging.level = LogLevel.INFO

    def get_database_url(self) -> str:
        """Get the complete database URL."""
        return self.database.get_database_url(self.data_dir)

    def get_secret_key(self) -> str:
        """Get the application secret key."""
        return self.security.get_secret_key()

    def validate_configuration(self) -> list[str]:
        """
        Validate the configuration and return any warnings.

        Returns:
            List of warning messages
        """
        warnings = []

        # Check security settings
        if self.mode == DeploymentProfile.PRODUCTION:
            if not self.security.require_https:
                warnings.append("HTTPS should be enabled in production")
            if self.security.session_timeout_hours > 24:
                warnings.append("Session timeout is very long for production")
            if self.security.password_min_length < 8:
                warnings.append(
                    "Password minimum length should be at least 8 for production"
                )

        # Check database settings
        if self.mode == DeploymentProfile.PRODUCTION and self.database.type == "sqlite":
            warnings.append("Consider using PostgreSQL for production deployments")

        # Check resource settings
        if self.resources.max_memory_usage_mb < 128:
            warnings.append("Memory limit is very low, may cause performance issues")

        return warnings

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump(mode="python", exclude_none=True)

    def to_yaml(self) -> str:
        """Convert configuration to YAML format."""
        import yaml

        return yaml.safe_dump(self.to_dict(), default_flow_style=False)


# =============================================================================
# Configuration Factory
# =============================================================================


# app/config/base.py - In the load_config function, add type: ignore comments


def load_config(
    profile: str | None = None, config_file: Path | None = None, validate: bool = True
) -> HarborConfig:
    """
    Load Harbor configuration.

    Args:
        profile: Override deployment profile
        config_file: Optional configuration file path
        validate: Whether to validate configuration

    Returns:
        HarborConfig: Loaded and validated configuration

    Raises:
        ValidationError: If configuration is invalid
    """
    # Override profile if specified
    if profile:
        os.environ["HARBOR_MODE"] = profile

    # Load configuration file if specified
    if config_file and config_file.exists():
        import yaml

        with open(config_file) as f:
            config_data = yaml.safe_load(f)

        # Set environment variables from config file
        for key, value in config_data.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    env_key = f"HARBOR_{key.upper()}_{sub_key.upper()}"
                    if env_key not in os.environ:
                        os.environ[env_key] = str(sub_value)
            else:
                env_key = f"HARBOR_{key.upper()}"
                if env_key not in os.environ:
                    os.environ[env_key] = str(value)

    # Get deployment profile
    deployment_profile = DeploymentProfile(os.getenv("HARBOR_MODE", "homelab"))

    # Create nested settings with type ignore since we know they'll read from env
    config = HarborConfig(
        mode=deployment_profile,
        debug=os.getenv("HARBOR_DEBUG", "false").lower() == "true",
        host=os.getenv("HARBOR_HOST", "0.0.0.0"),
        port=int(os.getenv("HARBOR_PORT", "8080")),
        app_name=os.getenv("HARBOR_APP_NAME", "Harbor Container Updater"),
        version=os.getenv("HARBOR_VERSION", "0.1.0"),
        data_dir=Path(os.getenv("HARBOR_DATA_DIR", "/app/data")),
        logs_dir=Path(os.getenv("HARBOR_LOGS_DIR", "/app/logs")),
        config_dir=Path(os.getenv("HARBOR_CONFIG_DIR", "/app/config")),
        security=SecuritySettings(),
        database=DatabaseSettings(),  # type: ignore[call-arg]
        docker=DockerSettings(),  # type: ignore[call-arg]
        updates=UpdateSettings(),  # type: ignore[call-arg]
        registry=RegistrySettings(),  # type: ignore[call-arg]
        logging=LoggingSettings(),  # type: ignore[call-arg]
        resources=ResourceSettings(),  # type: ignore[call-arg]
        features=FeatureFlags(),  # type: ignore[call-arg]
    )

    # Apply profile defaults
    config._apply_profile_defaults()

    # Validate if requested
    if validate:
        warnings = config.validate_configuration()
        for warning in warnings:
            logger.warning(f"Configuration warning: {warning}")

    return config


# =============================================================================
# Singleton Configuration Instance
# =============================================================================

_config: HarborConfig | None = None


def get_config() -> HarborConfig:
    """Get the singleton configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reset_config():
    """Reset the singleton configuration instance."""
    global _config
    _config = None
