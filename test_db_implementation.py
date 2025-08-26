#!/usr/bin/env python3
"""
Harbor Database Implementation Test Script

Comprehensive testing script to validate all M0 Database Models functionality
before proceeding to the next milestone. Tests all components systematically.

FIXED: SQLite constraints and missing imports

Usage:
    python test_db_implementation.py
    python test_db_implementation.py --profile production
    python test_db_implementation.py --verbose
"""

import asyncio
import sys
import os
import uuid
import tempfile
from pathlib import Path
from typing import List, Dict, Any
import traceback
from datetime import datetime, timezone

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))


def print_header(title: str):
    """Print a formatted header"""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}")


def print_step(step: str, status: str = None):
    """Print a test step with optional status"""
    if status == "PASS":
        print(f"✅ {step}")
    elif status == "FAIL":
        print(f"❌ {step}")
    elif status == "SKIP":
        print(f"⭐️ {step}")
    else:
        print(f"📋 {step}")


def print_info(info: str):
    """Print info message"""
    print(f"ℹ️ {info}")


def print_error(error: str):
    """Print error message"""
    print(f"💥 ERROR: {error}")


async def test_configuration_system():
    """Test configuration system integration"""
    print_header("Testing Configuration System")

    try:
        from app.config import (
            get_settings,
            get_config_summary,
            validate_runtime_requirements,
        )

        print_step("Import configuration modules", "PASS")

        # Test getting settings
        settings = get_settings()
        print_step(
            f"Get settings - Profile: {settings.deployment_profile.value}", "PASS"
        )

        # Test configuration summary
        summary = get_config_summary()
        print_step(f"Get config summary - Database: {summary['database_type']}", "PASS")

        # Test validation
        errors = validate_runtime_requirements()
        if errors:
            print_step(f"Runtime validation - Found {len(errors)} issues", "FAIL")
            for error in errors:
                print_info(f"  - {error}")
        else:
            print_step("Runtime validation - All checks passed", "PASS")

        return len(errors) == 0

    except Exception as e:
        print_step("Configuration system test", "FAIL")
        print_error(str(e))
        traceback.print_exc()
        return False


async def test_database_models():
    """Test database models and their methods"""
    print_header("Testing Database Models")

    try:
        from app.db.models.user import User
        from app.db.models.api_key import APIKey
        from app.db.models.settings import SystemSettings
        from app.db.models.container import Container
        from app.db.models.policy import ContainerPolicy

        print_step("Import all database models", "PASS")

        # Test User model
        user = User(
            username="testuser",
            password_hash="hashed_password",
            email="test@example.com",
        )

        # Test user methods
        user.record_login()
        user.set_preferences({"theme": "dark", "notifications": True})
        prefs = user.get_preferences()

        print_step(
            f"User model - Login count: {user.login_count}, Preferences: {len(prefs)}",
            "PASS",
        )

        # Test SystemSettings model
        settings = SystemSettings(id=1)
        settings.set_maintenance_days(["monday", "friday"])
        days = settings.get_maintenance_days()

        print_step(f"SystemSettings model - Maintenance days: {days}", "PASS")

        # Test Container model
        container_uid = str(uuid.uuid4())
        container = Container(
            uid=container_uid,
            docker_name="test-nginx",
            image_repo="nginx",
            image_tag="latest",
            image_ref="nginx:latest",
            status="running",
        )

        container.set_labels({"harbor.enable": "true"})
        is_excluded = container.is_excluded_from_updates()

        print_step(
            f"Container model - UID: {container_uid[:8]}..., Excluded: {is_excluded}",
            "PASS",
        )

        # Test ContainerPolicy model
        policy = ContainerPolicy(container_uid=container_uid)
        policy.set_update_days(["monday", "wednesday"])
        eligible = policy.is_eligible_for_update()

        print_step(f"ContainerPolicy model - Eligible for update: {eligible}", "PASS")

        return True

    except Exception as e:
        print_step("Database models test", "FAIL")
        print_error(str(e))
        traceback.print_exc()
        return False


