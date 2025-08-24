"""
Smoke integration tests for Harbor Container Updater.

These tests verify basic functionality and infrastructure components
without requiring Docker or external dependencies.
"""

import os
import tempfile
import unittest
from pathlib import Path


class TestSmokeIntegration(unittest.TestCase):
    """Smoke tests for basic Harbor functionality"""

    def test_environment_variable_handling(self) -> None:
        """Test that environment variables can be set and read"""
        test_var = "HARBOR_TEST_VARIABLE"
        test_value = "test_value_12345"

        # Clean up first
        if test_var in os.environ:
            del os.environ[test_var]

        try:
            os.environ[test_var] = test_value
            self.assertEqual(os.getenv(test_var), test_value)
        finally:
            # Cleanup
            if test_var in os.environ:
                del os.environ[test_var]

    def test_file_system_operations(self) -> None:
        """Test basic file system operations work correctly"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.assertTrue(temp_path.exists())
            self.assertTrue(temp_path.is_dir())

            # Test file creation and reading
            test_file = temp_path / "test_file.txt"
            test_file.write_text("test content")
            self.assertTrue(test_file.exists())
            self.assertEqual(test_file.read_text(), "test content")

    def test_database_url_configuration(self) -> None:
        """Test database URL configuration handling"""
        test_db_url = "sqlite:///test_harbor.db"
        original_db_url = os.getenv("DATABASE_URL")

        try:
            os.environ["DATABASE_URL"] = test_db_url
            self.assertEqual(os.getenv("DATABASE_URL"), test_db_url)
        finally:
            # Restore original value
            if original_db_url is not None:
                os.environ["DATABASE_URL"] = original_db_url
            elif "DATABASE_URL" in os.environ:
                del os.environ["DATABASE_URL"]

    def test_harbor_config_import(self) -> None:
        """Test that Harbor configuration modules can be imported"""
        try:
            import app.config  # noqa: F401

            # If we get here, import succeeded
            self.assertTrue(True, "Harbor config module imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import Harbor config module: {e}")

    def test_harbor_main_import(self) -> None:
        """Test that Harbor main application can be imported"""
        try:
            import app.main  # noqa: F401

            # If we get here, import succeeded
            self.assertTrue(True, "Harbor main module imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import Harbor main module: {e}")

    def test_configuration_profiles_defined(self) -> None:
        """Test that configuration profiles are properly defined"""
        try:
            from app.config import DeploymentProfile

            # Check all expected profiles exist
            expected_profiles = ["homelab", "development", "staging", "production"]
            actual_profiles = [profile.value for profile in DeploymentProfile]

            for expected in expected_profiles:
                self.assertIn(
                    expected, actual_profiles, f"Profile {expected} not found"
                )

        except ImportError as e:
            self.fail(f"Failed to import DeploymentProfile: {e}")

    def test_fastapi_app_creation(self) -> None:
        """Test that FastAPI application can be created"""
        try:
            from app.main import create_app

            app = create_app()
            self.assertIsNotNone(app, "FastAPI app creation returned None")

            # Basic check that it's a FastAPI app
            self.assertTrue(
                hasattr(app, "openapi"), "Created app doesn't have FastAPI methods"
            )

        except Exception as e:
            self.fail(f"Failed to create FastAPI app: {e}")


if __name__ == "__main__":
    unittest.main()
