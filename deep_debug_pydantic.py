#!/usr/bin/env python3
"""
Deep debug script to understand exactly why Pydantic isn't reading environment variables

This script will help us understand the root cause and implement a proper fix.
"""

import os
import sys
from pathlib import Path


# Add app to path
sys.path.insert(0, str(Path(__file__).parent))


def debug_pydantic_sources():
    """Debug what sources Pydantic is actually using"""

    print("🔍 Deep Debugging Pydantic Environment Variable Sources")
    print("=" * 60)

    try:
        from enum import Enum

        from pydantic import Field
        from pydantic_settings import BaseSettings

        class TestProfile(str, Enum):
            HOMELAB = "homelab"
            DEVELOPMENT = "development"
            PRODUCTION = "production"

        # Create a test settings class with detailed source debugging
        class DebugSettings(BaseSettings):
            deployment_profile: TestProfile = Field(
                default=TestProfile.HOMELAB, env="HARBOR_MODE"
            )

            password_min_length: int = Field(
                default=6, env="HARBOR_SECURITY_PASSWORD_MIN_LENGTH"
            )

            def __init__(self, **data):
                print(f"  🔧 DebugSettings.__init__ called with data: {data}")
                print(f"  🌍 Current HARBOR_MODE env var: {os.getenv('HARBOR_MODE')}")
                print(
                    f"  🌍 Current PASSWORD env var: {os.getenv('HARBOR_SECURITY_PASSWORD_MIN_LENGTH')}"
                )

                # Call parent init
                super().__init__(**data)

                print(f"  📝 Final deployment_profile: {self.deployment_profile.value}")
                print(f"  📝 Final password_min_length: {self.password_min_length}")

            class Config:
                env_file = ".env"
                env_file_encoding = "utf-8"
                case_sensitive = False
                extra = "ignore"

                @classmethod
                def customise_sources(
                    cls,
                    init_settings,
                    env_settings,
                    file_secret_settings,
                ):
                    print("  🎯 Pydantic customise_sources called")
                    print(
                        "  📖 Available sources: init_settings, env_settings, file_secret_settings"
                    )

                    # Let's see what env_settings actually contains
                    try:
                        # This is a hack to peek into env_settings
                        env_data = {}
                        if callable(env_settings):
                            # Try to call it and see what we get
                            env_result = env_settings()
                            print(f"  🌍 env_settings() returned: {env_result}")
                            env_data = env_result
                    except Exception as e:
                        print(f"  ❌ Could not peek into env_settings: {e}")

                    # Return sources in priority order (env first, then init, then file)
                    return (
                        env_settings,
                        init_settings,
                        file_secret_settings,
                    )

        print("\n1. Testing with direct environment variables...")

        # Clear environment first
        for var in ["HARBOR_MODE", "HARBOR_SECURITY_PASSWORD_MIN_LENGTH"]:
            if var in os.environ:
                del os.environ[var]

        # Test 1: Default values
        print("\nTest 1: Default values (no env vars)")
        settings1 = DebugSettings()

        # Test 2: Set environment and create new instance
        print("\nTest 2: Set environment variables and create new instance")
        os.environ["HARBOR_MODE"] = "development"
        os.environ["HARBOR_SECURITY_PASSWORD_MIN_LENGTH"] = "12"

        settings2 = DebugSettings()

        # Test 3: Change environment again
        print("\nTest 3: Change environment again")
        os.environ["HARBOR_MODE"] = "production"
        os.environ["HARBOR_SECURITY_PASSWORD_MIN_LENGTH"] = "15"

        settings3 = DebugSettings()

        print("\n" + "=" * 60)
        print("Summary of Results:")
        print(
            f"Settings 1 (no env): profile={settings1.deployment_profile.value}, password={settings1.password_min_length}"
        )
        print(
            f"Settings 2 (development): profile={settings2.deployment_profile.value}, password={settings2.password_min_length}"
        )
        print(
            f"Settings 3 (production): profile={settings3.deployment_profile.value}, password={settings3.password_min_length}"
        )

        return settings1, settings2, settings3

    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback

        traceback.print_exc()
        return None


