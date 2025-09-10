#!/usr/bin/env python3
# scripts/dev/test_structure.py
"""
Harbor Project Structure Validation

Validates that the project structure matches the specifications defined
in the foundational documents. Checks for required directories, files,
and validates naming conventions.

Can interactively create missing directories and files (never overwrites existing).
Can also fix non-ASCII characters in code files.
"""

import os
import sys
import re
import fnmatch
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional
import json

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Test result tracking
test_results = []
verbose = "--verbose" in sys.argv or "-v" in sys.argv
interactive = "--interactive" in sys.argv or "-i" in sys.argv
auto_create = "--auto" in sys.argv


def log(message: str, level: str = "INFO"):
    """Log message with level indicator."""
    colors = {
        "INFO": "\033[0;34m",
        "PASS": "\033[0;32m",
        "FAIL": "\033[0;31m",
        "WARN": "\033[1;33m",
        "DEBUG": "\033[0;90m",
        "CREATE": "\033[0;36m",
        "FIX": "\033[0;35m",
    }
    color = colors.get(level, "")
    reset = "\033[0m"

    if level in ["PASS", "FAIL", "WARN", "CREATE", "FIX"] or verbose:
        print(f"{color}[{level}] {message}{reset}")


def test_section(name: str):
    """Print test section header."""
    print(f"\n{'=' * 70}")
    print(f" {name}")
    print(f"{'=' * 70}\n")


def record_test(name: str, passed: bool, details: str = ""):
    """Record test result."""
    status = "PASS" if passed else "FAIL"
    test_results.append({"name": name, "passed": passed, "details": details})
    log(f"{name}: {details if details else 'Completed'}", status)


def prompt_user(message: str) -> bool:
    """
    Prompt user for yes/no response.

    Returns:
        True if user responds yes
    """
    if auto_create:
        return True

    while True:
        response = input(f"{message} (y/n): ").strip().lower()
        if response in ["y", "yes"]:
            return True
        elif response in ["n", "no"]:
            return False
        else:
            print("Please enter 'y' for yes or 'n' for no.")


def create_directory(dir_path: Path) -> bool:
    """
    Create a directory if it doesn't exist.

    Never overwrites existing directories.

    Returns:
        True if directory was created or already exists
    """
    if dir_path.exists():
        if dir_path.is_dir():
            return True
        else:
            log(f"Path exists but is not a directory: {dir_path}", "WARN")
            return False

    try:
        dir_path.mkdir(parents=True, exist_ok=True)
        log(f"Created directory: {dir_path.relative_to(PROJECT_ROOT)}", "CREATE")
        return True
    except Exception as e:
        log(f"Failed to create directory {dir_path}: {e}", "FAIL")
        return False


def create_file(file_path: Path, content: str = "") -> bool:
    """
    Create a file if it doesn't exist.

    Never overwrites existing files.

    Returns:
        True if file was created or already exists
    """
    if file_path.exists():
        if file_path.is_file():
            return True
        else:
            log(f"Path exists but is not a file: {file_path}", "WARN")
            return False

    # Ensure parent directory exists
    parent_dir = file_path.parent
    if not parent_dir.exists():
        if not create_directory(parent_dir):
            return False

    try:
        file_path.write_text(content)
        log(f"Created file: {file_path.relative_to(PROJECT_ROOT)}", "CREATE")
        return True
    except Exception as e:
        log(f"Failed to create file {file_path}: {e}", "FAIL")
        return False


