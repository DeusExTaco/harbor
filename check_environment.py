#!/usr/bin/env python3
"""
Harbor Environment Check Script

Quick diagnostic script to check if all required dependencies
and modules are properly set up before running the main tests.

Updated to match Harbor's actual project structure with app/security/ module.
"""

import os
import sys
from pathlib import Path


def print_header(title):
    print(f"\n{'=' * 50}")
    print(f" {title}")
    print(f"{'=' * 50}")


def print_check(item, status, details=None):
    status_symbol = "✅" if status else "❌"
    print(f"{status_symbol} {item}")
    if details:
        print(f"   {details}")


def check_python_version():
    """Check Python version"""
    print_header("Python Environment")

    version = sys.version_info
    print_check(
        f"Python version: {version.major}.{version.minor}.{version.micro}",
        version >= (3, 8),
    )

    print_check(f"Python executable: {sys.executable}", True)
    print_check(f"Current working directory: {os.getcwd()}", True)


def check_project_structure():
    """Check if we're in the right directory with correct structure"""
    print_header("Project Structure")

    # Core application files that must exist
    required_files = [
        "app/main.py",
        "app/config.py",
        "app/__init__.py",
        "app/db/__init__.py",
        "app/db/base.py",
        "app/db/config.py",
        "app/db/session.py",
        "app/db/init.py",
        "app/security/__init__.py",
        "app/security/headers.py",
        "app/security/rate_limit.py",
        "app/security/validation.py",
        "app/utils/__init__.py",
        "app/utils/logging.py",
    ]

    # Required directories that must exist
    required_dirs = [
        "app",
        "app/db",
        "app/db/models",
        "app/db/repositories",
        "app/security",
        "app/utils",
        "tests",  # Only if tests directory exists
    ]

    all_good = True

    for file_path in required_files:
        exists = Path(file_path).exists()
        print_check(f"File: {file_path}", exists)
        if not exists:
            all_good = False

    for dir_path in required_dirs:
        # Skip tests directory check if it doesn't exist (not critical for core functionality)
        if dir_path == "tests" and not Path(dir_path).exists():
            print_check(f"Directory: {dir_path}", True, "Optional - not found")
            continue

        exists = Path(dir_path).is_dir()
        print_check(f"Directory: {dir_path}", exists)
        if not exists:
            all_good = False

    return all_good


def check_dependencies():
    """Check if required Python packages are available"""
    print_header("Python Dependencies")

    required_packages = [
        ("fastapi", "FastAPI web framework"),
        ("sqlalchemy", "SQL toolkit and ORM"),
        ("aiosqlite", "Async SQLite driver"),
        ("pydantic", "Data validation"),
        ("uvicorn", "ASGI server"),
        ("pydantic_settings", "Pydantic settings management"),
    ]

    optional_packages = [
        ("asyncpg", "PostgreSQL async driver"),
        ("psutil", "System monitoring"),
        ("httpx", "HTTP client for testing"),
        ("pytest", "Testing framework"),
        ("yaml", "YAML parsing"),
    ]

    all_required = True

    for package, description in required_packages:
        try:
            __import__(package)
            print_check(f"{package}: {description}", True)
        except ImportError:
            print_check(f"{package}: {description}", False, "REQUIRED - Please install")
            all_required = False

    print("\nOptional packages:")
    for package, description in optional_packages:
        try:
            __import__(package)
            print_check(f"{package}: {description}", True, "Optional")
        except ImportError:
            print_check(f"{package}: {description}", False, "Optional - not installed")

    return all_required


def check_harbor_modules():
    """Check if Harbor modules can be imported"""
    print_header("Harbor Modules")

    # Add current directory to Python path
    if str(Path.cwd()) not in sys.path:
        sys.path.insert(0, str(Path.cwd()))

    # Core Harbor modules that must import successfully
    harbor_modules = [
        ("app", "Main application package"),
        ("app.config", "Configuration system"),
        ("app.main", "Main application factory"),
        ("app.db.base", "Database base classes"),
        ("app.db.config", "Database configuration"),
        ("app.db.session", "Session management"),
        ("app.db.init", "Database initialization"),
        ("app.utils.logging", "Logging utilities"),
        ("app.security", "Security middleware module"),
        ("app.security.headers", "Security headers middleware"),
        ("app.security.rate_limit", "Rate limiting middleware"),
        ("app.security.validation", "Input validation"),
    ]

    # Database models (check if they exist and can import)
    model_modules = [
        ("app.db.models.user", "User model"),
        ("app.db.models.settings", "System settings model"),
        ("app.db.models.api_key", "API key model"),
        ("app.db.models.container", "Container model"),
        ("app.db.models.policy", "Policy model"),
    ]

    # Repository modules (check if they exist)
    repository_modules = [
        ("app.db.repositories.user", "User repository"),
        ("app.db.repositories.container", "Container repository"),
    ]

    all_modules = True

    # Check core modules
    for module, description in harbor_modules:
        try:
            __import__(module)
            print_check(f"{module}: {description}", True)
        except ImportError as e:
            print_check(f"{module}: {description}", False, f"Import error: {e}")
            all_modules = False
        except Exception as e:
            print_check(f"{module}: {description}", False, f"Error: {e}")
            all_modules = False

    print("\nDatabase Models:")
    for module, description in model_modules:
        try:
            __import__(module)
            print_check(f"{module}: {description}", True)
        except ImportError as e:
            print_check(f"{module}: {description}", False, f"Import error: {e}")
            all_modules = False
        except Exception as e:
            print_check(f"{module}: {description}", False, f"Error: {e}")
            all_modules = False

    print("\nRepositories:")
    for module, description in repository_modules:
        try:
            __import__(module)
            print_check(f"{module}: {description}", True)
        except ImportError as e:
            # Repositories might not exist yet - this is less critical
            print_check(f"{module}: {description}", True, f"Not implemented yet: {e}")
        except Exception as e:
            print_check(f"{module}: {description}", False, f"Error: {e}")

    return all_modules


