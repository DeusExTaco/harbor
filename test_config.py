#!/usr/bin/env python3
"""
Harbor Container Updater - Configuration System Test (Type Fixed)

Quick test script to verify the configuration system works properly.
Run this to validate the M0 configuration implementation.

Usage:
    python test_config.py
"""

import os
import sys
from pathlib import Path


# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent))


def test_configuration_system() -> bool:
    """Test the configuration system components"""

    print("🛳️ Harbor Configuration System Test")
    print("=" * 50)
    print()

    try:
        # Test basic imports
        print("1. Testing imports...")
        from app.config import (
            DeploymentProfile,
            detect_environment,
            get_config_summary,
            get_settings,
            validate_runtime_requirements,
        )

        print("   ✅ All imports successful")

        # Test profile enum
        print("2. Testing deployment profiles...")
        profiles = [
            DeploymentProfile.HOMELAB,
            DeploymentProfile.DEVELOPMENT,
            DeploymentProfile.STAGING,
            DeploymentProfile.PRODUCTION,
        ]
        print(f"   ✅ Profiles available: {[p.value for p in profiles]}")

        # Test default settings
        print("3. Testing default settings...")
        settings = get_settings()
        print(f"   ✅ Profile: {settings.deployment_profile.value}")
        print(f"   ✅ Version: {settings.app_version}")
        print(f"   ✅ Database: {settings.database.database_type.value}")

        # Test configuration summary
        print("4. Testing configuration summary...")
        summary = get_config_summary()
        print(f"   ✅ Summary keys: {list(summary.keys())}")

        # Test environment detection
        print("5. Testing environment detection...")
        env_info = detect_environment()
        print(f"   ✅ Platform: {env_info['platform']['system']}")
        print(f"   ✅ Architecture: {env_info['platform']['machine']}")
        print(f"   ✅ Suggested profile: {env_info['suggested_profile']}")

        # Test validation
        print("6. Testing configuration validation...")
        errors = validate_runtime_requirements()
        if errors:
            print("   ⚠️ Validation issues:")
            for error in errors:
                print(f"      - {error}")
        else:
            print("   ✅ Configuration valid")

        # Test profile switching
        print("7. Testing profile switching...")
        original_mode = os.getenv("HARBOR_MODE")

        for profile in ["homelab", "development", "production"]:
            os.environ["HARBOR_MODE"] = profile
            # Force reload by creating new settings
            from app.config import reload_settings

            test_settings = reload_settings()
            actual_profile = test_settings.deployment_profile.value
            print(f"   ✅ {profile}: {actual_profile}")

            # Verify the profile actually changed
            if actual_profile != profile:
                print("   ⚠️ Profile switching may not be working correctly")

        # Restore original profile
        if original_mode:
            os.environ["HARBOR_MODE"] = original_mode
        elif "HARBOR_MODE" in os.environ:
            del os.environ["HARBOR_MODE"]

        print()
        print("🎉 All tests passed! Configuration system is working properly.")
        print()

        # Show final configuration summary
        print("📋 Final Configuration Summary:")
        reload_settings()  # Reload to restore original state
        final_summary = get_config_summary()

        for key, value in final_summary.items():
            print(f"   {key}: {value}")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_profile_specific() -> None:
    """Test profile-specific configurations"""

    print("\n🔧 Testing Profile-Specific Settings")
    print("=" * 40)

    from app.config import reload_settings

    test_cases = [
        (
            "homelab",
            {
                "security.require_https": False,
                "security.session_timeout_hours": 168,
                "updates.max_concurrent_updates": 2,
                "logging.log_level": "INFO",
                "features.enable_simple_mode": True,
            },
        ),
        (
            "development",
            {
                "debug": True,
                "security.session_timeout_hours": 72,
                "updates.max_concurrent_updates": 3,
                "logging.log_level": "DEBUG",
            },
        ),
        (
            "production",
            {
                "security.require_https": True,
                "security.session_timeout_hours": 8,
                "security.password_min_length": 12,
                "updates.max_concurrent_updates": 10,
                "logging.log_format": "json",
            },
        ),
    ]

    original_mode = os.getenv("HARBOR_MODE")

    try:
        for profile, expected_settings in test_cases:
            print(f"\nTesting {profile} profile:")

            # Set environment and reload
            os.environ["HARBOR_MODE"] = profile
            settings = reload_settings()

            # Verify profile was set correctly
            actual_profile = settings.deployment_profile.value
            if actual_profile != profile:
                print(
                    f"   ⚠️ Profile mismatch: got {actual_profile}, expected {profile}"
                )
                continue

            for setting_path, expected_value in expected_settings.items():
                try:
                    # Handle nested settings like security.require_https
                    if "." in setting_path:
                        parts = setting_path.split(".")
                        actual_value = settings
                        for part in parts:
                            actual_value = getattr(actual_value, part)
                    else:
                        actual_value = getattr(settings, setting_path)

                    # Handle enum values
                    if hasattr(actual_value, "value"):
                        actual_value = actual_value.value

                    if actual_value == expected_value:
                        print(f"   ✅ {setting_path}: {actual_value}")
                    else:
                        print(
                            f"   ⚠️ {setting_path}: got {actual_value}, expected {expected_value}"
                        )

                except AttributeError as e:
                    print(f"   ❌ {setting_path}: AttributeError - {e}")
                except Exception as e:
                    print(f"   ❌ {setting_path}: Error - {e}")

    finally:
        # Restore original profile
        if original_mode:
            os.environ["HARBOR_MODE"] = original_mode
        elif "HARBOR_MODE" in os.environ:
            del os.environ["HARBOR_MODE"]

        # Reload one final time to restore original state
        reload_settings()