def test_manual_environment_reading():
    """Test reading environment variables manually vs Pydantic"""

    print("\n🔍 Testing Manual vs Pydantic Environment Reading")
    print("=" * 60)

    # Set test environment
    os.environ["HARBOR_MODE"] = "development"
    os.environ["HARBOR_SECURITY_PASSWORD_MIN_LENGTH"] = "10"

    print("Set environment variables:")
    print(f"  HARBOR_MODE = {os.getenv('HARBOR_MODE')}")
    print(
        f"  HARBOR_SECURITY_PASSWORD_MIN_LENGTH = {os.getenv('HARBOR_SECURITY_PASSWORD_MIN_LENGTH')}"
    )

    # Test manual reading
    print("\nManual environment reading:")
    manual_profile = os.getenv("HARBOR_MODE", "homelab")
    manual_password = int(os.getenv("HARBOR_SECURITY_PASSWORD_MIN_LENGTH", "6"))
    print(f"  Manual profile: {manual_profile}")
    print(f"  Manual password: {manual_password}")

    # Test with explicit initialization
    try:
        from enum import Enum

        from pydantic import Field
        from pydantic_settings import BaseSettings

        class TestProfile(str, Enum):
            HOMELAB = "homelab"
            DEVELOPMENT = "development"
            PRODUCTION = "production"

        class ManualSettings(BaseSettings):
            deployment_profile: TestProfile = Field(default=TestProfile.HOMELAB)
            password_min_length: int = Field(default=6)

            def __init__(self, **data):
                # Manually read environment if not provided in data
                if "deployment_profile" not in data:
                    env_profile = os.getenv("HARBOR_MODE")
                    if env_profile:
                        try:
                            data["deployment_profile"] = TestProfile(env_profile)
                            print(
                                f"  📖 Manually set deployment_profile to {env_profile}"
                            )
                        except ValueError:
                            print(f"  ⚠️ Invalid profile value: {env_profile}")

                if "password_min_length" not in data:
                    env_password = os.getenv("HARBOR_SECURITY_PASSWORD_MIN_LENGTH")
                    if env_password:
                        try:
                            data["password_min_length"] = int(env_password)
                            print(
                                f"  📖 Manually set password_min_length to {env_password}"
                            )
                        except ValueError:
                            print(f"  ⚠️ Invalid password length: {env_password}")

                super().__init__(**data)

        print("\nManual Pydantic approach:")
        manual_settings = ManualSettings()
        print(f"  Manual Pydantic profile: {manual_settings.deployment_profile.value}")
        print(f"  Manual Pydantic password: {manual_settings.password_min_length}")

        return True

    except Exception as e:
        print(f"❌ Manual test failed: {e}")
        return False