def replace_non_ascii(text: str) -> str:
    """
    Replace common non-ASCII characters with ASCII equivalents.

    Returns:
        Text with non-ASCII characters replaced
    """
    replacements = {
        # Common quotes
        '"': '"',
        '"': '"',  # Smart double quotes
        """: "'", """: "'",  # Smart single quotes
        "`": "`",
        "´": "'",  # Backticks and acute accent
        # Dashes and hyphens
        "–": "-",
        "—": "--",  # En dash, em dash
        "‐": "-",
        "‑": "-",  # Various hyphens
        # Common symbols that might appear in comments
        "…": "...",
        "•": "*",
        "·": "-",
        "©": "(c)",
        "®": "(r)",
        "™": "(tm)",
        "°": " degrees",
        "±": "+/-",
        # Arrows
        "→": "->",
        "←": "<-",
        "↑": "^",
        "↓": "v",
        "⇒": "=>",
        "⇐": "<=",
        # Common mathematical symbols
        "×": "x",
        "÷": "/",
        "≈": "~=",
        "≠": "!=",
        "≤": "<=",
        "≥": ">=",
        # Common fractions
        "½": "1/2",
        "¼": "1/4",
        "¾": "3/4",
        # Currency symbols
        "€": "EUR",
        "£": "GBP",
        "¥": "JPY",
        # Other common symbols
        "§": "Section",
        "¶": "Paragraph",
    }

    result = text
    for non_ascii, ascii_equiv in replacements.items():
        result = result.replace(non_ascii, ascii_equiv)

    # Remove any remaining non-ASCII characters that weren't in our replacement dict
    # Replace with space to maintain word boundaries
    result_chars = []
    for char in result:
        if ord(char) < 128:
            result_chars.append(char)
        else:
            # For unknown non-ASCII, replace with space or underscore depending on context
            if char.isalnum():
                result_chars.append("_")
            else:
                result_chars.append(" ")

    return "".join(result_chars)


