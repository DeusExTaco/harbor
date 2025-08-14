"""
Harbor Test Configuration
Shared pytest fixtures and configuration for all test suites
"""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def test_data_dir():
    """Create temporary directory for test data"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(scope="session")
def test_database_url(test_data_dir):
    """Provide test database URL"""
    return f"sqlite:///{test_data_dir}/test.db"


@pytest.fixture
def harbor_config():
    """Basic Harbor configuration for testing"""
    return {
        "HARBOR_MODE": "development",
        "LOG_LEVEL": "DEBUG",
        "ENABLE_AUTO_DISCOVERY": False,  # Disable for tests
    }


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
