# tests/integration/test_database.py
"""
Harbor Database Integration Tests

Integration tests for database initialization, session management,
and repository operations.
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.init import initialize_database, get_database_info, reset_database
from app.db.repositories.user import UserRepository
from app.db.repositories.container import ContainerRepository
from app.db.models.user import User
from app.db.models.settings import SystemSettings
from app.db.config import get_database_config, get_engine
from app.db.session import get_async_session, get_session_manager


class TestDatabaseInitialization:
    """Test database initialization and setup"""

    async def test_database_initialization(self):
        """Test complete database initialization"""
        # Initialize database
        success = await initialize_database(force_recreate=True)
        assert success is True

        # Check database info
        info = await get_database_info()
        assert "table_count" in info
        assert info["table_count"] > 0  # Should have created tables

        # Verify tables exist by checking system settings
        async with get_async_session() as session:
            settings = await session.get(SystemSettings, 1)
            assert settings is not None
            assert settings.deployment_profile == "homelab"  # Default profile

    async def test_profile_specific_initialization(self, monkeypatch):
        """Test initialization with different deployment profiles"""
        # Test with production profile
        monkeypatch.setenv("HARBOR_MODE", "production")

        # Force reload of settings
        from app.config import _settings

        _settings.clear()

        success = await initialize_database(force_recreate=True)
        assert success is True

        async with get_async_session() as session:
            settings = await session.get(SystemSettings, 1)
            assert settings.deployment_profile == "production"
            # Production should have stricter defaults
            assert settings.max_concurrent_updates >= 5  # Higher than homelab
            assert settings.require_https is True

    async def test_database_health_check(self):
        """Test database health checking"""
        from app.db.init import check_database_health

        engine = await get_engine()
        healthy = await check_database_health(engine)
        assert healthy is True


class TestSessionManagement:
    """Test database session management"""

    async def test_session_context_manager(self):
        """Test async session context manager"""
        async with get_async_session() as session:
            assert isinstance(session, AsyncSession)

            # Test basic query
            from sqlalchemy import text

            result = await session.execute(text("SELECT 1 as test"))
            assert result.scalar() == 1

    async def test_session_manager_lifecycle(self):
        """Test session manager initialization and cleanup"""
        session_manager = get_session_manager()

        # Initialize
        await session_manager.initialize()

        # Test session creation
        async with session_manager.session() as session:
            assert isinstance(session, AsyncSession)

        # Cleanup
        await session_manager.close()

    async def test_session_error_handling(self):
        """Test session error handling and rollback"""
        async with get_async_session() as session:
            try:
                # Force an error
                await session.execute(text("SELECT FROM invalid_table"))
                assert False, "Should have raised an exception"
            except Exception:
                # Session should handle rollback automatically
                pass

            # Session should still be usable for valid queries
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1


class TestRepositoryOperations:
    """Test repository pattern operations"""

    async def test_user_repository_crud(self):
        """Test User repository CRUD operations"""
        async with get_async_session() as session:
            user_repo = UserRepository(session)

            # Create user
            user = await user_repo.create_user(
                username="testuser",
                password_hash="hashed_password",  # pragma: allowlist secret
                email="test@example.com",
                display_name="Test User",
            )

            assert user.id is not None
            assert user.username == "testuser"

            # Read user
            found_user = await user_repo.get_by_username("testuser")
            assert found_user is not None
            assert found_user.id == user.id

            # Update user
            updated_user = await user_repo.update_profile(
                user.id, display_name="Updated Test User"
            )
            assert updated_user.display_name == "Updated Test User"

            # Test username uniqueness
            with pytest.raises(ValueError, match="Username .* already exists"):
                await user_repo.create_user(
                    username="testuser",  # Duplicate username
                    password_hash="another_hash",  # pragma: allowlist secret
                )

            await session.commit()

    async def test_container_repository_operations(self):
        """Test Container repository operations"""
        async with get_async_session() as session:
            container_repo = ContainerRepository(session)

            # Create container
            import uuid

            container_uid = str(uuid.uuid4())

            container = await container_repo.create_or_update_container(
                uid=container_uid,
                docker_id="abc123",
                docker_name="test-nginx",
                image_repo="nginx",
                image_tag="latest",
                image_ref="nginx:latest",
                status="running",
                current_digest="sha256:abc123...",
            )

            assert container.uid == container_uid
            assert container.docker_name == "test-nginx"

            # Test update existing container
            updated_container = await container_repo.create_or_update_container(
                uid=container_uid,
                docker_id="def456",  # New docker ID
                docker_name="test-nginx",
                image_repo="nginx",
                image_tag="latest",
                image_ref="nginx:latest",
                status="running",
                current_digest="sha256:def456...",  # New digest
            )

            assert updated_container.id == container.id  # Same container
            assert updated_container.docker_id == "def456"  # Updated field
            assert updated_container.current_digest == "sha256:def456..."

            # Test search functionality
            results = await container_repo.search_containers(
                query="nginx", managed_only=True
            )

            assert len(results.items) == 1
            assert results.items[0].docker_name == "test-nginx"

            await session.commit()

    async def test_repository_pagination(self):
        """Test repository pagination functionality"""
        async with get_async_session() as session:
            user_repo = UserRepository(session)

            # Create multiple users
            users = []
            for i in range(25):  # More than one page
                user = await user_repo.create_user(
                    username=f"user{i:02d}",
                    password_hash="hash",  # pragma: allowlist secret
                )
                users.append(user)

            await session.commit()

            # Test pagination
            page1 = await user_repo.paginate(page=1, per_page=10)
            assert len(page1.items) == 10
            assert page1.total == 25
            assert page1.pages == 3
            assert page1.has_next is True
            assert page1.has_prev is False

            page2 = await user_repo.paginate(page=2, per_page=10)
            assert len(page2.items) == 10
            assert page2.has_next is True
            assert page2.has_prev is True

            page3 = await user_repo.paginate(page=3, per_page=10)
            assert len(page3.items) == 5  # Remaining items
            assert page3.has_next is False
            assert page3.has_prev is True


class TestDatabaseConfiguration:
    """Test database configuration for different profiles"""

    async def test_homelab_configuration(self, monkeypatch):
        """Test home lab database configuration"""
        monkeypatch.setenv("HARBOR_MODE", "homelab")

        # Force reload of settings
        from app.config import _settings

        _settings.clear()

        config = get_database_config()
        url = config.get_database_url()

        assert url.startswith("sqlite+aiosqlite://")
        assert "data/harbor.db" in url

        connection_config = config.get_connection_config()
        assert connection_config["pool_size"] == 3  # Conservative for home lab

    async def test_production_configuration(self, monkeypatch):
        """Test production database configuration"""
        monkeypatch.setenv("HARBOR_MODE", "production")
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql+asyncpg://user:pass@localhost/harbor",  # pragma: allowlist secret
        )

        # Force reload of settings
        from app.config import _settings

        _settings.clear()

        config = get_database_config()
        url = config.get_database_url()

        assert url.startswith("postgresql+asyncpg://")

        connection_config = config.get_connection_config()
        assert connection_config["pool_size"] == 20  # Higher for production


class TestDatabaseBackupAndRecovery:
    """Test database backup and recovery functionality"""

    async def test_sqlite_backup_directory_creation(self, monkeypatch):
        """Test backup directory creation for SQLite"""
        with tempfile.TemporaryDirectory() as temp_dir:
            monkeypatch.setenv("HARBOR_DATA_DIR", temp_dir)

            from app.db.init import create_backup_directory

            await create_backup_directory()

            backup_dir = Path(temp_dir) / "backups"
            assert backup_dir.exists()
            assert backup_dir.is_dir()

    async def test_database_reset_functionality(self):
        """Test database reset (dangerous operation)"""
        # Create some test data
        async with get_async_session() as session:
            user = User(username="reset_test", password_hash="hash")
            session.add(user)
            await session.commit()

            user_id = user.id

        # Verify data exists
        async with get_async_session() as session:
            found_user = await session.get(User, user_id)
            assert found_user is not None

        # Reset database
        success = await reset_database()
        assert success is True

        # Verify data is gone but tables still exist
        async with get_async_session() as session:
            found_user = await session.get(User, user_id)
            assert found_user is None

            # But system settings should be recreated
            settings = await session.get(SystemSettings, 1)
            assert settings is not None


@pytest.mark.integration
class TestDatabaseConcurrency:
    """Test database concurrency and connection handling"""

    async def test_concurrent_sessions(self):
        """Test concurrent database sessions"""

        async def create_user(username: str):
            async with get_async_session() as session:
                user_repo = UserRepository(session)
                user = await user_repo.create_user(
                    username=username,
                    password_hash="concurrent_hash",  # pragma: allowlist secret
                )
                await session.commit()
                return user

        # Create users concurrently
        tasks = [create_user(f"concurrent_user_{i}") for i in range(5)]
        users = await asyncio.gather(*tasks)

        assert len(users) == 5
        assert all(user.id is not None for user in users)

        # Verify all users were created
        async with get_async_session() as session:
            user_repo = UserRepository(session)
            for user in users:
                found_user = await user_repo.get_by_id(user.id)
                assert found_user is not None

    async def test_transaction_isolation(self):
        """Test transaction isolation"""
        async with get_async_session() as session1:
            async with get_async_session() as session2:
                user_repo1 = UserRepository(session1)
                user_repo2 = UserRepository(session2)

                # Create user in session1 but don't commit
                user1 = await user_repo1.create_user(
                    username="isolation_test",
                    password_hash="hash",  # pragma: allowlist secret
                )

                # Session2 should not see uncommitted user
                user2 = await user_repo2.get_by_username("isolation_test")
                assert user2 is None

                # Commit in session1
                await session1.commit()

                # Session2 should now see the user
                user2 = await user_repo2.get_by_username("isolation_test")
                assert user2 is not None
                assert user2.id == user1.id