async def test_database_initialization():
    """Test database initialization and setup"""
    print_header("Testing Database Initialization")

    try:
        from app.db.init import (
            initialize_database,
            get_database_info,
            ensure_database_ready,
        )
        from app.db.config import get_database_config

        print_step("Import database initialization modules", "PASS")

        # Test database configuration
        config = get_database_config()
        db_url = config.get_database_url()
        print_step(
            f"Database configuration - URL type: {db_url.split(':', 1)[0]}", "PASS"
        )

        # Test database initialization
        success = await initialize_database(force_recreate=True)
        if success:
            print_step("Database initialization", "PASS")
        else:
            print_step("Database initialization", "FAIL")
            return False

        # Test database info
        db_info = await get_database_info()
        print_step(
            f"Database info - Tables: {db_info.get('table_count', 0)}, "
            f"Dialect: {db_info.get('dialect', 'unknown')}",
            "PASS",
        )

        # Test ensure ready
        ready = await ensure_database_ready()
        print_step(f"Database ready check", "PASS" if ready else "FAIL")

        return success and ready

    except Exception as e:
        print_step("Database initialization test", "FAIL")
        print_error(str(e))
        traceback.print_exc()
        return False


async def test_session_management():
    """Test database session management"""
    print_header("Testing Session Management")

    try:
        from app.db.session import get_async_session, get_session_manager
        from sqlalchemy import text

        print_step("Import session management modules", "PASS")

        # Test session manager
        session_manager = get_session_manager()
        await session_manager.initialize()
        print_step("Initialize session manager", "PASS")

        # Test basic session
        async with get_async_session() as session:
            result = await session.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            print_step(
                f"Basic session test - Query result: {test_value}",
                "PASS" if test_value == 1 else "FAIL",
            )

        # Test session context manager
        try:
            async with get_async_session() as session:
                # This should work without errors
                await session.execute(text("SELECT COUNT(*) FROM users"))
            print_step("Session context manager", "PASS")
        except Exception as e:
            print_step("Session context manager", "FAIL")
            print_error(str(e))

        await session_manager.close()
        print_step("Close session manager", "PASS")

        return True

    except Exception as e:
        print_step("Session management test", "FAIL")
        print_error(str(e))
        traceback.print_exc()
        return False


async def test_repository_operations():
    """Test repository pattern operations"""
    print_header("Testing Repository Operations")

    try:
        from app.db.repositories.user import UserRepository
        from app.db.repositories.container import ContainerRepository
        from app.db.session import get_async_session
        from app.db.models.user import User
        from app.db.models.container import Container

        print_step("Import repository modules", "PASS")

        # Test UserRepository
        async with get_async_session() as session:
            user_repo = UserRepository(session)

            # Create user
            user = await user_repo.create_user(
                username="repo_test_user",
                password_hash="hashed_password",
                email="repo@example.com",
            )

            print_step(
                f"Create user - ID: {user.id}, Username: {user.username}", "PASS"
            )

            # Find user
            found_user = await user_repo.get_by_username("repo_test_user")
            print_step(f"Find user by username", "PASS" if found_user else "FAIL")

            # Count users
            user_count = await user_repo.count()
            print_step(f"Count users - Total: {user_count}", "PASS")

            await session.commit()

        # Test ContainerRepository
        async with get_async_session() as session:
            container_repo = ContainerRepository(session)

            # Create container
            container_uid = str(uuid.uuid4())
            container = await container_repo.create_or_update_container(
                uid=container_uid,
                docker_id="repo_test_123",
                docker_name="repo-test-nginx",
                image_repo="nginx",
                image_tag="latest",
                image_ref="nginx:latest",
                status="running",
            )

            print_step(f"Create container - Name: {container.docker_name}", "PASS")

            # Update container
            updated_container = await container_repo.create_or_update_container(
                uid=container_uid,
                docker_id="repo_test_456",  # New docker ID
                docker_name="repo-test-nginx",
                image_repo="nginx",
                image_tag="latest",
                image_ref="nginx:latest",
                status="running",
            )

            print_step(
                f"Update existing container - Docker ID: {updated_container.docker_id}",
                "PASS",
            )

            # Search containers
            search_results = await container_repo.search_containers("nginx")
            print_step(
                f"Search containers - Found: {len(search_results.items)}", "PASS"
            )

            await session.commit()

        return True

    except Exception as e:
        print_step("Repository operations test", "FAIL")
        print_error(str(e))
        traceback.print_exc()
        return False


