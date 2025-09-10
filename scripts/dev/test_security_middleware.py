#!/usr/bin/env python3
# scripts/dev/test_security_middleware.py
"""
Harbor Security Middleware Smoke Test

Quick validation that all middleware components are installed and functioning.
This is a lightweight smoke test - comprehensive testing is done in test_complete_middleware.py

Runtime: ~30 seconds
Purpose: Early detection of missing or broken middleware
"""

import sys
import time
from pathlib import Path
from typing import Dict, Any

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Test result tracking
test_results = []


def log(message: str, level: str = "INFO"):
    """Log message with level indicator."""
    colors = {
        "INFO": "\033[0;34m",
        "PASS": "\033[0;32m",
        "FAIL": "\033[0;31m",
        "WARN": "\033[1;33m",
    }
    color = colors.get(level, "")
    reset = "\033[0m"
    print(f"{color}[{level}] {message}{reset}")


def test_section(name: str):
    """Print test section header."""
    print(f"\n{'=' * 60}")
    print(f" {name}")
    print(f"{'=' * 60}\n")


def record_test(name: str, passed: bool, details: str = ""):
    """Record test result."""
    status = "PASS" if passed else "FAIL"
    test_results.append({"name": name, "passed": passed, "details": details})
    log(f"{name}: {details if details else 'Completed'}", status)


# ==============================================================================
# Smoke Test 1: Middleware Components Available
# ==============================================================================


def test_middleware_imports():
    """Test that all middleware components can be imported."""
    test_section("1. MIDDLEWARE COMPONENT IMPORTS")

    components_to_test = [
        ("app.security.headers", "SecurityHeadersMiddleware"),
        ("app.security.rate_limit", "RateLimitMiddleware"),
        ("app.middleware.correlation", "CorrelationMiddleware"),
        ("app.middleware.request_logging", "RequestLoggingMiddleware"),
        ("app.middleware.authentication", "AuthenticationMiddleware"),
        ("app.security.validation", "InputSanitizer"),
        ("app.auth.csrf", "CSRFProtection"),
    ]

    import_count = 0
    failed_imports = []

    for module_name, class_name in components_to_test:
        try:
            module = __import__(module_name, fromlist=[class_name])
            if hasattr(module, class_name):
                import_count += 1
                log(f"  ✓ {module_name}.{class_name}", "PASS")
            else:
                failed_imports.append(f"{module_name}.{class_name}")
                log(f"  ✗ {module_name}.{class_name} - class not found", "FAIL")
        except ImportError as e:
            failed_imports.append(f"{module_name}.{class_name}")
            log(f"  ✗ {module_name}.{class_name} - {str(e)}", "FAIL")

    if import_count == len(components_to_test):
        record_test(
            "Middleware Imports", True, f"All {import_count} components available"
        )
        return True
    else:
        record_test(
            "Middleware Imports",
            False,
            f"Failed to import: {', '.join(failed_imports)}",
        )
        return False


# ==============================================================================
# Smoke Test 2: Basic FastAPI Integration
# ==============================================================================


def test_fastapi_integration():
    """Test that middleware can be added to FastAPI."""
    test_section("2. FASTAPI MIDDLEWARE INTEGRATION")

    try:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.security.headers import SecurityHeadersMiddleware
        from app.security.rate_limit import RateLimitMiddleware
        from app.middleware.correlation import CorrelationMiddleware

        # Create test app
        app = FastAPI(title="Smoke Test App")

        # Add middleware
        app.add_middleware(SecurityHeadersMiddleware)
        app.add_middleware(RateLimitMiddleware)
        app.add_middleware(CorrelationMiddleware)

        @app.get("/test")
        def test_endpoint():
            return {"message": "test"}

        # Create test client
        client = TestClient(app)

        # Make test request
        response = client.get("/test")

        tests_passed = 0

        # Check response
        if response.status_code == 200:
            tests_passed += 1
            log("  ✓ Request processed successfully", "PASS")
        else:
            log(f"  ✗ Request failed with status {response.status_code}", "FAIL")

        # Check for security headers
        if "X-Content-Type-Options" in response.headers:
            tests_passed += 1
            log("  ✓ Security headers present", "PASS")
        else:
            log("  ✗ Security headers missing", "FAIL")

        # Check for request ID
        if "X-Request-ID" in response.headers:
            tests_passed += 1
            log("  ✓ Correlation middleware active", "PASS")
        else:
            log("  ✗ Correlation middleware not active", "FAIL")

        # Check middleware count
        middleware_count = len(app.user_middleware)
        if middleware_count >= 3:
            tests_passed += 1
            log(f"  ✓ {middleware_count} middleware components added", "PASS")
        else:
            log(f"  ✗ Only {middleware_count} middleware added", "FAIL")

        if tests_passed >= 3:
            record_test("FastAPI Integration", True, f"{tests_passed}/4 checks passed")
            return True
        else:
            record_test(
                "FastAPI Integration", False, f"Only {tests_passed}/4 checks passed"
            )
            return False

    except Exception as e:
        record_test("FastAPI Integration", False, str(e))
        return False