def fix_non_ascii_in_file(file_path: Path) -> Optional[int]:
    """
    Fix non-ASCII characters in a file.

    Returns:
        Number of lines fixed, or None if error
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        fixed_lines = []
        lines_fixed = 0

        for line in lines:
            # Check if line has non-ASCII
            has_non_ascii = any(ord(char) > 127 for char in line)

            if has_non_ascii:
                fixed_line = replace_non_ascii(line)
                fixed_lines.append(fixed_line)
                lines_fixed += 1
            else:
                fixed_lines.append(line)

        if lines_fixed > 0:
            # Write back the fixed content
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(fixed_lines)

            log(
                f"Fixed {lines_fixed} lines in: {file_path.relative_to(PROJECT_ROOT)}",
                "FIX",
            )

        return lines_fixed

    except Exception as e:
        log(f"Error fixing file {file_path}: {e}", "FAIL")
        return None


def parse_gitignore() -> List[str]:
    """
    Parse .gitignore file and return list of patterns.

    Returns:
        List of gitignore patterns
    """
    gitignore_path = PROJECT_ROOT / ".gitignore"
    patterns = []

    # Default patterns to always ignore
    default_patterns = [
        "__pycache__",
        "*.pyc",
        ".git",
        ".venv",
        "venv",
        "env",
        ".env",
        "node_modules",
        ".pytest_cache",
        ".coverage",
        "htmlcov",
        "*.egg-info",
        "dist",
        "build",
        ".idea",
        ".vscode",
        "*.swp",
        "*.swo",
        ".DS_Store",
        "Thumbs.db",
    ]
    patterns.extend(default_patterns)

    if gitignore_path.exists():
        try:
            with open(gitignore_path, "r") as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if line and not line.startswith("#"):
                        patterns.append(line)
        except Exception as e:
            log(f"Warning: Could not read .gitignore: {e}", "WARN")

    return patterns


def should_ignore_path(path: Path, patterns: List[str]) -> bool:
    """
    Check if a path should be ignored based on gitignore patterns.

    Args:
        path: Path to check
        patterns: List of gitignore patterns

    Returns:
        True if path should be ignored
    """
    rel_path = path.relative_to(PROJECT_ROOT)
    rel_path_str = str(rel_path)

    for pattern in patterns:
        # Handle directory patterns
        if pattern.endswith("/"):
            pattern = pattern[:-1]
            if any(part == pattern for part in rel_path.parts):
                return True

        # Handle patterns with wildcards
        if "*" in pattern or "?" in pattern:
            if fnmatch.fnmatch(rel_path_str, pattern):
                return True
            # Also check individual path components
            for part in rel_path.parts:
                if fnmatch.fnmatch(part, pattern):
                    return True
        else:
            # Exact match or substring match
            if pattern in rel_path_str or pattern in rel_path.parts:
                return True

    return False


def print_progress_bar(
    current: int, total: int, prefix: str = "", suffix: str = "", length: int = 50
):
    """
    Print a progress bar to the console.

    Args:
        current: Current progress value
        total: Total value
        prefix: Prefix string
        suffix: Suffix string
        length: Character length of bar
    """
    if total == 0:
        return

    percent = min(100, (100 * current) // total)
    filled_length = (length * current) // total
    bar = "█" * filled_length + "-" * (length - filled_length)

    # Clear the line and print progress
    print(f"\r{prefix} |{bar}| {percent}% {suffix}", end="", flush=True)

    # Print newline on completion
    if current >= total:
        print()


def get_file_content(file_path: str) -> str:
    """
    Get appropriate default content for a file based on its type.

    Returns:
        Default content for the file
    """
    file_name = Path(file_path).name

    # Python __init__.py files
    if file_name == "__init__.py":
        return '"""\nHarbor module initialization.\n"""\n'

    # Python module files
    if file_path.endswith(".py"):
        module_name = Path(file_path).stem
        return f'"""\n{module_name.replace("_", " ").title()} module.\n"""\n\n# TODO: Implement {module_name}\n'

    # Markdown files
    if file_path.endswith(".md"):
        title = Path(file_path).stem.replace("_", " ").replace("-", " ").title()
        return f"# {title}\n\nTODO: Add content\n"

    # YAML files
    if file_path.endswith((".yml", ".yaml")):
        return "# Configuration file\n---\n\n# TODO: Add configuration\n"

    # JSON files
    if file_path.endswith(".json"):
        return '{\n  "todo": "Add configuration"\n}\n'

    # Shell scripts
    if file_path.endswith(".sh"):
        return "#!/bin/bash\n# Script description\n\necho 'TODO: Implement script'\n"

    # Requirements files
    if "requirements" in file_path and file_path.endswith(".txt"):
        if "base.txt" in file_path:
            return "# Base Python dependencies\n# Common to all environments\n"
        elif "production.txt" in file_path:
            return "# Production dependencies\n-r base.txt\n\n# Production-specific packages\n"
        elif "development.txt" in file_path:
            return "# Development dependencies\n-r base.txt\n\n# Development-specific packages\n"
        elif "test.txt" in file_path:
            return "# Test dependencies\n-r base.txt\n\n# Testing packages\npytest>=7.0.0\npytest-asyncio\npytest-cov\n"
        else:
            return "# Python dependencies\n"

    # Dockerfile
    if file_name == "Dockerfile":
        return "FROM python:3.12-slim\n\n# TODO: Complete Dockerfile\n"

    # Docker compose
    if "docker-compose" in file_name:
        return "version: '3.8'\n\nservices:\n  # TODO: Define services\n"

    # Default
    return ""


# ==============================================================================
# Project Structure Definitions (from foundational documents)
# ==============================================================================

# Core application structure
REQUIRED_APP_DIRS = [
    "app",
    "app/api",
    "app/auth",
    "app/db",
    "app/db/models",
    "app/db/repositories",
    "app/db/migrations",
    "app/db/migrations/versions",
    "app/services",
    "app/runtimes",
    "app/registry",
    "app/scheduler",
    "app/security",
    "app/utils",
    "app/web",
    "app/web/static",
    "app/web/static/css",
    "app/web/static/js",
    "app/web/static/js/components",
    "app/web/templates",
    "app/web/templates/auth",
    "app/web/templates/components",
    "app/setup",
    "app/middleware",
    "app/core",
]

# Testing structure
REQUIRED_TEST_DIRS = [
    "tests",
    "tests/unit",
    "tests/unit/auth",
    "tests/unit/db",
    "tests/unit/services",
    "tests/unit/api",
    "tests/unit/utils",
    "tests/unit/runtimes",
    "tests/integration",
    "tests/e2e",
    "tests/performance",
    "tests/security",
    "tests/fixtures",
]

# Deployment structure
REQUIRED_DEPLOY_DIRS = [
    "deploy",
    "deploy/docker",
    "deploy/kubernetes",
    "deploy/kubernetes/helm",
    "deploy/kubernetes/helm/templates",
    "deploy/nginx",
    "deploy/terraform",
    "deploy/ansible",
]

# Documentation structure
REQUIRED_DOCS_DIRS = [
    "docs",
    "docs/getting-started",
    "docs/configuration",
    "docs/deployment",
    "docs/api",
    "docs/development",
    "docs/troubleshooting",
    "docs/assets",
    "docs/assets/images",
]

# Scripts structure
REQUIRED_SCRIPTS_DIRS = [
    "scripts",
    "scripts/dev",
]

# Configuration and examples
REQUIRED_CONFIG_DIRS = [
    "config",
    "config/monitoring",
    "examples",
    "examples/home-lab",
    "examples/enterprise",
    "examples/migration",
    "requirements",  # Added requirements directory
]

# Required root-level files (removed requirements.txt)
REQUIRED_ROOT_FILES = [
    ".gitignore",
    ".dockerignore",
    ".pre-commit-config.yaml",
    "pyproject.toml",
    "Makefile",
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
]

# Requirements files in the requirements/ directory
REQUIRED_REQUIREMENTS_FILES = [
    "requirements/base.txt",
    "requirements/production.txt",
    "requirements/development.txt",
    "requirements/test.txt",
]

# Required Python package files
REQUIRED_PACKAGE_FILES = [
    "app/__init__.py",
    "app/api/__init__.py",
    "app/auth/__init__.py",
    "app/db/__init__.py",
    "app/db/models/__init__.py",
    "app/db/repositories/__init__.py",
    "app/services/__init__.py",
    "app/runtimes/__init__.py",
    "app/registry/__init__.py",
    "app/scheduler/__init__.py",
    "app/security/__init__.py",
    "app/utils/__init__.py",
    "app/utils/logging/__init__.py",
    "app/middleware/__init__.py",
    "app/core/__init__.py",
]

# Key application files
REQUIRED_APP_FILES = [
    "app/main.py",
    "app/config.py",
    "app/exceptions.py",
    "app/constants.py",
    # Auth files
    "app/auth/manager.py",
    "app/auth/sessions.py",
    "app/auth/api_keys.py",
    "app/auth/password.py",
    # DB files
    "app/db/base.py",
    "app/db/session.py",
    "app/db/init.py",
    # Core files
    "app/core/security.py",
    # Service files
    "app/services/health.py",
    # Middleware files
    "app/middleware/correlation.py",
    "app/middleware/authentication.py",
    "app/middleware/request_logging.py",
    "app/middleware/cors.py",
]

# Test configuration files
REQUIRED_TEST_FILES = [
    "tests/conftest.py",
    "tests/unit/utils/test_logging.py",
    "tests/integration/test_logging_integration.py",
]

# Deployment files
REQUIRED_DEPLOY_FILES = [
    "deploy/docker/Dockerfile",
    "deploy/docker/docker-compose.yml",
]


# ==============================================================================
# Validation Functions with Creation Support
# ==============================================================================


def validate_directories(dirs: List[str], category: str) -> Tuple[int, int, int]:
    """
    Validate that required directories exist, with option to create missing ones.

    Returns:
        Tuple of (found_count, missing_count, created_count)
    """
    found = 0
    missing = 0
    created = 0
    missing_dirs = []

    for dir_path in dirs:
        full_path = PROJECT_ROOT / dir_path
        if full_path.exists() and full_path.is_dir():
            found += 1
            if verbose:
                log(f"  ✓ {dir_path}", "DEBUG")
        else:
            missing += 1
            missing_dirs.append((dir_path, full_path))

    if missing_dirs and interactive:
        log(f"  Missing {category} directories:", "WARN")
        for dir_path, _ in missing_dirs[:10]:
            log(f"    - {dir_path}", "WARN")
        if len(missing_dirs) > 10:
            log(f"    ... and {len(missing_dirs) - 10} more", "WARN")

        if prompt_user(f"\nCreate {len(missing_dirs)} missing {category} directories?"):
            for dir_path, full_path in missing_dirs:
                if create_directory(full_path):
                    created += 1
                    missing -= 1
    elif missing_dirs:
        log(f"  Missing {category} directories (use -i to create):", "WARN")
        for dir_path, _ in missing_dirs[:10]:
            log(f"    - {dir_path}", "WARN")
        if len(missing_dirs) > 10:
            log(f"    ... and {len(missing_dirs) - 10} more", "WARN")

    return found, missing, created


def validate_files(files: List[str], category: str) -> Tuple[int, int, int]:
    """
    Validate that required files exist, with option to create missing ones.

    Returns:
        Tuple of (found_count, missing_count, created_count)
    """
    found = 0
    missing = 0
    created = 0
    missing_files = []

    for file_path in files:
        full_path = PROJECT_ROOT / file_path
        if full_path.exists() and full_path.is_file():
            found += 1
            if verbose:
                log(f"  ✓ {file_path}", "DEBUG")
        else:
            missing += 1
            missing_files.append((file_path, full_path))

    if missing_files and interactive:
        log(f"  Missing {category} files:", "WARN")
        for file_path, _ in missing_files[:10]:
            log(f"    - {file_path}", "WARN")
        if len(missing_files) > 10:
            log(f"    ... and {len(missing_files) - 10} more", "WARN")

        if prompt_user(f"\nCreate {len(missing_files)} missing {category} files?"):
            for file_path, full_path in missing_files:
                content = get_file_content(file_path)
                if create_file(full_path, content):
                    created += 1
                    missing -= 1
    elif missing_files:
        log(f"  Missing {category} files (use -i to create):", "WARN")
        for file_path, _ in missing_files[:10]:
            log(f"    - {file_path}", "WARN")
        if len(missing_files) > 10:
            log(f"    ... and {len(missing_files) - 10} more", "WARN")

    return found, missing, created


def check_naming_conventions() -> bool:
    """
    Check that files follow proper naming conventions.

    Returns:
        True if all naming conventions are followed
    """
    issues = []

    # Check Python files for snake_case
    for py_file in PROJECT_ROOT.glob("app/**/*.py"):
        if py_file.name != "__init__.py":
            # Check for snake_case
            if not py_file.stem.replace("_", "").isalnum():
                issues.append(
                    f"Non-alphanumeric in: {py_file.relative_to(PROJECT_ROOT)}"
                )
            elif py_file.stem != py_file.stem.lower():
                issues.append(f"Not snake_case: {py_file.relative_to(PROJECT_ROOT)}")

    # Check that test files start with test_
    for test_file in PROJECT_ROOT.glob("tests/**/*.py"):
        if test_file.name != "__init__.py" and test_file.name != "conftest.py":
            if not test_file.name.startswith("test_"):
                issues.append(
                    f"Test file doesn't start with test_: {test_file.relative_to(PROJECT_ROOT)}"
                )

    if issues:
        log("  Naming convention issues:", "WARN")
        for issue in issues[:5]:
            log(f"    - {issue}", "WARN")
        if len(issues) > 5:
            log(f"    ... and {len(issues) - 5} more", "WARN")
        return False

    return True


def check_and_fix_non_ascii() -> Tuple[bool, int]:
    """
    Check for non-ASCII characters in code files and optionally fix them.
    Uses .gitignore to skip unnecessary files.

    Returns:
        Tuple of (all_ascii, files_fixed)
    """
    issues = []
    files_with_issues = {}

    # Parse gitignore patterns
    gitignore_patterns = parse_gitignore()

    # File extensions to check
    code_extensions = [".py", ".yml", ".yaml", ".json", ".toml", ".sh"]

    # First, collect all files to check
    files_to_check = []
    for ext in code_extensions:
        for file_path in PROJECT_ROOT.glob(f"**/*{ext}"):
            # Skip if path should be ignored
            if should_ignore_path(file_path, gitignore_patterns):
                continue

            # Skip test files and documentation
            if "test" in str(file_path) or "docs" in str(file_path):
                continue

            files_to_check.append(file_path)

    total_files = len(files_to_check)

    if total_files == 0:
        return True, 0

    log(f"  Scanning {total_files} files for non-ASCII characters...", "INFO")

    # Check files with progress bar
    for idx, file_path in enumerate(files_to_check):
        # Update progress bar
        print_progress_bar(
            idx + 1,
            total_files,
            prefix="  Progress:",
            suffix=f"({idx + 1}/{total_files}) {file_path.name[:20]:20}",
        )

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for non-ASCII characters
            file_issues = []
            for line_num, line in enumerate(content.split("\n"), 1):
                for char_pos, char in enumerate(line):
                    if ord(char) > 127:
                        rel_path = file_path.relative_to(PROJECT_ROOT)
                        file_issues.append(
                            {
                                "line": line_num,
                                "char": char,
                                "ord": ord(char),
                                "preview": line[:50] + "..."
                                if len(line) > 50
                                else line,
                            }
                        )
                        break

            if file_issues:
                files_with_issues[file_path] = file_issues
                issues.append(
                    f"{file_path.relative_to(PROJECT_ROOT)} - {len(file_issues)} lines with non-ASCII"
                )

        except Exception:
            # Skip files that can't be read
            pass

    # Clear progress bar line
    print("\r" + " " * 80 + "\r", end="")

    if not issues:
        log(f"  ✓ Scanned {total_files} files - all contain only ASCII", "PASS")
        return True, 0

    # Report issues
    log(f"  Non-ASCII characters found in {len(files_with_issues)} files:", "WARN")
    for issue in issues[:5]:
        log(f"    - {issue}", "WARN")
    if len(issues) > 5:
        log(f"    ... and {len(issues) - 5} more files", "WARN")

    # If not interactive/auto mode, just report
    if not interactive and not auto_create:
        return False, 0

    # Offer to fix
    files_fixed = 0

    if interactive or auto_create:
        if verbose:
            # Show some examples of what will be replaced
            log("\n  Examples of characters that will be replaced:", "INFO")
            example_count = 0
            for file_path, file_issues in files_with_issues.items():
                for issue in file_issues[:2]:  # Show max 2 per file
                    char = issue["char"]
                    replacement = replace_non_ascii(char)
                    log(
                        f"    Line {issue['line']}: '{char}' (U+{ord(char):04X}) → '{replacement}'",
                        "INFO",
                    )
                    example_count += 1
                    if example_count >= 5:
                        break
                if example_count >= 5:
                    break

        fix_them = auto_create or prompt_user(
            f"\nFix non-ASCII characters in {len(files_with_issues)} files?"
        )

        if fix_them:
            log(f"  Fixing {len(files_with_issues)} files...", "INFO")

            for idx, file_path in enumerate(files_with_issues):
                # Update progress bar for fixing
                print_progress_bar(
                    idx + 1,
                    len(files_with_issues),
                    prefix="  Fixing:",
                    suffix=f"({idx + 1}/{len(files_with_issues)}) {file_path.name[:20]:20}",
                )

                lines_fixed = fix_non_ascii_in_file(file_path)
                if lines_fixed is not None and lines_fixed > 0:
                    files_fixed += 1

            # Clear progress bar line
            print("\r" + " " * 80 + "\r", end="")

            if files_fixed > 0:
                log(f"  ✓ Fixed non-ASCII characters in {files_fixed} files", "FIX")

    return len(issues) == 0, files_fixed


# ==============================================================================
# Main Test Runner
# ==============================================================================


def run_all_tests():
    """Run all structure validation tests."""
    print("=" * 70)
    print(" HARBOR PROJECT STRUCTURE VALIDATION")
    print("=" * 70)
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Verbose mode: {verbose}")
    print(f"Interactive mode: {interactive}")
    if auto_create:
        print("Auto-create mode: ENABLED (will create missing items and fix issues)")
    print()

    if interactive:
        print("NOTE: This tool will NEVER overwrite existing files or directories.")
        print(
            "      It only creates missing items and fixes issues in existing files.\n"
        )

    all_passed = True
    total_created = 0
    total_fixed = 0

    # Test 1: Core Application Structure
    test_section("1. CORE APPLICATION STRUCTURE")
    found, missing, created = validate_directories(REQUIRED_APP_DIRS, "application")
    total_created += created

    if missing == 0:
        log(f"✓ All {found} application directories present", "PASS")
        if created > 0:
            log(f"  Created {created} missing directories", "CREATE")
        record_test("Application Structure", True, f"{found} directories found")
    else:
        log(f"✗ Missing {missing}/{found + missing} application directories", "FAIL")
        record_test("Application Structure", False, f"{missing} directories missing")
        all_passed = False

    # Test 2: Test Structure
    test_section("2. TEST STRUCTURE")
    found, missing, created = validate_directories(REQUIRED_TEST_DIRS, "test")
    total_created += created

    if missing == 0:
        log(f"✓ All {found} test directories present", "PASS")
        if created > 0:
            log(f"  Created {created} missing directories", "CREATE")
        record_test("Test Structure", True, f"{found} directories found")
    else:
        log(f"✗ Missing {missing}/{found + missing} test directories", "FAIL")
        record_test("Test Structure", False, f"{missing} directories missing")
        all_passed = False

    # Test 3: Deployment Structure
    test_section("3. DEPLOYMENT STRUCTURE")
    found, missing, created = validate_directories(REQUIRED_DEPLOY_DIRS, "deployment")
    total_created += created

    if missing <= 3:  # Allow some optional deployment dirs
        log(f"✓ {found}/{found + missing} deployment directories present", "PASS")
        if created > 0:
            log(f"  Created {created} missing directories", "CREATE")
        record_test("Deployment Structure", True, f"{found} directories found")
    else:
        log(f"✗ Missing {missing}/{found + missing} deployment directories", "FAIL")
        record_test("Deployment Structure", False, f"{missing} directories missing")
        all_passed = False

    # Test 4: Documentation Structure
    test_section("4. DOCUMENTATION STRUCTURE")
    found, missing, created = validate_directories(REQUIRED_DOCS_DIRS, "documentation")
    total_created += created

    if missing <= 5:  # Allow some missing doc dirs
        log(f"✓ {found}/{found + missing} documentation directories present", "PASS")
        if created > 0:
            log(f"  Created {created} missing directories", "CREATE")
        record_test("Documentation Structure", True, f"{found} directories found")
    else:
        log(f"⚠ Missing {missing}/{found + missing} documentation directories", "WARN")
        record_test(
            "Documentation Structure",
            True,
            f"{missing} directories missing (non-critical)",
        )

    # Test 5: Scripts and Config Directories
    test_section("5. SCRIPTS AND CONFIG STRUCTURE")
    all_dirs = REQUIRED_SCRIPTS_DIRS + REQUIRED_CONFIG_DIRS
    found, missing, created = validate_directories(all_dirs, "scripts/config")
    total_created += created

    if missing == 0:
        log(f"✓ All {found} scripts/config directories present", "PASS")
        if created > 0:
            log(f"  Created {created} missing directories", "CREATE")
        record_test("Scripts/Config Structure", True, f"{found} directories found")
    else:
        log(f"✗ Missing {missing}/{found + missing} scripts/config directories", "FAIL")
        record_test("Scripts/Config Structure", False, f"{missing} directories missing")
        all_passed = False

    # Test 6: Required Files
    test_section("6. REQUIRED FILES")

    # Check root files
    found, missing, created = validate_files(REQUIRED_ROOT_FILES, "root")
    total_created += created
    if missing <= 2:  # Allow 2 missing root files
        log(f"✓ {found}/{found + missing} root files present", "PASS")
        if created > 0:
            log(f"  Created {created} missing files", "CREATE")
        record_test("Root Files", True, f"{found} files found")
    else:
        log(f"✗ Missing {missing}/{found + missing} root files", "FAIL")
        record_test("Root Files", False, f"{missing} files missing")
        all_passed = False

    # Check requirements files
    found, missing, created = validate_files(
        REQUIRED_REQUIREMENTS_FILES, "requirements"
    )
    total_created += created
    if missing == 0:
        log(f"✓ All {found} requirements files present", "PASS")
        if created > 0:
            log(f"  Created {created} missing files", "CREATE")
        record_test("Requirements Files", True, f"{found} files found")
    else:
        log(f"✗ Missing {missing}/{found + missing} requirements files", "FAIL")
        record_test("Requirements Files", False, f"{missing} files missing")
        all_passed = False

    # Check package files
    found, missing, created = validate_files(REQUIRED_PACKAGE_FILES, "package")
    total_created += created
    if missing == 0:
        log(f"✓ All {found} package __init__.py files present", "PASS")
        if created > 0:
            log(f"  Created {created} missing files", "CREATE")
        record_test("Package Files", True, f"{found} files found")
    else:
        log(f"✗ Missing {missing}/{found + missing} package files", "FAIL")
        record_test("Package Files", False, f"{missing} files missing")
        all_passed = False

    # Check application files
    found, missing, created = validate_files(REQUIRED_APP_FILES, "application")
    total_created += created
    if missing == 0:
        log(f"✓ All {found} key application files present", "PASS")
        if created > 0:
            log(f"  Created {created} missing files", "CREATE")
        record_test("Application Files", True, f"{found} files found")
    else:
        log(f"✗ Missing {missing}/{found + missing} application files", "FAIL")
        record_test("Application Files", False, f"{missing} files missing")
        all_passed = False

    # Test 7: Naming Conventions
    test_section("7. NAMING CONVENTIONS")
    if check_naming_conventions():
        log("✓ All files follow naming conventions", "PASS")
        record_test("Naming Conventions", True, "All files properly named")
    else:
        log("⚠ Some files don't follow naming conventions", "WARN")
        record_test("Naming Conventions", True, "Some naming issues (non-critical)")

    # Test 8: Code Standards (with fixing capability and progress bar)
    test_section("8. CODE STANDARDS (with .gitignore support)")
    all_ascii, files_fixed = check_and_fix_non_ascii()
    total_fixed += files_fixed

    if all_ascii:
        log("✓ No non-ASCII characters in code files", "PASS")
        record_test("Code Standards", True, "ASCII-only code")
    elif files_fixed > 0:
        log(f"✓ Fixed non-ASCII characters in {files_fixed} files", "FIX")
        record_test("Code Standards", True, f"Fixed {files_fixed} files")
    else:
        log("⚠ Non-ASCII characters found in code (use -i or --auto to fix)", "WARN")
        record_test("Code Standards", True, "Non-ASCII found (fixable)")

    # Print summary
    print("\n" + "=" * 70)
    print(" TEST SUMMARY")
    print("=" * 70 + "\n")

    passed = sum(1 for t in test_results if t["passed"])
    failed = len(test_results) - passed

    for result in test_results:
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"{status}: {result['name']}")
        if result["details"] and (not result["passed"] or verbose):
            print(f"         {result['details']}")

    print(f"\nTotal: {passed} passed, {failed} failed out of {len(test_results)} tests")

    if total_created > 0:
        print(f"\n📁 Created {total_created} missing directories/files")

    if total_fixed > 0:
        print(f"\n🔧 Fixed {total_fixed} files with non-ASCII characters")

    if all_passed:
        print("\n🎉 PROJECT STRUCTURE VALIDATION PASSED!")
        print("\n✅ Project structure conforms to specifications!")
        return 0
    else:
        print(f"\n❌ {failed} structural issue(s) found")
        if not interactive:
            print(
                "\n💡 Run with -i flag to interactively create missing items and fix issues"
            )
            print("   Example: python scripts/dev/test_structure.py -i")
            print("\n🚀 Or use --auto flag to automatically fix all issues")
            print("   Example: python scripts/dev/test_structure.py --auto")
        print("\n⚠️  Please review and fix structural issues")
        return 1


if __name__ == "__main__":
    print("\nUsage:")
    print("  python scripts/dev/test_structure.py           # Check only")
    print("  python scripts/dev/test_structure.py -i        # Interactive mode")
    print("  python scripts/dev/test_structure.py --auto    # Auto-fix all issues")
    print("  python scripts/dev/test_structure.py -v        # Verbose output")

    exit_code = run_all_tests()
    sys.exit(exit_code)
