#!/usr/bin/env python3
"""
Simple test to debug Pydantic v2 environment variable handling
"""

import os
from enum import Enum

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TestProfile(str, Enum):
    HOMELAB = "homelab"
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class SimpleSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HARBOR_",
        env_file=".env",
        case_sensitive=False,
    )

    # Test basic field
    debug: bool = Field(default=False, description="Debug mode")

    # Test enum field
    deployment_profile: TestProfile = Field(
        default=TestProfile.HOMELAB, description="Deployment profile"
    )

    # Test nested field
    password_min_length: int = Field(default=6, description="Password min length")


def test_simple_env_vars() -> None:
    """Test basic environment variable handling"""

    print("🧪 Simple Environment Variable Test")
    print("=" * 40)

    # Test 1: No environment variables
    print("\n1. Testing defaults (no env vars):")
    settings1 = SimpleSettings()
    print(f"   debug: {settings1.debug}")
    print(f"   deployment_profile: {settings1.deployment_profile.value}")
    print(f"   password_min_length: {settings1.password_min_length}")

    # Test 2: Set environment variables
    print("\n2. Setting environment variables:")
    os.environ["HARBOR_DEBUG"] = "true"
    os.environ["HARBOR_DEPLOYMENT_PROFILE"] = "production"
    os.environ["HARBOR_PASSWORD_MIN_LENGTH"] = "12"

    print("   HARBOR_DEBUG = true")
    print("   HARBOR_DEPLOYMENT_PROFILE = production")
    print("   HARBOR_PASSWORD_MIN_LENGTH = 12")

    settings2 = SimpleSettings()
    print(f"   debug: {settings2.debug}")
    print(f"   deployment_profile: {settings2.deployment_profile.value}")
    print(f"   password_min_length: {settings2.password_min_length}")

    # Test 3: Test HARBOR_MODE specifically
    print("\n3. Testing HARBOR_MODE:")
    if "HARBOR_DEPLOYMENT_PROFILE" in os.environ:
        del os.environ["HARBOR_DEPLOYMENT_PROFILE"]
    os.environ["HARBOR_MODE"] = "development"

    print("   HARBOR_MODE = development")
    print("   HARBOR_DEPLOYMENT_PROFILE = (removed)")

    settings3 = SimpleSettings()
    print(f"   deployment_profile: {settings3.deployment_profile.value}")

    # Clean up
    for var in ["HARBOR_DEBUG", "HARBOR_MODE", "HARBOR_PASSWORD_MIN_LENGTH"]:
        if var in os.environ:
            del os.environ[var]

    print("\n🧹 Environment cleaned up")


class SettingsWithMODE(BaseSettings):
    """Settings with custom HARBOR_MODE handling"""

    model_config = SettingsConfigDict(
        env_prefix="HARBOR_",
        case_sensitive=False,
    )

    debug: bool = False
    mode: TestProfile = Field(default=TestProfile.HOMELAB, alias="HARBOR_MODE")


def test_mode_alias() -> None:
    """Test using alias for HARBOR_MODE"""

    print("\n🧪 Testing HARBOR_MODE with alias")
    print("=" * 35)

    # Test with HARBOR_MODE
    os.environ["HARBOR_MODE"] = "production"
    print("   HARBOR_MODE = production")

    try:
        settings = SettingsWithMODE()
        print(f"   mode: {settings.mode.value}")
    except Exception as e:
        print(f"   Error: {e}")

    # Clean up
    if "HARBOR_MODE" in os.environ:
        del os.environ["HARBOR_MODE"]


if __name__ == "__main__":
    test_simple_env_vars()
    test_mode_alias()
