#!/usr/bin/env python3
"""
Debug script to test the fixed Pydantic environment variable loading

This script tests the updated configuration system to ensure environment
variables are properly detected and applied.
"""

import os
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))


def print_test_header(title: str):
    """Print formatted test header"""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}")


def print_test_result(test_name: str, expected: str, actual: str) -> bool:
    """Print test result with pass/fail status"""
    success = expected == actual
    status = "✅" if success else "❌"
    print(f"   {status} {test_name}: Expected={expected}, Actual={actual}")
    return success


def test_environment_variable_handling():
    """Test the fixed environment variable handling"""

    print_test_header("Testing Fixed Environment Variable Handling")

    # Clean slate - clear any existing environment vars
    env_vars_to_clear = [
        "HARBOR_MODE",
        "HARBOR_SECURITY_PASSWORD_MIN_LENGTH",
        "HARBOR_UPDATE_MAX_CONCURRENT_UPDATES",
        "HARBOR_LOG_LOG_LEVEL",
        "HARBOR_DEBUG",
    ]

    original_values = {}
    for var in env_vars_to_clear:
        original_values[var] = os.getenv(var)
        if var in os.environ:
            del os.environ[var]

    try:
        # Test 1: Basic environment variable detection
        print("\n1. Testing basic environment variable visibility...")

        os.environ["HARBOR_MODE"] = "development"
        os.environ["HARBOR_DEBUG"] = "true"

        # Check visibility
        print(f"   HARBOR_MODE = {os.getenv('HARBOR_MODE')}")
        print(f"   HARBOR_DEBUG = {os.getenv('HARBOR_DEBUG')}")

        # Test 2: Fresh settings creation
        print("\n2. Testing fresh settings creation...")

        from app.config import create_fresh_settings, clear_settings_cache

        # Clear any existing cache
        clear_settings_cache()

        # Create fresh settings
        settings = create_fresh_settings()

        success1 = print_test_result(
            "Deployment Profile", "development", settings.deployment_profile.value
        )

        success2 = print_test_result("Debug Mode", "True", str(settings.debug))

        # Test 3: Profile switching with complete reload
        print("\n3. Testing profile switching...")

        test_profiles = ["homelab", "development", "production"]
        profile_results = []

        for profile in test_profiles:
            # Set environment
            os.environ["HARBOR_MODE"] = profile

            # Force complete reload
            clear_settings_cache()
            settings = create_fresh_settings()

            actual_profile = settings.deployment_profile.value
            success = print_test_result(f"Profile {profile}", profile, actual_profile)
            profile_results.append(success)

            # Test profile-specific defaults
            if profile == "development":
                debug_expected = True
                debug_actual = settings.debug
                success_debug = print_test_result(
                    f"  Debug mode for {profile}",
                    str(debug_expected),
                    str(debug_actual),
                )
                profile_results.append(success_debug)

            elif profile == "production":
                https_expected = True
                https_actual = settings.security.require_https
                success_https = print_test_result(
                    f"  HTTPS required for {profile}",
                    str(https_expected),
                    str(https_actual),
                )
                profile_results.append(success_https)

        # Test 4: Environment variable overrides
        print("\n4. Testing specific environment variable overrides...")

        # Set specific overrides
        os.environ["HARBOR_MODE"] = "homelab"  # Base profile
        os.environ["HARBOR_SECURITY_PASSWORD_MIN_LENGTH"] = "10"
        os.environ["HARBOR_UPDATE_MAX_CONCURRENT_UPDATES"] = "5"
        os.environ["HARBOR_LOG_LOG_LEVEL"] = "DEBUG"

        # Create fresh settings
        clear_settings_cache()
        settings = create_fresh_settings()

        # Test overrides
        override_results = []

        override_results.append(
            print_test_result(
                "Password Min Length Override",
                "10",
                str(settings.security.password_min_length),
            )
        )

        override_results.append(
            print_test_result(
                "Max Concurrent Updates Override",
                "5",
                str(settings.updates.max_concurrent_updates),
            )
        )

        override_results.append(
            print_test_result(
                "Log Level Override", "DEBUG", settings.logging.log_level.value
            )
        )

        # Test 5: Settings manager cache behavior
        print("\n5. Testing settings manager cache behavior...")

        from app.config import get_settings, reload_settings

        # Set initial environment
        os.environ["HARBOR_MODE"] = "homelab"
        clear_settings_cache()

        # Get cached settings
        settings1 = get_settings()
        profile1 = settings1.deployment_profile.value

        # Change environment
        os.environ["HARBOR_MODE"] = "development"

        # Get settings again (should detect change)
        settings2 = get_settings()
        profile2 = settings2.deployment_profile.value

        cache_results = []
        cache_results.append(print_test_result("Initial profile", "homelab", profile1))
        cache_results.append(
            print_test_result("Changed profile", "development", profile2)
        )

        # Test forced reload
        os.environ["HARBOR_MODE"] = "production"
        settings3 = reload_settings()
        profile3 = settings3.deployment_profile.value

        cache_results.append(
            print_test_result("Reloaded profile", "production", profile3)
        )

        # Final results
        print_test_header("Test Results Summary")

        all_results = (
            [success1, success2] + profile_results + override_results + cache_results
        )

        passed = sum(all_results)
        total = len(all_results)

        print(f"Overall: {passed}/{total} tests passed ({(passed / total * 100):.1f}%)")

        if passed == total:
            print(
                "\n🎉 All tests passed! Environment variable handling is working correctly."
            )
            return True
        else:
            print(
                f"\n💥 {total - passed} tests failed. Environment variable handling needs more work."
            )
            return False

    except Exception as e:
        print(f"❌ Test suite failed with exception: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Restore original environment
        for var, original_value in original_values.items():
            if original_value is None:
                if var in os.environ:
                    del os.environ[var]
            else:
                os.environ[var] = original_value


def test_pydantic_behavior():
    """Test Pydantic's behavior directly"""

    print_test_header("Testing Pydantic BaseSettings Behavior")

    try:
        from pydantic_settings import BaseSettings
        from pydantic import Field
        from enum import Enum

        class TestProfile(str, Enum):
            HOMELAB = "homelab"
            DEVELOPMENT = "development"
            PRODUCTION = "production"

        class DirectSettings(BaseSettings):
            deployment_profile: TestProfile = Field(
                default=TestProfile.HOMELAB, env="HARBOR_MODE"
            )

            class Config:
                env_file = ".env"
                case_sensitive = False

        # Test direct Pydantic behavior
        test_cases = [
            ("homelab", TestProfile.HOMELAB),
            ("development", TestProfile.DEVELOPMENT),
            ("production", TestProfile.PRODUCTION),
        ]

        results = []

        for env_value, expected_enum in test_cases:
            os.environ["HARBOR_MODE"] = env_value

            # Create fresh instance each time
            settings = DirectSettings()
            actual = settings.deployment_profile

            success = actual == expected_enum
            status = "✅" if success else "❌"
            print(
                f"   {status} ENV='{env_value}' -> Expected={expected_enum.value}, Actual={actual.value}"
            )
            results.append(success)

        passed = sum(results)
        total = len(results)

        print(f"\nDirect Pydantic Test: {passed}/{total} passed")
        return passed == total

    except Exception as e:
        print(f"❌ Direct Pydantic test failed: {e}")
        return False


def main():
    """Run all debug tests"""

    print("🔍 Harbor Configuration Fix - Debug Test Suite")
    print("=" * 60)

    results = []

    # Test 1: Direct Pydantic behavior
    results.append(test_pydantic_behavior())

    # Test 2: Harbor configuration system
    results.append(test_environment_variable_handling())

    # Final summary
    print_test_header("Final Test Summary")

    total_passed = sum(results)
    total_tests = len(results)

    test_names = ["Direct Pydantic BaseSettings", "Harbor Configuration System"]

    for i, (test_name, passed) in enumerate(zip(test_names, results)):
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")

    print(f"\nOverall Result: {total_passed}/{total_tests} test suites passed")

    if total_passed == total_tests:
        print("\n🎉 SUCCESS: All environment variable handling is working correctly!")
        print("\n💡 You can now run:")
        print("   python test_config.py")
        print("   python test_db_implementation.py")
        return True
    else:
        print("\n💥 FAILURE: Environment variable handling still has issues.")
        print("\n🔧 Next steps:")
        print("   1. Review the failing test cases above")
        print("   2. Check Pydantic version compatibility")
        print("   3. Verify environment variable naming conventions")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