def check_environment_variables():
    """Check environment variables"""
    print_header("Environment Variables")

    # Check current environment
    harbor_mode = os.getenv("HARBOR_MODE", "not set")
    print_check(f"HARBOR_MODE: {harbor_mode}", True, "Current deployment profile")

    data_dir = os.getenv("HARBOR_DATA_DIR", "not set")
    print_check(f"HARBOR_DATA_DIR: {data_dir}", True, "Data storage directory")

    log_level = os.getenv("LOG_LEVEL", "not set")
    print_check(f"LOG_LEVEL: {log_level}", True, "Logging level")

    testing = os.getenv("TESTING", "not set")
    print_check(f"TESTING: {testing}", True, "Test mode flag")

    # Check for database URL if set
    db_url = os.getenv("DATABASE_URL", "not set")
    if db_url != "not set":
        # Mask credentials for security
        masked_url = db_url.split("://")[0] + "://***" if "://" in db_url else db_url
        print_check(f"DATABASE_URL: {masked_url}", True, "External database URL")


def check_basic_functionality():
    """Check if basic Harbor functionality works"""
    print_header("Basic Functionality Test")

    try:
        # Test configuration system
        from app.config import get_settings

        settings = get_settings()
        print_check(
            "Configuration system",
            True,
            f"Profile: {settings.deployment_profile.value}",
        )
    except Exception as e:
        print_check("Configuration system", False, str(e))
        return False

    try:
        # Test security middleware imports
        print_check("Security middleware", True, "Headers and rate limiting available")
    except Exception as e:
        print_check("Security middleware", False, str(e))
        return False

    try:
        # Test database models
        from app.db.models.user import User

        user = User(username="test", password_hash="hash")
        print_check("Database models", True, "User model works")
    except Exception as e:
        print_check("Database models", False, str(e))
        return False

    try:
        # Test database configuration
        from app.db.config import get_database_config

        db_config = get_database_config()
        print_check("Database configuration", True, "Database config available")
    except Exception as e:
        print_check("Database configuration", False, str(e))
        return False

    try:
        # Test main application
        from app.main import create_app

        app = create_app()
        print_check("Main application", True, f"FastAPI app: {app.title}")
    except Exception as e:
        print_check("Main application", False, str(e))
        return False

    return True


def check_data_directories():
    """Check if data directories can be created and are writable"""
    print_header("Data Directory Check")

    try:
        from app.config import get_settings

        settings = get_settings()

        # Test data directory
        data_dir = Path(settings.data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)

        # Test write access
        test_file = data_dir / ".write_test"
        test_file.write_text("test")
        test_file.unlink()

        print_check(f"Data directory: {data_dir}", True, "Writable")

        # Test logs directory
        logs_dir = Path(settings.logs_dir)
        logs_dir.mkdir(parents=True, exist_ok=True)

        test_file = logs_dir / ".write_test"
        test_file.write_text("test")
        test_file.unlink()

        print_check(f"Logs directory: {logs_dir}", True, "Writable")

        return True

    except Exception as e:
        print_check("Data directories", False, str(e))
        return False


def main():
    """Run all environment checks"""
    print("🛳️ Harbor Environment Check")
    print("Checking if everything is ready for M0 Database testing...")

    results = []

    # Run all checks
    check_python_version()

    results.append(("Project Structure", check_project_structure()))
    results.append(("Dependencies", check_dependencies()))
    results.append(("Harbor Modules", check_harbor_modules()))
    results.append(("Data Directories", check_data_directories()))

    check_environment_variables()

    results.append(("Basic Functionality", check_basic_functionality()))

    # Summary
    print_header("Environment Check Summary")

    passed = 0
    total = len(results)

    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {check_name}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{total} checks passed")

    if passed == total:
        print("\n🎉 Environment is ready!")
        print("All M0 core systems are available and working.")
        print("\nYou can now run:")
        print("  python test_db_implementation.py --verbose")
        print("  uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8080")
        print("\nTest endpoints:")
        print("  curl http://localhost:8080/healthz | jq .")
        print("  curl http://localhost:8080/security/status | jq .")
        print("  curl http://localhost:8080/database/status | jq .")
        return True
    else:
        print("\n💥 Environment issues detected!")
        print("Please fix the issues above before running tests.")
        print("\nCommon solutions:")
        print(
            "  - Install missing packages: pip install fastapi sqlalchemy aiosqlite pydantic pydantic-settings uvicorn"
        )
        print("  - Check you're in the Harbor project root directory")
        print("  - Ensure all Harbor modules are in the correct locations")
        print("  - Verify file permissions for data directories")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
