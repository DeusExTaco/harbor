"""
Harbor Feature Flags Configuration

This module defines feature flags for Harbor's development roadmap, clearly
separating v1.0 (home lab focused) features from future enterprise features.

Feature flags allow us to:
1. Build enterprise infrastructure while keeping it disabled
2. Test future features in development without affecting users
3. Enable features progressively based on deployment profile
4. Maintain clean separation between home lab and enterprise complexity

Author: Harbor Team
License: MIT
"""

import logging
from dataclasses import dataclass
from typing import Any

from app.config.base import DeploymentProfile


logger = logging.getLogger(__name__)


# =============================================================================
# Feature Flag Categories
# =============================================================================


@dataclass
class AuthFeatures:
    """Authentication and Authorization Features"""

    # v1.0 Features (M0-M6) - ACTIVE
    single_user_auth: bool = True  # Single admin user (M0)
    session_auth: bool = True  # Session-based auth (M0)
    api_key_auth: bool = True  # Single API key (M0)
    csrf_protection: bool = True  # CSRF tokens (M0)
    password_strength: bool = True  # Password validation (M0)

    # v1.1+ Features (M7+) - BEHIND FLAGS
    enable_mfa: bool = False  # TODO: M7+ Multi-factor auth (TOTP)
    enable_backup_codes: bool = False  # TODO: M7+ MFA backup codes
    enable_multi_user: bool = False  # TODO: M8+ Multiple users
    enable_rbac: bool = False  # TODO: M8+ Role-based access
    enable_api_key_scoping: bool = False  # TODO: M8+ Scoped API keys
    enable_ldap: bool = False  # TODO: M9+ LDAP integration
    enable_saml: bool = False  # TODO: M9+ SAML SSO
    enable_oauth: bool = False  # TODO: M9+ OAuth providers


@dataclass
class RuntimeFeatures:
    """Container Runtime Features"""

    # v1.0 Features (M0-M6) - ACTIVE
    docker_runtime: bool = True  # Docker support (M1)
    docker_socket: bool = True  # Direct socket access (M1)
    docker_socket_proxy: bool = True  # Socket proxy support (M1)
    container_discovery: bool = True  # Auto-discovery (M1)

    # v1.1+ Features (M7+) - BEHIND FLAGS
    enable_kubernetes: bool = False  # TODO: M9+ Kubernetes runtime
    enable_podman: bool = False  # TODO: M10+ Podman runtime
    enable_docker_swarm: bool = False  # TODO: M11+ Docker Swarm
    enable_containerd: bool = False  # TODO: M12+ Containerd direct


@dataclass
class UpdateFeatures:
    """Container Update Features"""

    # v1.0 Features (M0-M6) - ACTIVE
    rolling_updates: bool = True  # Rolling update strategy (M2)
    health_checks: bool = True  # Health verification (M2)
    automatic_rollback: bool = True  # Failed update rollback (M2)
    manual_rollback: bool = True  # User-initiated rollback (M2)
    dry_run_mode: bool = True  # Update simulation (M2)
    update_scheduling: bool = True  # Scheduled updates (M3)

    # v1.1+ Features (M7+) - BEHIND FLAGS
    enable_blue_green: bool = False  # TODO: M7+ Blue/green deployment
    enable_canary: bool = False  # TODO: M8+ Canary deployments
    enable_batch_updates: bool = False  # TODO: M8+ Batch processing
    enable_dependency_order: bool = False  # TODO: M9+ Dependency-aware updates
    enable_approval_workflow: bool = False  # TODO: M10+ Manual approval gates


@dataclass
class MonitoringFeatures:
    """Monitoring and Observability Features"""

    # v1.0 Features (M0-M6) - ACTIVE
    health_endpoints: bool = True  # Basic health checks (M0)
    structured_logging: bool = True  # JSON logging (M0)
    prometheus_metrics: bool = True  # Metrics collection (M4)
    basic_dashboards: bool = True  # Simple UI dashboards (M4)
    log_retention: bool = True  # Log rotation (M0)

    # v1.1+ Features (M7+) - BEHIND FLAGS
    enable_tracing: bool = False  # TODO: M7+ Distributed tracing
    enable_alerting: bool = False  # TODO: M7+ Alert manager integration
    enable_log_aggregation: bool = False  # TODO: M8+ ELK/Loki integration
    enable_apm: bool = False  # TODO: M8+ Application performance monitoring
    enable_custom_metrics: bool = False  # TODO: M9+ User-defined metrics