def test_different_pydantic_approaches():
    """Test different approaches to make Pydantic work with environment variables"""

    print("\n🧪 Testing Different Pydantic Approaches")
    print("=" * 60)

    # Set environment
    os.environ["HARBOR_MODE"] = "development"

    approaches = []

    # Approach 1: Standard BaseSettings
    try:
        from enum import Enum

        from pydantic import Field
        from pydantic_settings import BaseSettings

        class TestProfile(str, Enum):
            HOMELAB = "homelab"
            DEVELOPMENT = "development"
            PRODUCTION = "production"

        print("\nApproach 1: Standard BaseSettings")

        class StandardSettings(BaseSettings):
            deployment_profile: TestProfile = Field(
                default=TestProfile.HOMELAB, env="HARBOR_MODE"
            )

            model_config = {
                "env_file": ".env",
                "env_file_encoding": "utf-8",
                "case_sensitive": False,
                "extra": "ignore",
            }

        settings1 = StandardSettings()
        result1 = settings1.deployment_profile.value
        print(f"  Result: {result1}")
        approaches.append(("Standard", result1 == "development"))

    except Exception as e:
        print(f"  ❌ Standard approach failed: {e}")
        approaches.append(("Standard", False))

    # Approach 2: Custom __init__ with environment reading
    try:
        print("\nApproach 2: Custom __init__ with environment reading")

        class CustomInitSettings(BaseSettings):
            deployment_profile: TestProfile = Field(default=TestProfile.HOMELAB)

            def __init__(self, **data):
                # Read environment in __init__
                env_profile = os.getenv("HARBOR_MODE")
                if env_profile and "deployment_profile" not in data:
                    try:
                        data["deployment_profile"] = TestProfile(env_profile)
                    except ValueError:
                        pass

                super().__init__(**data)

        settings2 = CustomInitSettings()
        result2 = settings2.deployment_profile.value
        print(f"  Result: {result2}")
        approaches.append(("Custom Init", result2 == "development"))

    except Exception as e:
        print(f"  ❌ Custom init approach failed: {e}")
        approaches.append(("Custom Init", False))

    # Approach 3: Factory function
    try:
        print("\nApproach 3: Factory function")

        class FactorySettings(BaseSettings):
            deployment_profile: TestProfile = Field(default=TestProfile.HOMELAB)

        def create_settings():
            # Read environment and pass as init data
            init_data = {}

            env_profile = os.getenv("HARBOR_MODE")
            if env_profile:
                try:
                    init_data["deployment_profile"] = TestProfile(env_profile)
                except ValueError:
                    pass

            return FactorySettings(**init_data)

        settings3 = create_settings()
        result3 = settings3.deployment_profile.value
        print(f"  Result: {result3}")
        approaches.append(("Factory", result3 == "development"))

    except Exception as e:
        print(f"  ❌ Factory approach failed: {e}")
        approaches.append(("Factory", False))

    # Summary
    print(f"\n{'=' * 60}")
    print("Approach Results:")
    for name, success in approaches:
        status = "✅" if success else "❌"
        print(f"  {status} {name}")

    working_approaches = [name for name, success in approaches if success]
    if working_approaches:
        print(f"\n🎉 Working approaches: {', '.join(working_approaches)}")
        return working_approaches[0]  # Return first working approach
    else:
        print("\n💥 No approaches worked!")
        return None


def main():
    """Run all debug tests"""

    print("🛳️ Harbor Deep Debug - Environment Variable Issue")
    print("=" * 60)

    # Debug Pydantic sources
    result1 = debug_pydantic_sources()

    # Test manual reading
    result2 = test_manual_environment_reading()

    # Test different approaches
    working_approach = test_different_pydantic_approaches()

    print(f"\n{'=' * 60}")
    print("CONCLUSIONS:")
    print(f"{'=' * 60}")

    if working_approach:
        print(f"✅ Found working approach: {working_approach}")
        print("\n🔧 SOLUTION:")
        if working_approach == "Factory":
            print("  Use factory function approach to read environment variables")
            print("  and pass them as initialization data to Pydantic")
        elif working_approach == "Custom Init":
            print("  Use custom __init__ method to read environment variables")
            print("  and override default values")
        else:
            print(f"  Use the {working_approach} approach")

        print("\n💡 This means we need to rewrite the configuration system")
        print("   to explicitly read environment variables rather than")
        print("   relying on Pydantic's automatic environment handling.")

    else:
        print("❌ No working approaches found!")
        print("\n🔧 ALTERNATIVE SOLUTION:")
        print("  We may need to abandon Pydantic BaseSettings entirely")
        print("  and implement our own configuration system that explicitly")
        print("  reads environment variables using os.getenv()")

    print(f"\n{'=' * 60}")
    print("NEXT STEPS:")
    print(f"{'=' * 60}")
    print("1. Implement the working approach in Harbor configuration")
    print("2. Test thoroughly with all profile switching scenarios")
    print("3. Ensure nested settings classes also work properly")
    print("4. Update test scripts to validate the fix")


if __name__ == "__main__":
    main()
