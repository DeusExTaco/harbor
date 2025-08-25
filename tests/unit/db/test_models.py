# tests/unit/db/test_models.py
"""
Unit tests for Harbor database models

Tests for User, APIKey, SystemSettings, Container, and ContainerPolicy models.
"""

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.config import DeploymentProfile
from app.db.models.api_key import APIKey
from app.db.models.container import Container
from app.db.models.policy import ContainerPolicy
from app.db.models.settings import SystemSettings
from app.db.models.user import User


# =============================================================================
# User Model Tests
# =============================================================================


@pytest.mark.database
class TestUserModel:
    """Test User model functionality"""

    async def test_create_user(self, async_session):
        """Test creating a new user"""
        user = User(
            username="testuser",
            password_hash="$argon2id$v=19$m=65536,t=3,p=4$test_hash",
            email="test@example.com",
            display_name="Test User",
            is_admin=False,
        )

        async_session.add(user)
        await async_session.flush()

        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.is_admin is False
        assert user.login_count == 0

    async def test_user_unique_username(self, async_session):
        """Test username uniqueness constraint"""
        user1 = User(username="duplicate", password_hash="hash1")
        user2 = User(username="duplicate", password_hash="hash2")

        async_session.add(user1)
        await async_session.flush()

        async_session.add(user2)
        with pytest.raises(IntegrityError):
            await async_session.flush()

    async def test_record_login(self, async_session):
        """Test recording user login"""
        user = User(username="logintest", password_hash="hash")
        async_session.add(user)
        await async_session.flush()

        assert user.login_count == 0
        assert user.last_login_at is None

        user.record_login()
        await async_session.flush()

        assert user.login_count == 1
        assert user.last_login_at is not None
        assert isinstance(user.last_login_at, datetime)

    async def test_user_preferences(self, async_session):
        """Test user preferences JSON field"""
        user = User(username="preftest", password_hash="hash")
        async_session.add(user)
        await async_session.flush()

        # Default preferences
        assert user.get_preferences() == {}

        # Set preferences
        prefs = {"theme": "dark", "notifications": True, "language": "en"}
        user.set_preferences(prefs)
        await async_session.flush()

        # Get preferences
        retrieved_prefs = user.get_preferences()
        assert retrieved_prefs == prefs

        # Update single preference
        user.update_preference("theme", "light")
        await async_session.flush()

        updated_prefs = user.get_preferences()
        assert updated_prefs["theme"] == "light"
        assert updated_prefs["notifications"] is True

    async def test_user_roles(self, async_session):
        """Test user roles JSON field"""
        user = User(username="roletest", password_hash="hash", is_admin=True)
        async_session.add(user)
        await async_session.flush()

        # Default admin user should have admin role
        assert user.has_role("admin")

        # Set custom roles
        user.set_roles(["admin", "moderator"])
        await async_session.flush()

        assert user.get_roles() == ["admin", "moderator"]
        assert user.has_role("admin")
        assert user.has_role("moderator")
        assert not user.has_role("user")

    async def test_user_to_dict(self, async_session):
        """Test user serialization to dictionary"""
        user = User(
            username="dicttest",
            password_hash="secret_hash",  # pragma: allowlist secret
            email="dict@test.com",
            display_name="Dict Test",
        )
        async_session.add(user)
        await async_session.flush()

        # Full dict without sensitive data
        user_dict = user.to_dict(include_sensitive=False)
        assert "password_hash" not in user_dict
        assert "mfa_secret" not in user_dict
        assert user_dict["username"] == "dicttest"
        assert user_dict["email"] == "dict@test.com"

        # Summary dict
        summary = user.to_summary_dict()
        assert summary["username"] == "dicttest"
        assert summary["display_name"] == "Dict Test"
        assert "password_hash" not in summary


# =============================================================================
# APIKey Model Tests
# =============================================================================


