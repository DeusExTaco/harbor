# tests/conftest.py
"""
Harbor Test Configuration - Enhanced Database Integration

Shared pytest fixtures and configuration for all test suites with
comprehensive database testing support and proper isolation.
"""

import asyncio
import os
import tempfile
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

# Import all models to ensure they're registered
from app.db.base import Base
from app.db.models.api_key import APIKey
from app.db.models.container import Container
from app.db.models.policy import ContainerPolicy
from app.db.models.settings import SystemSettings
from app.db.models.user import User


# ============================================================================
# Session and Event Loop Configuration
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# File System Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def test_data_dir():
    """Create temporary directory for test data"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_data_dir():
    """Create temporary data directory for individual tests"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set environment variable for Harbor to use temp directory
        original_data_dir = os.environ.get("HARBOR_DATA_DIR")
        os.environ["HARBOR_DATA_DIR"] = temp_dir

        yield Path(temp_dir)

        # Restore original environment
        if original_data_dir:
            os.environ["HARBOR_DATA_DIR"] = original_data_dir
        else:
            os.environ.pop("HARBOR_DATA_DIR", None)


# ============================================================================
# Database Fixtures
# ============================================================================


@pytest.fixture(scope="function")  # Change to function scope
def test_database_url():
    """Provide test database URL - use new in-memory DB for each test"""
    return "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="function")  # Change to function scope
async def test_engine(test_database_url: str) -> AsyncGenerator[AsyncEngine]:
    """Create test database engine per test for isolation"""
    engine = create_async_engine(
        test_database_url,
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
            "isolation_level": None,
        },
        echo=False,  # Set to True for SQL debugging
    )

    # Create all tables for this test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest.fixture(scope="function")  # Change to function scope
def test_session_factory(test_engine: AsyncEngine) -> async_sessionmaker:
    """Create test session factory per test"""
    return async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=True,
        autocommit=False,
    )


@pytest.fixture
async def async_session(
    test_session_factory: async_sessionmaker,
) -> AsyncGenerator[AsyncSession]:
    """Create isolated test session with automatic rollback"""
    async with test_session_factory() as session:
        async with session.begin():
            yield session
            # Transaction rolls back here automatically


@pytest.fixture
async def committed_session(
    test_session_factory: async_sessionmaker,
) -> AsyncGenerator[AsyncSession]:
    """Create test session that commits changes (for integration tests)"""
    async with test_session_factory() as session:
        # Don't use a transaction context that auto-rolls back
        yield session
        await session.close()


@pytest.fixture
async def test_user(committed_session: AsyncSession) -> User:
    """Create a test user fixture for integration tests"""
    from app.auth.password import hash_password
    from app.db.models.user import User

    user = User(
        username="testuser",
        password_hash=hash_password("TestPassword123!"),
        email="test@example.com",
        is_active=True,
        is_admin=False,
    )

    committed_session.add(user)
    await committed_session.flush()  # Use flush instead of commit
    # Don't refresh here - the session is still active

    return user


# ============================================================================
# Model Fixtures
# ============================================================================


@pytest.fixture
async def sample_user(async_session: AsyncSession) -> User:
    """Create a sample user for testing"""
    user = User(
        username="testuser",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$test_hash",
        email="test@example.com",
        display_name="Test User",
        is_admin=True,
    )

    async_session.add(user)
    await async_session.flush()
    await async_session.refresh(user)

    return user


@pytest.fixture
async def sample_container(async_session: AsyncSession) -> Container:
    """Create a sample container for testing"""
    container_uid = str(uuid.uuid4())

    container = Container(
        uid=container_uid,
        docker_id="test_docker_id_123",
        docker_name="test-nginx",
        image_repo="nginx",
        image_tag="1.21-alpine",
        image_ref="nginx:1.21-alpine",
        status="running",
        current_digest="sha256:test_digest_123",
        managed=True,
        auto_discovered=True,
    )

    async_session.add(container)
    await async_session.flush()
    await async_session.refresh(container)

    return container


@pytest.fixture
async def sample_system_settings(async_session: AsyncSession) -> SystemSettings:
    """Create sample system settings for testing"""
    settings = SystemSettings(id=1)
    settings.deployment_profile = "homelab"
    settings.default_check_interval_seconds = 86400
    settings.max_concurrent_updates = 2

    async_session.add(settings)
    await async_session.flush()
    await async_session.refresh(settings)

    return settings