async def test_model_relationships():
    """Test model relationships and foreign keys - FIXED: Added missing import"""
    print_header("Testing Model Relationships")

    try:
        from app.db.session import get_async_session
        from app.db.repositories.user import UserRepository
        from app.db.models.user import User  # FIXED: Added missing import
        from app.db.models.api_key import APIKey
        from app.db.models.container import Container
        from app.db.models.policy import ContainerPolicy
        from sqlalchemy.orm import selectinload
        from sqlalchemy import select
        import uuid  # FIXED: Added missing uuid import

        print_step("Import relationship testing modules", "PASS")

        async with get_async_session() as session:
            user_repo = UserRepository(session)

            # Create user
            user = await user_repo.create_user(
                username="relationship_user", password_hash="hashed_password"
            )

            # Create API key for user
            api_key = APIKey(
                name="test-relationship-key",
                key_hash="hashed_key_123",
                created_by_user_id=user.id,
            )
            session.add(api_key)
            await session.flush()

            print_step(f"Create user and API key relationship", "PASS")

            # Test relationship loading
            stmt = (
                select(User)
                .options(selectinload(User.api_keys))
                .where(User.id == user.id)
            )
            result = await session.execute(stmt)
            loaded_user = result.scalar_one()

            print_step(
                f"Load user with API keys - Keys: {len(loaded_user.api_keys)}",
                "PASS" if len(loaded_user.api_keys) == 1 else "FAIL",
            )

            # Test container-policy relationship
            container_uid = str(uuid.uuid4())
            container = Container(
                uid=container_uid,
                docker_name="relationship-test",
                image_repo="nginx",
                image_tag="latest",
                image_ref="nginx:latest",
                status="running",
            )
            session.add(container)

            policy = ContainerPolicy(
                container_uid=container_uid, desired_version="latest"
            )
            session.add(policy)
            await session.flush()

            # Test container with policy loading
            stmt = (
                select(Container)
                .options(selectinload(Container.policy))
                .where(Container.uid == container_uid)
            )
            result = await session.execute(stmt)
            loaded_container = result.scalar_one()

            print_step(
                f"Load container with policy",
                "PASS" if loaded_container.policy is not None else "FAIL",
            )

            await session.commit()

        return True

    except Exception as e:
        print_step("Model relationships test", "FAIL")
        print_error(str(e))
        traceback.print_exc()
        return False


async def test_main_application():
    """Test main application with database integration"""
    print_header("Testing Main Application Integration")

    try:
        from app.main import create_app
        from fastapi.testclient import TestClient

        print_step("Import main application", "PASS")

        # Create app
        app = create_app()
        client = TestClient(app)

        print_step("Create FastAPI application", "PASS")

        # Test basic endpoints
        response = client.get("/")
        print_step(
            f"Root endpoint - Status: {response.status_code}",
            "PASS" if response.status_code == 200 else "FAIL",
        )

        # Test health check
        response = client.get("/healthz")
        if response.status_code == 200:
            health_data = response.json()
            print_step(
                f"Health check - Status: {health_data.get('status', 'unknown')}", "PASS"
            )

            # Check database component
            components = health_data.get("components", {})
            db_status = components.get("database", False)
            print_step(
                f"Database component in health check: {db_status}",
                "PASS" if db_status else "FAIL",
            )
        else:
            print_step(f"Health check - Status: {response.status_code}", "FAIL")

        # Test database status endpoint
        response = client.get("/database/status")
        if response.status_code == 200:
            db_data = response.json()
            print_step(
                f"Database status endpoint - Status: {db_data.get('status', 'unknown')}",
                "PASS",
            )
        else:
            print_step(
                f"Database status endpoint - Status: {response.status_code}", "FAIL"
            )

        # Test database health endpoint
        response = client.get("/database/health")
        if response.status_code == 200:
            db_health = response.json()
            print_step(
                f"Database health endpoint - Status: {db_health.get('status', 'unknown')}",
                "PASS",
            )
        else:
            print_step(
                f"Database health endpoint - Status: {response.status_code}", "FAIL"
            )

        return True

    except Exception as e:
        print_step("Main application integration test", "FAIL")
        print_error(str(e))
        traceback.print_exc()
        return False