@pytest.mark.database
class TestAPIKeyModel:
    """Test APIKey model functionality"""

    async def test_create_api_key(self, async_session, sample_user):
        """Test creating an API key"""
        api_key = APIKey(
            name="test-key",
            key_hash="hashed_test_key_123",
            created_by_user_id=sample_user.id,
            description="Test API key",
        )

        async_session.add(api_key)
        await async_session.flush()

        assert api_key.id is not None
        assert api_key.name == "test-key"
        assert api_key.is_active is True
        assert api_key.usage_count == 0
        assert api_key.created_by_user_id == sample_user.id

    async def test_api_key_usage_tracking(self, async_session, sample_user):
        """Test API key usage recording"""
        api_key = APIKey(
            name="usage-test",
            key_hash="hashed_usage_key",
            created_by_user_id=sample_user.id,
        )

        async_session.add(api_key)
        await async_session.flush()

        assert api_key.usage_count == 0
        assert api_key.last_used_at is None
        assert api_key.last_used_ip is None

        # Record usage
        api_key.record_usage("192.168.1.100")
        await async_session.flush()

        assert api_key.usage_count == 1
        assert api_key.last_used_at is not None
        assert api_key.last_used_ip == "192.168.1.100"

    async def test_api_key_revocation(self, async_session, sample_user):
        """Test API key revocation"""
        api_key = APIKey(
            name="revoke-test",
            key_hash="hashed_revoke_key",
            created_by_user_id=sample_user.id,
        )

        async_session.add(api_key)
        await async_session.flush()

        assert api_key.is_active is True
        assert api_key.revoked_at is None
        assert api_key.is_valid() is True

        # Revoke key
        api_key.revoke()
        await async_session.flush()

        assert api_key.is_active is False
        assert api_key.revoked_at is not None
        assert api_key.is_revoked() is True
        assert api_key.is_valid() is False

    async def test_api_key_scopes(self, async_session, sample_user):
        """Test API key scopes"""
        api_key = APIKey(
            name="scope-test",
            key_hash="hashed_scope_key",
            created_by_user_id=sample_user.id,
        )

        async_session.add(api_key)
        await async_session.flush()

        # Default scope
        assert api_key.has_scope("admin")

        # Set custom scopes
        api_key.set_scopes(["read", "write"])
        await async_session.flush()

        assert api_key.get_scopes() == ["read", "write"]
        assert api_key.has_scope("read")
        assert api_key.has_scope("write")
        assert not api_key.has_scope("delete")


# =============================================================================
# SystemSettings Model Tests
# =============================================================================


@pytest.mark.database
class TestSystemSettingsModel:
    """Test SystemSettings singleton model"""

    async def test_create_system_settings(self, async_session):
        """Test creating system settings"""
        settings = SystemSettings(id=1)
        settings.deployment_profile = "homelab"

        async_session.add(settings)
        await async_session.flush()

        assert settings.id == 1
        assert settings.deployment_profile == "homelab"
        assert settings.default_check_interval_seconds == 86400
        assert settings.default_update_time == "03:00"

    async def test_singleton_constraint(self, async_session):
        """Test that only one system settings record can exist"""
        settings1 = SystemSettings(id=1)
        async_session.add(settings1)
        await async_session.flush()

        # Try to create another with id=1 should fail
        settings2 = SystemSettings(id=1)
        async_session.add(settings2)
        with pytest.raises(IntegrityError):
            await async_session.flush()

    async def test_apply_profile_defaults(self, async_session):
        """Test applying deployment profile defaults"""
        settings = SystemSettings(id=1)

        # Apply homelab defaults
        settings.apply_profile_defaults(DeploymentProfile.HOMELAB)
        assert settings.max_concurrent_updates == 2
        assert settings.session_timeout_hours == 168
        assert settings.require_https is False
        assert settings.show_getting_started is True

        # Apply production defaults
        settings.apply_profile_defaults(DeploymentProfile.PRODUCTION)
        assert settings.max_concurrent_updates == 10
        assert settings.session_timeout_hours == 8
        assert settings.require_https is True
        assert settings.show_getting_started is False

    async def test_maintenance_days(self, async_session):
        """Test maintenance days JSON field"""
        settings = SystemSettings(id=1)
        async_session.add(settings)
        await async_session.flush()

        # Default empty
        assert settings.get_maintenance_days() == []

        # Set maintenance days
        days = ["monday", "wednesday", "friday"]
        settings.set_maintenance_days(days)
        await async_session.flush()

        assert settings.get_maintenance_days() == days

        # Test invalid days are filtered
        settings.set_maintenance_days(["monday", "invalid", "sunday"])
        assert settings.get_maintenance_days() == ["monday", "sunday"]

    async def test_validation(self):
        """Test settings validation"""
        settings = SystemSettings(id=1)

        # Valid settings should not raise
        settings.default_check_interval_seconds = 60
        settings.max_concurrent_updates = 1
        settings.default_cleanup_keep_images = 0
        settings.validate()  # Should not raise

        # Invalid check interval
        settings.default_check_interval_seconds = 30
        with pytest.raises(ValueError, match="Check interval must be at least 60"):
            settings.validate()

        # Invalid concurrent updates
        settings.default_check_interval_seconds = 60
        settings.max_concurrent_updates = 0
        with pytest.raises(ValueError, match="Must allow at least 1 concurrent"):
            settings.validate()

        # Invalid cleanup keep images
        settings.max_concurrent_updates = 1
        settings.default_cleanup_keep_images = -1
        with pytest.raises(ValueError, match="must be non-negative"):
            settings.validate()


