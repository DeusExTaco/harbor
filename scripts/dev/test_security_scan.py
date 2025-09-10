#!/usr/bin/env python3
# scripts/dev/test_security_scan.py
"""
Harbor Security Vulnerability Scan

Checks dependencies for known security vulnerabilities and hardcoded secrets.
Enhanced version with detailed output for debugging.
"""

import subprocess
import sys
import json
import re
from pathlib import Path


def check_pip_audit():
    """Check if pip-audit is installed."""
    try:
        subprocess.run(["pip-audit", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  pip-audit not installed")
        print("   Installing pip-audit...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pip-audit"])
        return True


def run_security_scan():
    """Run security vulnerability scan with detailed output."""
    print("\n🔒 Security Vulnerability Scan")
    print("-" * 50)

    if not check_pip_audit():
        return False

    try:
        # Run pip-audit and capture output
        result = subprocess.run(
            ["pip-audit", "--format", "json"], capture_output=True, text=True
        )

        if result.returncode == 0:
            print("✅ No known vulnerabilities found")
            return True
        else:
            # Try to parse JSON output
            try:
                vulnerabilities = json.loads(result.stdout)

                # Check if it's a list or dict structure
                if isinstance(vulnerabilities, list) and vulnerabilities:
                    print("⚠️  Vulnerabilities found:")
                    for vuln in vulnerabilities:
                        if isinstance(vuln, dict):
                            name = vuln.get("name", "Unknown")
                            version = vuln.get("version", "Unknown")
                            vulnerability = vuln.get("vulnerability", "Unknown")
                            print(f"   - {name} {version}: {vulnerability}")
                        else:
                            print(f"   - {vuln}")
                    return False
                elif isinstance(vulnerabilities, dict):
                    # Check for the dependencies key
                    deps = vulnerabilities.get("dependencies", [])
                    if deps:
                        print("⚠️  Vulnerabilities found:")
                        for dep in deps:
                            vulns = dep.get("vulns", [])
                            if vulns:
                                name = dep.get("name", "Unknown")
                                version = dep.get("version", "Unknown")
                                print(f"   - {name} {version}:")
                                for v in vulns:
                                    print(
                                        f"     • {v.get('description', v.get('id', 'Unknown'))}"
                                    )
                        return False
                    else:
                        print("✅ No known vulnerabilities found")
                        return True
                else:
                    # Empty or no vulnerabilities
                    print("✅ No known vulnerabilities found")
                    return True

            except json.JSONDecodeError:
                # If JSON parsing fails, show raw output
                print("⚠️  Could not parse pip-audit output. Raw output:")
                print(result.stdout)
                if result.stderr:
                    print("Errors:")
                    print(result.stderr)
                return False

    except Exception as e:
        print(f"❌ Security scan failed: {e}")
        return False


def check_hardcoded_secrets():
    """Check for potential hardcoded secrets with detailed line information."""
    print("\n🔑 Checking for Hardcoded Secrets")
    print("-" * 50)

    # Patterns that might indicate hardcoded secrets
    suspicious_patterns = [
        (r'password\s*=\s*["\'][^"\']+["\']', "password assignment"),
        (r'secret\s*=\s*["\'][^"\']+["\']', "secret assignment"),
        (r'token\s*=\s*["\'][^"\']+["\']', "token assignment"),
        (r'api_key\s*=\s*["\'][^"\']+["\']', "api_key assignment"),
        (r'key\s*=\s*["\'][^"\']+["\']', "key assignment"),
    ]

    # Known safe patterns to exclude
    safe_patterns = [
        r"os\.environ",
        r"os\.getenv",
        r"getenv",
        r"\.env",
        r"example",
        r"test",
        r"placeholder",
        r"your[-_]",
        r"xxx",
        r"\*\*\*",
        r"<.*>",
        r"TODO",
        r"FIXME",
        r"default",
        r"config\.",
        r"settings\.",
        r"raise",
        r"assert",
        r"error",
        r"warning",
        r"message",
        r"description",
        r"pragma: allowlist secret",  # Our allowlist comment
    ]

    try:
        found_issues = []

        # Scan Python files
        for py_file in Path("app").rglob("*.py"):
            with open(py_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                # Skip comments and docstrings
                stripped_line = line.strip()
                if (
                    stripped_line.startswith("#")
                    or stripped_line.startswith('"""')
                    or stripped_line.startswith("'''")
                ):
                    continue

                # Check each suspicious pattern
                for pattern, pattern_type in suspicious_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        # Check if it's a safe pattern
                        is_safe = False
                        for safe_pattern in safe_patterns:
                            if re.search(safe_pattern, line, re.IGNORECASE):
                                is_safe = True
                                break

                        if not is_safe:
                            # Extract the actual value for inspection
                            match = re.search(pattern, line, re.IGNORECASE)
                            if match:
                                found_issues.append(
                                    {
                                        "file": str(py_file),
                                        "line": line_num,
                                        "type": pattern_type,
                                        "content": stripped_line[
                                            :100
                                        ],  # First 100 chars
                                        "match": match.group(0),
                                    }
                                )

        if not found_issues:
            print("✅ No hardcoded secrets detected")
            return True
        else:
            print(f"⚠️  Found {len(found_issues)} potential secret(s):\n")

            # Group by file for better readability
            files_with_issues = {}
            for issue in found_issues:
                if issue["file"] not in files_with_issues:
                    files_with_issues[issue["file"]] = []
                files_with_issues[issue["file"]].append(issue)

            # Display detailed information
            for file_path, issues in files_with_issues.items():
                print(f"📄 {file_path}:")
                for issue in issues:
                    print(f"   Line {issue['line']}: {issue['type']}")
                    print(f"   Found: {issue['match']}")
                    print(f"   Context: {issue['content']}")
                    print()

            print("\n💡 To fix these issues:")
            print("   1. Replace hardcoded values with environment variables")
            print("   2. Use os.getenv() or configuration management")
            print("   3. Add '# pragma: allowlist secret' comment if it's safe")
            print("   4. Ensure no actual secrets are committed")

            return False

    except Exception as e:
        print(f"❌ Secret scan failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def check_env_files():
    """Check for .env files that shouldn't be committed."""
    print("\n📁 Checking for Environment Files")
    print("-" * 50)

    env_files = [".env", ".env.local", ".env.production"]
    found_env_files = []

    for env_file in env_files:
        if Path(env_file).exists():
            found_env_files.append(env_file)

    if found_env_files:
        print(f"⚠️  Found environment files that should not be committed:")
        for f in found_env_files:
            print(f"   - {f}")
        print("\n   Make sure these are in .gitignore!")
        return False
    else:
        print("✅ No environment files found in repository")
        return True


def main():
    """Run security scans."""
    print("\n" + "=" * 60)
    print("🔒 HARBOR SECURITY SCAN")
    print("=" * 60)

    results = []

    # Run scans
    results.append(("Vulnerability Scan", run_security_scan()))
    results.append(("Secret Detection", check_hardcoded_secrets()))
    results.append(("Environment Files", check_env_files()))

    # Summary
    print("\n" + "=" * 60)
    passed = sum(1 for _, result in results if result)
    total = len(results)

    if passed == total:
        print(f"✅ All security scans passed ({passed}/{total})")
        return True
    else:
        print(f"⚠️  Security issues detected ({passed}/{total} passed)")
        print("\nReview the detailed output above to fix issues.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