@pytest.fixture
async def sample_api_key(async_session: AsyncSession, sample_user: User) -> APIKey:
    """Create a sample API key for testing"""
    api_key = APIKey(
        name="test-key",
        key_hash="hashed_api_key_123",
        created_by_user_id=sample_user.id,
        description="Test API key for testing",
    )

    async_session.add(api_key)
    await async_session.flush()
    await async_session.refresh(api_key)

    return api_key


@pytest.fixture
async def sample_container_policy(
    async_session: AsyncSession, sample_container: Container
) -> ContainerPolicy:
    """Create a sample container policy for testing"""
    policy = ContainerPolicy(
        container_uid=sample_container.uid,
        desired_version="latest",
        update_strategy="rolling",
        auto_update_enabled=True,
        health_check_enabled=True,
        rollback_enabled=True,
    )

    async_session.add(policy)
    await async_session.flush()
    await async_session.refresh(policy)

    return policy


# ============================================================================
# Configuration Fixtures
# ============================================================================


@pytest.fixture
def harbor_config():
    """Basic Harbor configuration for testing"""
    return {
        "HARBOR_MODE": "development",
        "LOG_LEVEL": "DEBUG",
        "ENABLE_AUTO_DISCOVERY": False,  # Disable for tests
    }


@pytest.fixture
def mock_homelab_config(monkeypatch):
    """Mock home lab configuration for testing"""
    monkeypatch.setenv("HARBOR_MODE", "homelab")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("ENABLE_AUTO_DISCOVERY", "true")
    monkeypatch.setenv("TESTING", "true")

    # Clear cached settings to force reload - FIXED
    from app.config import clear_settings_cache

    clear_settings_cache()

    yield

    # Clear settings again after test
    clear_settings_cache()


@pytest.fixture
def mock_production_config(monkeypatch):
    """Mock production configuration for testing"""
    monkeypatch.setenv("HARBOR_MODE", "production")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("REQUIRE_HTTPS", "true")
    monkeypatch.setenv("MAX_CONCURRENT_UPDATES", "10")
    monkeypatch.setenv("TESTING", "true")

    # Clear cached settings to force reload - FIXED
    from app.config import clear_settings_cache

    clear_settings_cache()

    yield

    # Clear settings again after test
    clear_settings_cache()


# ============================================================================
# Mock External Dependencies
# ============================================================================


@pytest.fixture
def mock_docker_client():
    """Mock Docker client for testing"""
    from unittest.mock import AsyncMock, MagicMock

    mock_client = AsyncMock()
    mock_client.containers = MagicMock()
    mock_client.images = MagicMock()
    mock_client.version = AsyncMock(return_value={"Version": "24.0.7"})

    return mock_client


@pytest.fixture
def mock_registry_client():
    """Mock registry client for testing"""
    from unittest.mock import AsyncMock

    mock_client = AsyncMock()
    mock_client.get_manifest = AsyncMock(
        return_value={
            "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
            "digest": "sha256:test_digest_456",
        }
    )

    return mock_client


# ============================================================================
# Pytest Configuration
# ============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "database: Tests requiring database")