# =============================================================================
# Container Model Tests
# =============================================================================


@pytest.mark.database
class TestContainerModel:
    """Test Container model functionality"""

    async def test_create_container(self, async_session):
        """Test creating a container"""
        container = Container(
            uid="test-uid-123",
            docker_id="docker123",
            docker_name="test-nginx",
            image_repo="nginx",
            image_tag="latest",
            image_ref="nginx:latest",
            status="running",
        )

        async_session.add(container)
        await async_session.flush()

        assert container.id is not None
        assert container.uid == "test-uid-123"
        assert container.docker_name == "test-nginx"
        assert container.managed is True
        assert container.auto_discovered is True

    async def test_container_labels(self, async_session):
        """Test container labels JSON field"""
        container = Container(
            uid="label-test",
            docker_id="docker456",
            docker_name="labeled",
            image_repo="nginx",
            image_tag="latest",
            image_ref="nginx:latest",
            status="running",
        )

        async_session.add(container)
        await async_session.flush()

        # Set labels
        labels = {"com.docker.compose.service": "web", "harbor.enable": "true"}
        container.set_labels(labels)
        await async_session.flush()

        assert container.get_labels() == labels

        # Test exclusion check
        container.set_labels({"harbor.exclude": "true"})
        assert container.is_excluded_from_updates() is True

        container.set_labels({"harbor.enable": "true"})
        assert container.is_excluded_from_updates() is False

    async def test_container_ports(self, async_session):
        """Test container ports JSON field"""
        container = Container(
            uid="port-test",
            docker_id="docker789",
            docker_name="ported",
            image_repo="nginx",
            image_tag="latest",
            image_ref="nginx:latest",
            status="running",
        )

        ports = [
            {"container_port": 80, "host_port": 8080, "protocol": "tcp"},
            {"container_port": 443, "host_port": 8443, "protocol": "tcp"},
        ]

        container.set_ports(ports)
        async_session.add(container)
        await async_session.flush()

        assert container.get_ports() == ports


# =============================================================================
# ContainerPolicy Model Tests
# =============================================================================


@pytest.mark.database
class TestContainerPolicyModel:
    """Test ContainerPolicy model functionality"""

    async def test_create_policy(self, async_session, sample_container):
        """Test creating a container policy"""
        policy = ContainerPolicy(
            container_uid=sample_container.uid,
            desired_version="latest",
            auto_update_enabled=True,
            health_check_enabled=True,
        )

        async_session.add(policy)
        await async_session.flush()

        assert policy.id is not None
        assert policy.container_uid == sample_container.uid
        assert policy.is_eligible_for_update() is True

    async def test_policy_eligibility(self, async_session, sample_container):
        """Test policy update eligibility checks"""
        policy = ContainerPolicy(container_uid=sample_container.uid)

        # Default should be eligible
        assert policy.is_eligible_for_update() is True

        # Exclude from updates
        policy.exclude_from_updates = True
        assert policy.is_eligible_for_update() is False

        # Dry run only
        policy.exclude_from_updates = False
        policy.dry_run_only = True
        assert policy.is_eligible_for_update() is False

        # Auto update disabled
        policy.dry_run_only = False
        policy.auto_update_enabled = False
        assert policy.is_eligible_for_update() is False

    async def test_update_days(self, async_session, sample_container):
        """Test update days configuration"""
        policy = ContainerPolicy(container_uid=sample_container.uid)

        # Set update days
        days = ["monday", "wednesday", "friday"]
        policy.set_update_days(days)

        assert policy.get_update_days() == days
        assert policy.should_update_on_day("monday") is True
        assert policy.should_update_on_day("tuesday") is False
        assert policy.should_update_on_day("friday") is True

        # No restrictions
        policy.set_update_days([])
        assert policy.should_update_on_day("sunday") is True