@dataclass
class UIFeatures:
    """User Interface Features"""

    # v1.0 Features (M0-M6) - ACTIVE
    web_interface: bool = True  # Basic web UI (M0)
    getting_started: bool = True  # Setup wizard (M3)
    simple_mode: bool = True  # Simplified UI (M3)
    mobile_responsive: bool = True  # Mobile support (M3)
    dark_theme: bool = True  # Dark/light themes (M3)
    real_time_updates: bool = True  # Live updates (M3)

    # v1.1+ Features (M7+) - BEHIND FLAGS
    enable_advanced_mode: bool = False  # TODO: M7+ Advanced power-user UI
    enable_custom_dashboards: bool = False  # TODO: M8+ User-customizable dashboards
    enable_cli_interface: bool = False  # TODO: M8+ Command-line interface
    enable_mobile_app: bool = False  # TODO: M12+ Native mobile app
    enable_desktop_app: bool = False  # TODO: M12+ Electron desktop app


@dataclass
class DataFeatures:
    """Data Management Features"""

    # v1.0 Features (M0-M6) - ACTIVE
    sqlite_database: bool = True  # SQLite support (M0)
    automatic_backups: bool = True  # Database backups (M0)
    data_retention: bool = True  # Automatic cleanup (M0)
    audit_logging: bool = True  # Basic audit trail (M0)

    # v1.1+ Features (M7+) - BEHIND FLAGS
    enable_postgresql: bool = False  # TODO: M7+ PostgreSQL support
    enable_mysql: bool = False  # TODO: M8+ MySQL support
    enable_ha_database: bool = False  # TODO: M9+ High availability
    enable_data_encryption: bool = False  # TODO: M9+ Database encryption
    enable_backup_encryption: bool = False  # TODO: M9+ Encrypted backups
    enable_compliance_export: bool = False  # TODO: M10+ Compliance reporting


@dataclass
class IntegrationFeatures:
    """External Integration Features"""

    # v1.0 Features (M0-M6) - ACTIVE
    docker_hub: bool = True  # Docker Hub registry (M1)
    private_registries: bool = True  # Private registry support (M1)
    webhook_notifications: bool = True  # Basic webhooks (M4)

    # v1.1+ Features (M7+) - BEHIND FLAGS
    enable_slack: bool = False  # TODO: M7+ Slack notifications
    enable_discord: bool = False  # TODO: M7+ Discord notifications
    enable_teams: bool = False  # TODO: M7+ Microsoft Teams
    enable_email: bool = False  # TODO: M7+ Email notifications
    enable_sms: bool = False  # TODO: M8+ SMS notifications
    enable_ci_cd: bool = False  # TODO: M8+ CI/CD integrations
    enable_iac: bool = False  # TODO: M9+ Infrastructure as Code
    enable_gitops: bool = False  # TODO: M10+ GitOps workflows


@dataclass
class SecurityFeatures:
    """Security Features"""

    # v1.0 Features (M0-M6) - ACTIVE
    basic_auth: bool = True  # Username/password (M0)
    session_security: bool = True  # Secure sessions (M0)
    input_validation: bool = True  # Input sanitization (M0)
    rate_limiting: bool = True  # Basic rate limits (M0)
    security_headers: bool = True  # HTTP security headers (M0)

    # v1.1+ Features (M7+) - BEHIND FLAGS
    enable_advanced_auth: bool = False  # TODO: M7+ Advanced auth methods
    enable_security_scanning: bool = False  # TODO: M7+ Vulnerability scanning
    enable_penetration_testing: bool = False  # TODO: M8+ Automated pen testing
    enable_compliance_mode: bool = False  # TODO: M9+ Compliance frameworks
    enable_zero_trust: bool = False  # TODO: M10+ Zero trust architecture


@dataclass
class DeploymentFeatures:
    """Deployment and Scaling Features"""

    # v1.0 Features (M0-M6) - ACTIVE
    single_instance: bool = True  # Single container deployment (M0)
    docker_compose: bool = True  # Docker Compose support (M0)
    auto_discovery: bool = True  # Container auto-discovery (M1)

    # v1.1+ Features (M7+) - BEHIND FLAGS
    enable_clustering: bool = False  # TODO: M8+ Multi-instance clustering
    enable_load_balancing: bool = False  # TODO: M8+ Load balancer integration
    enable_auto_scaling: bool = False  # TODO: M9+ Horizontal auto-scaling
    enable_ha_deployment: bool = False  # TODO: M9+ High availability
    enable_multi_region: bool = False  # TODO: M11+ Multi-region deployment


