"""
Test configuration management
Basic unit test to verify testing infrastructure works
"""

import os

import pytest


@pytest.mark.unit
def test_environment_configuration():
    """Test basic environment configuration"""
    # This is a basic test to verify pytest is working
    assert os.getenv("HARBOR_MODE", "homelab") in [
        "homelab",
        "development",
        "production",
    ]


@pytest.mark.unit
def test_python_version():
    """Test Python version compatibility"""
    import sys

    version = sys.version_info
    # Harbor requires Python 3.11+
    assert version.major == 3
    assert version.minor >= 11


@pytest.mark.unit
def test_basic_imports():
    """Test that basic Python libraries can be imported"""
    # Test core dependencies that should always be available
    import json
    import logging
    import pathlib

    # Basic validation
    assert json.dumps({"test": True}) == '{"test": true}'
    assert logging.getLogger("test")
    assert pathlib.Path()