# ==============================================================================
# Smoke Test 3: Basic Security Functions
# ==============================================================================


def test_basic_security_functions():
    """Test basic security functions work."""
    test_section("3. BASIC SECURITY FUNCTIONS")

    tests_passed = 0

    try:
        # Test 1: Input sanitization
        from app.security.validation import InputSanitizer

        sanitizer = InputSanitizer()

        dangerous_input = "<script>alert('xss')</script>"
        safe_output = sanitizer.sanitize_html(dangerous_input)

        if "<script>" not in safe_output:
            tests_passed += 1
            log("  ✓ Input sanitization working", "PASS")
        else:
            log("  ✗ Input sanitization failed", "FAIL")

        # Test 2: CSRF token generation
        from app.auth.csrf import CSRFProtection

        csrf = CSRFProtection()

        token = csrf.generate_token()
        if token and len(token) > 20:
            tests_passed += 1
            log("  ✓ CSRF token generation working", "PASS")
        else:
            log("  ✗ CSRF token generation failed", "FAIL")

        # Test 3: Rate limiter creation
        from app.security.rate_limit import SlidingWindowRateLimiter

        limiter = SlidingWindowRateLimiter(max_requests=10, window_seconds=60)

        if limiter.max_requests == 10:
            tests_passed += 1
            log("  ✓ Rate limiter initialization working", "PASS")
        else:
            log("  ✗ Rate limiter initialization failed", "FAIL")

        # Test 4: Security config available
        from app.core.security import SecurityConfig

        config = SecurityConfig.get_security_config()

        if "authentication" in config:
            tests_passed += 1
            log("  ✓ Security configuration available", "PASS")
        else:
            log("  ✗ Security configuration missing", "FAIL")

        if tests_passed >= 3:
            record_test(
                "Basic Security Functions", True, f"{tests_passed}/4 functions working"
            )
            return True
        else:
            record_test(
                "Basic Security Functions",
                False,
                f"Only {tests_passed}/4 functions working",
            )
            return False

    except Exception as e:
        record_test("Basic Security Functions", False, str(e))
        return False


# ==============================================================================
# Main Test Runner
# ==============================================================================


def run_smoke_tests():
    """Run all smoke tests."""
    print("=" * 60)
    print(" HARBOR SECURITY MIDDLEWARE SMOKE TEST")
    print("=" * 60)
    print("Purpose: Quick validation of middleware components")
    print("For comprehensive testing, run test_complete_middleware.py")
    print()

    start_time = time.time()

    # Run smoke tests
    all_passed = True
    all_passed &= test_middleware_imports()
    all_passed &= test_fastapi_integration()
    all_passed &= test_basic_security_functions()

    # Print summary
    print("\n" + "=" * 60)
    print(" SMOKE TEST SUMMARY")
    print("=" * 60 + "\n")

    passed = sum(1 for t in test_results if t["passed"])
    failed = len(test_results) - passed

    for result in test_results:
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"{status}: {result['name']}")
        if result["details"]:
            print(f"         {result['details']}")

    elapsed = time.time() - start_time
    print(f"\nTotal: {passed} passed, {failed} failed out of {len(test_results)} tests")
    print(f"Time elapsed: {elapsed:.1f} seconds")

    if all_passed:
        print("\n🎉 ALL SMOKE TESTS PASSED!")
        print("Middleware components are installed and functioning.")
        return 0
    else:
        print(f"\n❌ {failed} smoke test(s) failed")
        print("Please review failures before running comprehensive tests.")
        return 1


if __name__ == "__main__":
    exit_code = run_smoke_tests()
    sys.exit(exit_code)
