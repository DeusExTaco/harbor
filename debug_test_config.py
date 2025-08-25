#!/usr/bin/env python3
"""
Debug test for Harbor configuration system to check profile switching
"""

import os
import sys
from pathlib import Path


# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent))


def debug_profile_switching() -> None:
    """Debug profile switching functionality"""

    print("🔍 Debug: Profile Switching Test")
    print("=" * 40)

    from app.config import reload_settings

    # Test each profile
    for profile_name in ["homelab", "development", "production"]:
        print(f"\n🧪 Testing {profile_name} profile:")

        # Set environment variable
        os.environ["HARBOR_MODE"] = profile_name
        print(f"   Set HARBOR_MODE = {os.getenv('HARBOR_MODE')}")

        # Create fresh settings
        settings = reload_settings()

        # Check what we got
        print(f"   Detected profile: {settings.deployment_profile.value}")
        print(f"   Debug mode: {settings.debug}")
        print(f"   HTTPS required: {settings.security.require_https}")
        print(f"   Session timeout: {settings.security.session_timeout_hours} hours")
        print(f"   Max concurrent updates: {settings.updates.max_concurrent_updates}")
        print(f"   Log level: {settings.logging.log_level.value}")
        print(f"   Log format: {settings.logging.log_format.value}")

        # Check if profile-specific defaults were applied
        if profile_name == "homelab":
            expected_https = False
            expected_timeout = 168
            expected_updates = 2
        elif profile_name == "production":
            expected_https = True
            expected_timeout = 8
            expected_updates = 10
        else:  # development
            expected_https = False
            expected_timeout = 72  # 3 days for dev
            expected_updates = 3

        # Validate expectations
        checks = [
            ("HTTPS required", settings.security.require_https, expected_https),
            (
                "Session timeout",
                settings.security.session_timeout_hours,
                expected_timeout,
            ),
            (
                "Max concurrent updates",
                settings.updates.max_concurrent_updates,
                expected_updates,
            ),
        ]

        for check_name, actual, expected in checks:
            if actual == expected:
                print(f"   ✅ {check_name}: {actual} (correct)")
            else:
                print(f"   ❌ {check_name}: got {actual}, expected {expected}")

    # Clean up
    if "HARBOR_MODE" in os.environ:
        del os.environ["HARBOR_MODE"]

    print("\n🧹 Cleaned up environment")


def debug_pydantic_behavior() -> None:
    """Debug Pydantic model behavior"""

    print("\n🔍 Debug: Pydantic Model Behavior")
    print("=" * 35)

    from app.config import AppSettings, DeploymentProfile

    # Test direct instantiation with different profiles
    for profile in [DeploymentProfile.HOMELAB, DeploymentProfile.PRODUCTION]:
        print(f"\n🧪 Testing direct instantiation with {profile.value}:")

        try:
            settings = AppSettings(deployment_profile=profile)
            print(f"   Profile: {settings.deployment_profile.value}")
            print(f"   Debug: {settings.debug}")
            print(f"   HTTPS: {settings.security.require_https}")
            print(f"   Session timeout: {settings.security.session_timeout_hours}")
            print(f"   Max updates: {settings.updates.max_concurrent_updates}")
            print("   ✅ Direct instantiation works")

        except Exception as e:
            print(f"   ❌ Error: {e}")


def debug_environment_detection() -> None:
    """Debug environment variable detection"""

    print("\n🔍 Debug: Environment Variable Detection")
    print("=" * 42)

    # Test environment variable override
    test_vars = {
        "HARBOR_MODE": "production",
        "HARBOR_SECURITY_REQUIRE_HTTPS": "true",
        "HARBOR_UPDATE_MAX_CONCURRENT_UPDATES": "5",
    }

    print("Setting test environment variables:")
    for var, value in test_vars.items():
        os.environ[var] = value
        print(f"   {var} = {value}")

    from app.config import reload_settings

    settings = reload_settings()

    print("\nResults:")
    print(f"   Profile: {settings.deployment_profile.value}")
    print(f"   HTTPS: {settings.security.require_https}")
    print(f"   Max updates: {settings.updates.max_concurrent_updates}")

    # Check if environment variables took effect
    if settings.deployment_profile.value == "production":
        print("   ✅ HARBOR_MODE working")
    else:
        print("   ❌ HARBOR_MODE not working")

    if settings.security.require_https:
        print("   ✅ HARBOR_SECURITY_REQUIRE_HTTPS working")
    else:
        print("   ❌ HARBOR_SECURITY_REQUIRE_HTTPS not working")

    if settings.updates.max_concurrent_updates == 5:
        print("   ✅ HARBOR_UPDATE_MAX_CONCURRENT_UPDATES working")
    else:
        print("   ❌ HARBOR_UPDATE_MAX_CONCURRENT_UPDATES not working")

    # Clean up
    for var in test_vars:
        if var in os.environ:
            del os.environ[var]

    print("\n🧹 Cleaned up test environment variables")


if __name__ == "__main__":
    debug_profile_switching()
    debug_pydantic_behavior()
    debug_environment_detection()