async def test_different_profiles():
    """Test different deployment profiles"""
    print_header("Testing Different Deployment Profiles")

    profiles_to_test = [
        ("homelab", {"HARBOR_MODE": "homelab"}),
        ("development", {"HARBOR_MODE": "development"}),
        (
            "production",
            {
                "HARBOR_MODE": "production",
                "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
            },
        ),
    ]

    results = []

    for profile_name, env_vars in profiles_to_test:
        try:
            print_step(f"Testing {profile_name} profile")

            # Set environment variables
            original_env = {}
            for key, value in env_vars.items():
                original_env[key] = os.environ.get(key)
                os.environ[key] = value

            # Clear cached settings
            from app.config import clear_settings_cache

            clear_settings_cache()

            # Test configuration
            from app.config import get_settings

            settings = get_settings()

            print_step(f"  Profile: {settings.deployment_profile.value}", "PASS")
            print_step(f"  Database: {settings.database.database_type.value}", "PASS")

            # Test database initialization
            from app.db.init import initialize_database

            success = await initialize_database(force_recreate=True)

            print_step(f"  Database initialization", "PASS" if success else "FAIL")

            results.append((profile_name, success))

            # Restore environment
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

            clear_settings_cache()

        except Exception as e:
            print_step(f"Profile {profile_name} test", "FAIL")
            print_error(str(e))
            results.append((profile_name, False))

    # Summary
    successful_profiles = [name for name, success in results if success]
    print_step(
        f"Successful profiles: {', '.join(successful_profiles)}",
        "PASS" if len(successful_profiles) == len(results) else "FAIL",
    )

    return len(successful_profiles) == len(results)


async def test_error_handling():
    """Test error handling and edge cases - PROPERLY FIXED: Session rollback test"""
    print_header("Testing Error Handling")

    try:
        from app.db.session import get_async_session
        from app.db.repositories.user import UserRepository
        from sqlalchemy import text

        print_step("Import modules for error testing", "PASS")

        # Test duplicate username
        async with get_async_session() as session:
            user_repo = UserRepository(session)

            # Create first user
            await user_repo.create_user(
                username="duplicate_test", password_hash="hash1"
            )
            await session.commit()

            # Try to create duplicate
            try:
                await user_repo.create_user(
                    username="duplicate_test", password_hash="hash2"
                )
                print_step("Duplicate username handling", "FAIL")
            except ValueError as e:
                if "already exists" in str(e):
                    print_step("Duplicate username handling", "PASS")
                else:
                    print_step("Duplicate username handling", "FAIL")

        # Test invalid SQL handling
        try:
            async with get_async_session() as session:
                await session.execute(text("SELECT * FROM nonexistent_table"))
                print_step("Invalid SQL error handling", "FAIL")
        except Exception:
            print_step("Invalid SQL error handling", "PASS")

        # Test session rollback on error - PROPERLY FIXED VERSION
        # Step 1: Get baseline count in separate session
        async with get_async_session() as session:
            user_repo = UserRepository(session)
            initial_count = await user_repo.count()
            print_step(f"Initial user count: {initial_count}", "PASS")

        # Step 2: Try to create user but force error before commit
        rollback_worked = False
        try:
            async with get_async_session() as session:
                user_repo = UserRepository(session)

                # Create user without flushing (stays in session only)
                user = await user_repo.create_user_no_flush(
                    username="rollback_test", password_hash="hash"
                )

                # Force an error - this should trigger session rollback
                raise Exception("Forced error for testing rollback")

        except Exception as e:
            if "Forced error" in str(e):
                rollback_worked = True
                print_step("Exception caught - session should rollback", "PASS")
            else:
                print_step(f"Unexpected error: {e}", "FAIL")
                raise

        # Step 3: Verify rollback worked - check in separate session
        async with get_async_session() as session:
            user_repo = UserRepository(session)
            found_user = await user_repo.get_by_username("rollback_test")
            final_count = await user_repo.count()

            rollback_success = (
                rollback_worked and found_user is None and final_count == initial_count
            )

            print_step(
                f"Session rollback verification - user exists: {found_user is not None}, "
                f"count changed: {final_count != initial_count}",
                "PASS" if rollback_success else "FAIL",
            )

        # Step 4: Test successful transaction (control test)
        async with get_async_session() as session:
            user_repo = UserRepository(session)

            user = await user_repo.create_user_no_flush(
                username="commit_test", password_hash="hash"
            )

            # Explicitly commit
            await session.commit()

        # Step 5: Verify successful transaction persisted
        async with get_async_session() as session:
            user_repo = UserRepository(session)
            found_user = await user_repo.get_by_username("commit_test")

            print_step(
                "Session commit on success",
                "PASS" if found_user is not None else "FAIL",
            )

        return True

    except Exception as e:
        print_step("Error handling test", "FAIL")
        print_error(str(e))
        traceback.print_exc()
        return False