def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="run integration tests",
    )
    parser.addoption(
        "--database", action="store_true", default=False, help="run database tests"
    )
    parser.addoption(
        "--slow", action="store_true", default=False, help="run slow tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle integration tests"""
    if not config.getoption("--integration"):
        skip_integration = pytest.mark.skip(reason="need --integration option to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)

    if not config.getoption("--database"):
        skip_database = pytest.mark.skip(reason="need --database option to run")
        for item in items:
            if "database" in item.keywords:
                item.add_marker(skip_database)

    if not config.getoption("--slow"):
        skip_slow = pytest.mark.skip(reason="need --slow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)


# ============================================================================
# Auto-Setup Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Automatically set up test environment for all tests"""
    # Set test-specific environment variables
    monkeypatch.setenv("HARBOR_MODE", "development")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("ENABLE_AUTO_DISCOVERY", "false")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    # Clear any cached settings before each test - FIXED
    from app.config import clear_settings_cache

    clear_settings_cache()

    yield

    # Clean up after test
    clear_settings_cache()


# ============================================================================
# Test Data Generators
# ============================================================================


def generate_test_users(count: int = 5):
    """Generate test user data"""
    return [
        {
            "username": f"user{i:02d}",
            "password_hash": f"$argon2id$test_hash_{i}",
            "email": f"user{i}@example.com",
            "display_name": f"User {i}",
            "is_admin": i == 0,  # First user is admin
        }
        for i in range(count)
    ]


def generate_test_containers(count: int = 5):
    """Generate test container data"""
    return [
        {
            "uid": str(uuid.uuid4()),
            "docker_id": f"container_id_{i}",
            "docker_name": f"test-container-{i}",
            "image_repo": "nginx" if i % 2 == 0 else "redis",
            "image_tag": f"tag-{i}",
            "image_ref": f"nginx:tag-{i}" if i % 2 == 0 else f"redis:tag-{i}",
            "status": "running" if i % 3 != 2 else "stopped",
            "current_digest": f"sha256:digest_{i}",
            "managed": True,
            "auto_discovered": True,
        }
        for i in range(count)
    ]


def generate_test_api_keys(user_id: int, count: int = 3):
    """Generate test API key data"""
    return [
        {
            "name": f"api-key-{i}",
            "key_hash": f"hashed_key_{i}",
            "created_by_user_id": user_id,
            "description": f"Test API key {i}",
            "is_active": i != 2,  # Make one inactive for testing
        }
        for i in range(count)
    ]


# ============================================================================
# Helper Functions for Tests
# ============================================================================


async def create_test_data(
    session: AsyncSession, users_count: int = 3, containers_count: int = 5
):
    """Create comprehensive test data"""
    # Create users
    users = []
    for user_data in generate_test_users(users_count):
        user = User(**user_data)
        session.add(user)
        users.append(user)

    await session.flush()

    # Create containers
    containers = []
    for container_data in generate_test_containers(containers_count):
        container = Container(**container_data)
        session.add(container)
        containers.append(container)

    await session.flush()

    # Create system settings
    settings = SystemSettings(id=1)
    settings.deployment_profile = "development"
    session.add(settings)

    # Create API keys for first user
    if users:
        for key_data in generate_test_api_keys(users[0].id, 2):
            api_key = APIKey(**key_data)
            session.add(api_key)

    await session.commit()

    return {"users": users, "containers": containers, "settings": settings}


# ============================================================================
# Repository Fixtures
# ============================================================================


@pytest.fixture
async def user_repository(async_session: AsyncSession):
    """Create UserRepository instance for testing"""
    from app.db.repositories.user import UserRepository

    return UserRepository(async_session)


@pytest.fixture
async def container_repository(async_session: AsyncSession):
    """Create ContainerRepository instance for testing"""
    from app.db.repositories.container import ContainerRepository

    return ContainerRepository(async_session)


# ============================================================================
# FastAPI Test Client Fixtures
# ============================================================================


@pytest.fixture
def test_client():
    """Create FastAPI test client"""
    from fastapi.testclient import TestClient

    from app.main import create_app

    app = create_app()
    return TestClient(app)


@pytest.fixture
async def async_test_client():
    """Create async FastAPI test client"""
    from httpx import AsyncClient

    from app.main import create_app

    app = create_app()

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# ============================================================================
# Performance Test Fixtures
# ============================================================================


@pytest.fixture
def performance_monitor():
    """Monitor test performance and resource usage"""
    import time

    import psutil

    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.start_memory = None

        def start(self):
            self.start_time = time.time()
            self.start_memory = psutil.Process().memory_info().rss

        def stop(self):
            if self.start_time is None:
                return None

            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss

            return {
                "duration_ms": (end_time - self.start_time) * 1000,
                "memory_delta_mb": (end_memory - self.start_memory) / 1024 / 1024,
                "peak_memory_mb": end_memory / 1024 / 1024,
            }

    return PerformanceMonitor()


# ============================================================================
# Security Test Fixtures
# ============================================================================


@pytest.fixture
def security_test_data():
    """Generate security test data"""
    return {
        "xss_payloads": [
            "<script>alert('xss')</script>",
            "javascript:alert(1)",
            "<img src=x onerror=alert(1)>",
            "';alert(String.fromCharCode(88,83,83))//'",
        ],
        "sql_injection_payloads": [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "1; SELECT * FROM users",
            "admin'--",
        ],
        "path_traversal_payloads": [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "....//....//etc/passwd",
        ],
    }