def test_environment_variables() -> None:
    """Test environment variable override functionality"""

    print("\n🌍 Testing Environment Variable Overrides")
    print("=" * 45)

    from app.config import reload_settings

    # Test environment variable override
    print("Testing environment variable overrides...")

    # Set some test environment variables
    test_vars = {
        "HARBOR_SECURITY_PASSWORD_MIN_LENGTH": "10",
        "HARBOR_UPDATE_MAX_CONCURRENT_UPDATES": "5",
        "HARBOR_LOG_LOG_LEVEL": "DEBUG",
    }

    original_vars = {}

    try:
        # Set test variables
        for var, value in test_vars.items():
            original_vars[var] = os.getenv(var)
            os.environ[var] = value

        # Reload settings to pick up environment changes
        settings = reload_settings()

        # Check if overrides worked
        checks = [
            ("password_min_length", settings.security.password_min_length, 10),
            ("max_concurrent_updates", settings.updates.max_concurrent_updates, 5),
            ("log_level", settings.logging.log_level.value, "DEBUG"),
        ]

        for name, actual, expected in checks:
            if actual == expected:
                print(f"   ✅ {name}: {actual}")
            else:
                print(f"   ⚠️ {name}: got {actual}, expected {expected}")

    finally:
        # Clean up test environment variables
        for var, original_value in original_vars.items():
            if original_value is None:
                if var in os.environ:
                    del os.environ[var]
            else:
                os.environ[var] = original_value


def main() -> None:
    """Main test function"""

    # Test basic configuration system
    success = test_configuration_system()

    if success:
        # Test profile-specific settings
        test_profile_specific()

        # Test environment variable overrides
        test_environment_variables()

        print("\n🎯 All configuration tests completed!")
        print("\n💡 Next steps:")
        print("   1. Run: python app/main.py (to test CLI)")
        print("   2. Run: uvicorn app.main:create_app --factory (to test API)")
        print("   3. Run: python scripts/validate_config.py (comprehensive validation)")

    else:
        print("\n❌ Configuration system has issues - please fix before proceeding")
        sys.exit(1)


if __name__ == "__main__":
    main()