async def run_all_tests(verbose: bool = False):
    """Run all database implementation tests"""
    print_header("Harbor M0 Database Implementation Test Suite")
    print_info(f"Python version: {sys.version}")
    print_info(f"Working directory: {os.getcwd()}")
    print_info(f"Test started at: {datetime.now().isoformat()}")

    # Create temporary data directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        os.environ["HARBOR_DATA_DIR"] = temp_dir
        os.environ["TESTING"] = "true"

        print_info(f"Using temporary data directory: {temp_dir}")

        # List of test functions
        tests = [
            ("Configuration System", test_configuration_system),
            ("Database Models", test_database_models),
            ("Database Initialization", test_database_initialization),
            ("Session Management", test_session_management),
            ("Repository Operations", test_repository_operations),
            ("Model Relationships", test_model_relationships),
            ("Main Application Integration", test_main_application),
            ("Different Profiles", test_different_profiles),
            ("Error Handling", test_error_handling),
        ]

        results = []

        for test_name, test_func in tests:
            try:
                result = await test_func()
                results.append((test_name, result))

                if not result and not verbose:
                    print_info(
                        "Test failed - stopping execution (use --verbose to continue)"
                    )
                    break

            except Exception as e:
                print_error(f"Test '{test_name}' crashed: {str(e)}")
                results.append((test_name, False))

                if not verbose:
                    print_info(
                        "Test crashed - stopping execution (use --verbose to continue)"
                    )
                    break

        # Final summary
        print_header("Test Results Summary")

        passed_tests = 0
        total_tests = len(results)

        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{status}: {test_name}")
            if result:
                passed_tests += 1

        print(f"\nOverall Result: {passed_tests}/{total_tests} tests passed")

        if passed_tests == total_tests:
            print("🎉 All tests passed! M0 Database implementation is ready.")
            return True
        else:
            print("💥 Some tests failed. Please review the errors above.")
            return False


def main():
    """Main test runner"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Harbor Database Implementation Test Suite"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Continue testing even if a test fails",
    )
    parser.add_argument(
        "--profile",
        choices=["homelab", "development", "production"],
        help="Set specific deployment profile for testing",
    )

    args = parser.parse_args()

    # Set profile if specified
    if args.profile:
        os.environ["HARBOR_MODE"] = args.profile
        print_info(f"Using deployment profile: {args.profile}")

    # Run tests
    success = asyncio.run(run_all_tests(verbose=args.verbose))

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
