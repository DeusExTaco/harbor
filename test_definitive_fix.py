#!/usr/bin/env python3
"""
Test script for the definitive configuration fix

This script validates that the factory pattern approach correctly
handles environment variable changes.
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
    success = str(expected) == str(actual)
    status = "✅" if success else "❌"
    print(f"   {status} {test_name}: Expected='{expected}', Actual='{actual}'")
    return success


def test_factory_pattern():
    """Test the factory pattern approach"""

    print_test_header("Testing Factory Pattern Configuration")

    # Clean environment first
    env_vars_to_test = [
        "HARBOR_MODE",
        "HARBOR_DEBUG",
        "HARBOR_SECURITY_PASSWORD_MIN_LENGTH",
        "HARBOR_UPDATE_MAX_CONCURRENT_UPDATES",
        "HARBOR_LOG_LOG_LEVEL",
    ]

    original_values = {}
    for var in env_vars_to_test:
        original_values[var] = os.getenv(var)
        if var in os.environ:
            del os.environ[var]

    try:
        from app.config import create_fresh_settings, clear_settings_cache

        results = []

        # Test 1: Default values (homelab profile)
        print("\n1. Testing default values (no environment variables)...")
        settings1 = create_fresh_settings()

        results.append(
            print_test_result(
                "Default profile", "homelab", settings1.deployment_profile.value
            )
        )
        results.append(
            print_test_result("Default debug", "False", str(settings1.debug))
        )
        results.append(
            print_test_result(
                "Default password length",
                "6",
                str(settings1.security.password_min_length),
            )
        )
        results.append(
            print_test_result(
                "Default concurrent updates",
                "2",
                str(settings1.updates.max_concurrent_updates),
            )
        )
        results.append(
            print_test_result(
                "Default log level", "INFO", settings1.logging.log_level.value
            )
        )

        # Test 2: Development profile
        print("\n2. Testing development profile...")
        os.environ["HARBOR_MODE"] = "development"

        settings2 = create_fresh_settings()

        results.append(
            print_test_result(
                "Development profile", "development", settings2.deployment_profile.value
            )
        )
        results.append(
            print_test_result("Development debug", "True", str(settings2.debug))
        )
        results.append(
            print_test_result(
                "Development log level", "DEBUG", settings2.logging.log_level.value
            )
        )

        # Test 3: Production profile
        print("\n3. Testing production profile...")
        os.environ["HARBOR_MODE"] = "production"

        settings3 = create_fresh_settings()

        results.append(
            print_test_result(
                "Production profile", "production", settings3.deployment_profile.value
            )
        )
        results.append(
            print_test_result(
                "Production HTTPS", "True", str(settings3.security.require_https)
            )
        )
        results.append(
            print_test_result(
                "Production password length",
                "12",
                str(settings3.security.password_min_length),
            )
        )
        results.append(
            print_test_result(
                "Production concurrent updates",
                "10",
                str(settings3.updates.max_concurrent_updates),
            )
        )

        # Test 4: Environment variable overrides
        print("\n4. Testing environment variable overrides...")
        os.environ["HARBOR_MODE"] = "homelab"
        os.environ["HARBOR_SECURITY_PASSWORD_MIN_LENGTH"] = "15"
        os.environ["HARBOR_UPDATE_MAX_CONCURRENT_UPDATES"] = "7"
        os.environ["HARBOR_LOG_LOG_LEVEL"] = "DEBUG"
        os.environ["HARBOR_DEBUG"] = "true"

        settings4 = create_fresh_settings()

        results.append(
            print_test_result(
                "Override profile", "homelab", settings4.deployment_profile.value
            )
        )
        results.append(
            print_test_result("Override debug", "True", str(settings4.debug))
        )
        results.append(
            print_test_result(
                "Override password length",
                "15",
                str(settings4.security.password_min_length),
            )
        )
        results.append(
            print_test_result(
                "Override concurrent updates",
                "7",
                str(settings4.updates.max_concurrent_updates),
            )
        )
        results.append(
            print_test_result(
                "Override log level", "DEBUG", settings4.logging.log_level.value
            )
        )

        # Test 5: Settings manager cache behavior
        print("\n5. Testing settings manager...")
        from app.config import get_settings, reload_settings

        # Clear cache and set initial environment
        clear_settings_cache()
        os.environ["HARBOR_MODE"] = "homelab"

        settings5a = get_settings()
        results.append(
            print_test_result(
                "Manager initial", "homelab", settings5a.deployment_profile.value
            )
        )

        # Change environment - manager should detect change
        os.environ["HARBOR_MODE"] = "development"

        settings5b = get_settings()
        results.append(
            print_test_result(
                "Manager auto-detect",
                "development",
                settings5b.deployment_profile.value,
            )
        )

        # Force reload
        os.environ["HARBOR_MODE"] = "production"
        settings5c = reload_settings()
        results.append(
            print_test_result(
                "Manager reload", "production", settings5c.deployment_profile.value
            )
        )

        # Calculate results
        passed = sum(results)
        total = len(results)

        print(
            f"\nFactory Pattern Test: {passed}/{total} tests passed ({(passed / total * 100):.1f}%)"
        )

        return passed == total

    except Exception as e:
        print(f"❌ Factory pattern test failed: {e}")
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


def test_environment_reader():
    """Test the EnvironmentReader class directly"""

    print_test_header("Testing EnvironmentReader Class")

    try:
        from app.config import EnvironmentReader, LogLevel, DeploymentProfile

        env = EnvironmentReader()
        results = []

        # Set up test environment
        os.environ["TEST_STR"] = "hello"
        os.environ["TEST_BOOL_TRUE"] = "true"
        os.environ["TEST_BOOL_FALSE"] = "false"
        os.environ["TEST_INT"] = "42"
        os.environ["TEST_ENUM"] = "development"
        os.environ["TEST_LIST"] = "a,b,c"

        # Test string reading
        result = env.read_str("TEST_STR", "default")
        results.append(print_test_result("String reading", "hello", result))

        # Test boolean reading
        result_true = env.read_bool("TEST_BOOL_TRUE", False)
        results.append(print_test_result("Boolean true", "True", str(result_true)))

        result_false = env.read_bool("TEST_BOOL_FALSE", True)
        results.append(print_test_result("Boolean false", "False", str(result_false)))

        # Test integer reading
        result_int = env.read_int("TEST_INT", 0)
        results.append(print_test_result("Integer reading", "42", str(result_int)))

        # Test enum reading
        result_enum = env.read_enum(
            "TEST_ENUM", DeploymentProfile, DeploymentProfile.HOMELAB
        )
        results.append(
            print_test_result("Enum reading", "development", result_enum.value)
        )

        # Test list reading
        result_list = env.read_list("TEST_LIST", [])
        results.append(
            print_test_result("List reading", "['a', 'b', 'c']", str(result_list))
        )

        # Test defaults (missing environment variables)
        result_default = env.read_str("MISSING_VAR", "default_value")
        results.append(
            print_test_result("Default value", "default_value", result_default)
        )

        # Cleanup
        for var in [
            "TEST_STR",
            "TEST_BOOL_TRUE",
            "TEST_BOOL_FALSE",
            "TEST_INT",
            "TEST_ENUM",
            "TEST_LIST",
        ]:
            if var in os.environ:
                del os.environ[var]

        passed = sum(results)
        total = len(results)

        print(
            f"\nEnvironmentReader Test: {passed}/{total} tests passed ({(passed / total * 100):.1f}%)"
        )

        return passed == total

    except Exception as e:
        print(f"❌ EnvironmentReader test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_profile_specific_behavior():
    """Test that profile-specific settings work correctly"""

    print_test_header("Testing Profile-Specific Behavior")

    try:
        from app.config import create_fresh_settings

        results = []

        # Test homelab profile specifics
        print("\n1. Testing homelab profile specifics...")
        if "HARBOR_MODE" in os.environ:
            del os.environ["HARBOR_MODE"]

        settings_homelab = create_fresh_settings()

        results.append(
            print_test_result(
                "Homelab profile", "homelab", settings_homelab.deployment_profile.value
            )
        )
        results.append(
            print_test_result(
                "Homelab HTTPS", "False", str(settings_homelab.security.require_https)
            )
        )
        results.append(
            print_test_result(
                "Homelab session timeout",
                "168",
                str(settings_homelab.security.session_timeout_hours),
            )
        )
        results.append(
            print_test_result(
                "Homelab simple mode",
                "True",
                str(settings_homelab.features.enable_simple_mode),
            )
        )

        # Test development profile specifics
        print("\n2. Testing development profile specifics...")
        os.environ["HARBOR_MODE"] = "development"

        settings_dev = create_fresh_settings()

        results.append(
            print_test_result(
                "Development profile",
                "development",
                settings_dev.deployment_profile.value,
            )
        )
        results.append(
            print_test_result("Development debug", "True", str(settings_dev.debug))
        )
        results.append(
            print_test_result(
                "Development log level", "DEBUG", settings_dev.logging.log_level.value
            )
        )
        results.append(
            print_test_result(
                "Development session timeout",
                "72",
                str(settings_dev.security.session_timeout_hours),
            )
        )

        # Test production profile specifics
        print("\n3. Testing production profile specifics...")
        os.environ["HARBOR_MODE"] = "production"

        settings_prod = create_fresh_settings()

        results.append(
            print_test_result(
                "Production profile",
                "production",
                settings_prod.deployment_profile.value,
            )
        )
        results.append(
            print_test_result("Production debug", "False", str(settings_prod.debug))
        )
        results.append(
            print_test_result(
                "Production HTTPS", "True", str(settings_prod.security.require_https)
            )
        )
        results.append(
            print_test_result(
                "Production API key required",
                "True",
                str(settings_prod.security.api_key_required),
            )
        )
        results.append(
            print_test_result(
                "Production password length",
                "12",
                str(settings_prod.security.password_min_length),
            )
        )
        results.append(
            print_test_result(
                "Production concurrent updates",
                "10",
                str(settings_prod.updates.max_concurrent_updates),
            )
        )
        results.append(
            print_test_result(
                "Production simple mode",
                "False",
                str(settings_prod.features.enable_simple_mode),
            )
        )

        # Clean up
        if "HARBOR_MODE" in os.environ:
            del os.environ["HARBOR_MODE"]

        passed = sum(results)
        total = len(results)

        print(
            f"\nProfile-Specific Test: {passed}/{total} tests passed ({(passed / total * 100):.1f}%)"
        )

        return passed == total

    except Exception as e:
        print(f"❌ Profile-specific test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests for the definitive fix"""

    print("🛳️ Harbor Configuration - Definitive Fix Test")
    print("=" * 60)

    test_results = []

    # Test 1: Environment reader
    test_results.append(("EnvironmentReader", test_environment_reader()))

    # Test 2: Factory pattern
    test_results.append(("Factory Pattern", test_factory_pattern()))

    # Test 3: Profile-specific behavior
    test_results.append(("Profile-Specific Behavior", test_profile_specific_behavior()))

    # Final summary
    print_test_header("Final Test Results")

    passed_tests = 0
    total_tests = len(test_results)

    for test_name, passed in test_results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")
        if passed:
            passed_tests += 1

    success_rate = (passed_tests / total_tests) * 100
    print(
        f"\nOverall Result: {passed_tests}/{total_tests} test suites passed ({success_rate:.1f}%)"
    )

    if passed_tests == total_tests:
        print("\n🎉 SUCCESS! Definitive configuration fix is working!")
        print("\n✅ Environment variables are now properly detected and applied")
        print("✅ Profile switching works correctly")
        print("✅ Environment variable overrides work")
        print("✅ Settings manager properly detects changes")

        print("\n💡 You can now run:")
        print("   python test_config.py")
        print("   python test_db_implementation.py")
        print("   uvicorn app.main:create_app --factory")

        return True
    else:
        print(f"\n💥 FAILURE: {total_tests - passed_tests} test suite(s) failed")
        print("\n🔧 The definitive fix still needs work")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