# =============================================================================
# Feature Flag Container
# =============================================================================


@dataclass
class FeatureFlags:
    """Complete feature flag configuration"""

    auth: AuthFeatures
    runtime: RuntimeFeatures
    updates: UpdateFeatures
    monitoring: MonitoringFeatures
    ui: UIFeatures
    data: DataFeatures
    integrations: IntegrationFeatures
    security: SecurityFeatures
    deployment: DeploymentFeatures


# =============================================================================
# Profile-Based Feature Configuration
# =============================================================================


def get_homelab_features() -> FeatureFlags:
    """Home lab optimized feature configuration (v1.0 focus)"""
    return FeatureFlags(
        auth=AuthFeatures(
            # Keep it simple for home labs
            single_user_auth=True,
            session_auth=True,
            api_key_auth=True,
            csrf_protection=True,
            # Future features disabled
            enable_mfa=False,
            enable_multi_user=False,
            enable_rbac=False,
        ),
        runtime=RuntimeFeatures(
            docker_runtime=True,
            docker_socket=True,
            docker_socket_proxy=True,
            container_discovery=True,
            # Future runtimes disabled
            enable_kubernetes=False,
            enable_podman=False,
        ),
        updates=UpdateFeatures(
            rolling_updates=True,
            health_checks=True,
            automatic_rollback=True,
            dry_run_mode=True,
            update_scheduling=True,
            # Advanced strategies disabled
            enable_blue_green=False,
            enable_canary=False,
        ),
        monitoring=MonitoringFeatures(
            health_endpoints=True,
            structured_logging=True,
            prometheus_metrics=True,
            basic_dashboards=True,
            # Advanced monitoring disabled
            enable_tracing=False,
            enable_alerting=False,
        ),
        ui=UIFeatures(
            web_interface=True,
            getting_started=True,
            simple_mode=True,
            mobile_responsive=True,
            real_time_updates=True,
            # Advanced UI disabled
            enable_advanced_mode=False,
            enable_custom_dashboards=False,
        ),
        data=DataFeatures(
            sqlite_database=True,
            automatic_backups=True,
            data_retention=True,
            audit_logging=True,
            # Enterprise data features disabled
            enable_postgresql=False,
            enable_ha_database=False,
        ),
        integrations=IntegrationFeatures(
            docker_hub=True,
            private_registries=True,
            webhook_notifications=True,
            # Advanced integrations disabled
            enable_slack=False,
            enable_email=False,
        ),
        security=SecurityFeatures(
            basic_auth=True,
            session_security=True,
            input_validation=True,
            rate_limiting=True,
            # Advanced security disabled
            enable_advanced_auth=False,
            enable_security_scanning=False,
        ),
        deployment=DeploymentFeatures(
            single_instance=True,
            docker_compose=True,
            auto_discovery=True,
            # Scaling features disabled
            enable_clustering=False,
            enable_load_balancing=False,
        ),
    )


def get_development_features() -> FeatureFlags:
    """Development environment with some future features enabled for testing"""
    features = get_homelab_features()

    # Enable select future features for development/testing
    features.auth.enable_mfa = True  # Test MFA implementation
    features.data.enable_postgresql = True  # Test PostgreSQL
    features.monitoring.enable_tracing = True  # Test tracing

    return features


def get_staging_features() -> FeatureFlags:
    """Staging environment for testing enterprise features"""
    features = get_development_features()

    # Enable more enterprise features for staging testing
    features.auth.enable_multi_user = True
    features.auth.enable_rbac = True
    features.updates.enable_blue_green = True
    features.monitoring.enable_alerting = True
    features.deployment.enable_clustering = True

    return features


def get_production_features() -> FeatureFlags:
    """Production environment - conservative feature set"""
    # Start with home lab features
    features = get_homelab_features()

    # Enable only stable enterprise features
    features.data.enable_postgresql = True  # Stable database option
    features.security.enable_advanced_auth = True  # Enhanced security
    features.monitoring.enable_alerting = True  # Production monitoring

    return features


# =============================================================================
# Feature Flag Factory
# =============================================================================


def get_feature_flags(deployment_profile: DeploymentProfile) -> FeatureFlags:
    """
    Get feature flags based on deployment profile

    Args:
        deployment_profile: Deployment profile enum

    Returns:
        FeatureFlags: Profile-specific feature configuration
    """
    profile_map = {
        DeploymentProfile.HOMELAB: get_homelab_features,
        DeploymentProfile.DEVELOPMENT: get_development_features,
        DeploymentProfile.STAGING: get_staging_features,
        DeploymentProfile.PRODUCTION: get_production_features,
    }

    feature_func = profile_map.get(deployment_profile, get_homelab_features)
    return feature_func()


# =============================================================================
# Feature Flag Utilities
# =============================================================================


def is_feature_enabled(feature_path: str, flags: FeatureFlags) -> bool:
    """
    Check if a specific feature is enabled using dot notation

    Args:
        feature_path: Dot-separated path like "auth.enable_mfa"
        flags: FeatureFlags instance

    Returns:
        bool: True if feature is enabled

    Example:
        >>> flags = get_feature_flags(DeploymentProfile.HOMELAB)
        >>> is_feature_enabled("auth.enable_mfa", flags)
        False
        >>> is_feature_enabled("auth.single_user_auth", flags)
        True
    """
    try:
        parts = feature_path.split(".")
        obj = flags

        for part in parts:
            obj = getattr(obj, part)

        return bool(obj)
    except AttributeError:
        logger.warning(f"Feature flag '{feature_path}' not found")
        return False


def get_enabled_features(flags: FeatureFlags) -> dict[str, Any]:
    """
    Get a dictionary of all enabled features for debugging/reporting

    Args:
        flags: FeatureFlags instance

    Returns:
        Dict[str, Any]: Nested dictionary of enabled features
    """
    result: dict[str, dict[str, bool]] = {}

    for category_name in [
        "auth",
        "runtime",
        "updates",
        "monitoring",
        "ui",
        "data",
        "integrations",
        "security",
        "deployment",
    ]:
        category = getattr(flags, category_name)
        result[category_name] = {}

        for field_name in category.__dataclass_fields__:
            field_value = getattr(category, field_name)
            if field_value:  # Only include enabled features
                result[category_name][field_name] = field_value

    return result


def require_feature(feature_path: str):
    """
    Decorator to enforce feature flag requirements

    Args:
        feature_path: Dot-separated feature path

    Example:
        @require_feature("auth.enable_mfa")
        def setup_mfa_for_user(user_id: int):
            # This function only runs if MFA is enabled
            pass
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            # Get feature flags from current app context
            from app.config import get_config

            config = get_config()
            flags = get_feature_flags(config.mode)

            if not is_feature_enabled(feature_path, flags):
                raise NotImplementedError(
                    f"Feature '{feature_path}' is not enabled in {config.mode.value} profile. "
                    f"This feature is planned for a future release."
                )

            return func(*args, **kwargs)

        return wrapper

    return decorator


# =============================================================================
# Migration Roadmap Comments
# =============================================================================

"""
MIGRATION ROADMAP - Feature Enablement Schedule

M7 (Month 1-3 Post-Release):
- auth.enable_mfa: Multi-factor authentication
- auth.enable_backup_codes: MFA backup codes
- updates.enable_blue_green: Blue/green deployments
- monitoring.enable_tracing: Distributed tracing
- integrations.enable_slack: Slack notifications
- security.enable_advanced_auth: Enhanced authentication

M8 (Month 4-6):
- auth.enable_multi_user: Multiple user accounts
- auth.enable_rbac: Role-based access control
- auth.enable_api_key_scoping: Scoped API keys
- updates.enable_canary: Canary deployments
- updates.enable_batch_updates: Batch processing
- monitoring.enable_alerting: Alert manager integration
- ui.enable_advanced_mode: Power-user interface
- data.enable_postgresql: PostgreSQL support
- deployment.enable_clustering: Multi-instance clustering

M9 (Month 7-12):
- auth.enable_ldap: LDAP integration
- runtime.enable_kubernetes: Kubernetes runtime
- updates.enable_dependency_order: Dependency-aware updates
- monitoring.enable_apm: Application performance monitoring
- data.enable_ha_database: High availability database
- security.enable_compliance_mode: Compliance frameworks
- deployment.enable_auto_scaling: Horizontal auto-scaling

M10+ (Year 2+):
- auth.enable_saml: SAML SSO
- runtime.enable_podman: Podman runtime support
- updates.enable_approval_workflow: Manual approval gates
- integrations.enable_gitops: GitOps workflows
- security.enable_zero_trust: Zero trust architecture
- deployment.enable_multi_region: Multi-region deployment

This roadmap ensures we deliver value incrementally while building toward
enterprise capabilities without compromising the home lab experience.
"""
