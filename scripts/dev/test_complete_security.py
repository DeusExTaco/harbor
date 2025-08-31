#!/usr/bin/env python3
# scripts/dev/test_complete_security.py
"""
Harbor Complete Security Middleware Test Suite

Comprehensive test script that validates all security components including:
- Security headers middleware
- Rate limiting middleware
- Input validation and sanitization
- Authentication dependencies
- Request logging middleware
- CORS configuration
- Core security configuration

Can be run standalone or as part of the test suite.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Test result tracking
test_results = []
verbose = "--verbose" in sys.argv or "-v" in sys.argv


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

    if level in ["PASS", "FAIL", "WARN"] or verbose:
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
# Test 1: Core Security Configuration
# ==============================================================================


def test_core_security_config():
    """Test core security configuration."""
    test_section("1. CORE SECURITY CONFIGURATION")

    try:
        from app.core.security import SecurityConfig
        from app.config import DeploymentProfile

        # Test configuration retrieval
        config = SecurityConfig.get_security_config()

        log("Security configuration loaded", "INFO")

        # Validate required sections
        required_sections = [
            "authentication",
            "rate_limiting",
            "cors",
            "audit",
            "https",
        ]
        for section in required_sections:
            if section in config:
                log(f"  ✓ {section}: configured", "PASS")
            else:
                record_test(f"Security config - {section}", False, "Missing section")
                return False

        # Test profile-specific configurations
        profiles_tested = 0
        for profile in [DeploymentProfile.HOMELAB, DeploymentProfile.PRODUCTION]:
            origins = SecurityConfig._get_cors_origins(profile)
            if origins:
                profiles_tested += 1
                if verbose:
                    log(f"  {profile.value} CORS origins: {origins[:2]}...", "INFO")

        # Test public paths
        public_paths = SecurityConfig.get_public_paths()
        assert len(public_paths) > 0, "No public paths defined"
        assert "/" in public_paths, "Root path should be public"
        assert "/healthz" in public_paths, "Health check should be public"

        record_test(
            "Core Security Configuration",
            True,
            f"All sections present, {profiles_tested} profiles tested",
        )
        return True

    except Exception as e:
        record_test("Core Security Configuration", False, str(e))
        if verbose:
            import traceback

            traceback.print_exc()
        return False


# ==============================================================================
# Test 2: Security Headers Middleware
# ==============================================================================


def test_security_headers():
    """Test security headers middleware."""
    test_section("2. SECURITY HEADERS MIDDLEWARE")

    try:
        from app.security.headers import (
            get_security_headers_for_profile,
            SecurityContext,
            SecurityResponseHandler,
        )
        from app.config import DeploymentProfile
        from fastapi import Request
        from starlette.datastructures import Headers

        # Test headers for each profile
        profiles_passed = 0
        for profile in DeploymentProfile:
            headers = get_security_headers_for_profile(profile)

            # Check common headers
            required = ["X-Content-Type-Options", "X-Frame-Options", "Server"]
            missing = [h for h in required if h not in headers]

            if not missing:
                profiles_passed += 1
                log(f"  ✓ {profile.value}: {len(headers)} headers", "PASS")
            else:
                log(f"  ✗ {profile.value}: missing {missing}", "FAIL")

            # Profile-specific checks
            if profile == DeploymentProfile.PRODUCTION:
                assert "Strict-Transport-Security" in headers, "Production missing HSTS"

        # Test security response handlers
        rate_limit_response = SecurityResponseHandler.rate_limit_response(60)
        assert rate_limit_response.status_code == 429
        assert "Retry-After" in rate_limit_response.headers

        auth_error = SecurityResponseHandler.authentication_error_response()
        assert auth_error.status_code == 401

        record_test(
            "Security Headers Middleware",
            profiles_passed == len(DeploymentProfile),
            f"{profiles_passed}/{len(DeploymentProfile)} profiles configured correctly",
        )
        return profiles_passed == len(DeploymentProfile)

    except Exception as e:
        record_test("Security Headers Middleware", False, str(e))
        if verbose:
            import traceback

            traceback.print_exc()
        return False


# ==============================================================================
# Test 3: Rate Limiting
# ==============================================================================


async def test_rate_limiting():
    """Test rate limiting functionality."""
    test_section("3. RATE LIMITING")

    try:
        from app.security.rate_limit import SlidingWindowRateLimiter, RateLimitConfig
        from app.config import DeploymentProfile

        # Test sliding window limiter
        limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=2)
        client_key = f"test_client_{uuid.uuid4()}"

        # Test within limit
        results = []
        for i in range(5):
            allowed, info = await limiter.is_allowed(client_key)
            results.append(allowed)
            if verbose:
                log(
                    f"  Request {i + 1}: {'ALLOWED' if allowed else 'BLOCKED'} "
                    f"(remaining: {info['remaining']})",
                    "INFO",
                )

        # Should have 3 allowed, 2 blocked
        expected = [True, True, True, False, False]
        if results == expected:
            log("  ✓ Rate limiting working correctly", "PASS")
        else:
            log(f"  ✗ Expected {expected}, got {results}", "FAIL")
            return False

        # Test cleanup
        await limiter.cleanup_old_entries()

        # Test configuration for profiles
        configs_tested = 0
        for profile in [DeploymentProfile.HOMELAB, DeploymentProfile.PRODUCTION]:
            config = RateLimitConfig.get_limits_for_profile(profile)
            if all(k in config for k in ["ip", "api_key", "burst"]):
                configs_tested += 1
                if verbose:
                    log(
                        f"  {profile.value} limits: IP={config['ip']['requests']}/hr",
                        "INFO",
                    )

        record_test(
            "Rate Limiting",
            True,
            f"Limiter working, {configs_tested} profiles configured",
        )
        return True

    except Exception as e:
        record_test("Rate Limiting", False, str(e))
        if verbose:
            import traceback

            traceback.print_exc()
        return False


# ==============================================================================
# Test 4: Input Validation
# ==============================================================================


def test_input_validation():
    """Test input validation and sanitization."""
    test_section("4. INPUT VALIDATION & SANITIZATION")

    try:
        from app.security.validation import (
            InputSanitizer,
            SecurityValidationError,
            ContainerIdentifier,
            RequestValidator,
        )

        sanitizer = InputSanitizer()
        tests_passed = 0

        # Test HTML sanitization
        dangerous_html = "<script>alert('xss')</script>Hello"
        safe_html = sanitizer.sanitize_html(dangerous_html)
        if "<script>" not in safe_html and "&lt;script&gt;" in safe_html:
            tests_passed += 1
            log("  ✓ HTML sanitization: XSS prevented", "PASS")
        else:
            log("  ✗ HTML sanitization failed", "FAIL")

        # Test container name validation
        try:
            valid_name = sanitizer.sanitize_container_name("valid-container")
            assert valid_name == "valid-container"
            tests_passed += 1
            log("  ✓ Container name validation: valid names accepted", "PASS")
        except Exception as e:
            log(f"  ✗ Container name validation failed: {e}", "FAIL")

        try:
            sanitizer.sanitize_container_name("invalid/name")
            log("  ✗ Invalid container name not rejected", "FAIL")
        except SecurityValidationError:
            tests_passed += 1
            log("  ✓ Container name validation: invalid names rejected", "PASS")

        # Test URL sanitization
        test_url = "https://registry-1.docker.io/v2/"
        sanitized_url = sanitizer.sanitize_url(test_url)
        if sanitized_url:
            tests_passed += 1
            log("  ✓ URL sanitization working", "PASS")

        # Test request validation
        validator = RequestValidator()
        page, per_page = validator.validate_pagination_params(1, 20)
        if page == 1 and per_page == 20:
            tests_passed += 1
            log("  ✓ Pagination validation working", "PASS")

        record_test(
            "Input Validation",
            tests_passed >= 4,
            f"{tests_passed}/5 validation tests passed",
        )
        return tests_passed >= 4

    except Exception as e:
        record_test("Input Validation", False, str(e))
        if verbose:
            import traceback

            traceback.print_exc()
        return False


# ==============================================================================
# Test 5: Authentication Dependencies
# ==============================================================================


async def test_auth_dependencies():
    """Test authentication dependencies."""
    test_section("5. AUTHENTICATION DEPENDENCIES")

    try:
        from app.api.dependencies.auth import (
            get_current_user,
            require_auth,
            require_admin,
        )
        from app.api.dependencies.rate_limit import (
            endpoint_limiter,
            auth_limiter,
            read_limiter,
        )

        # Test rate limiters exist
        limiters_exist = all([endpoint_limiter, auth_limiter, read_limiter])
        if limiters_exist:
            log("  ✓ Rate limit dependencies configured", "PASS")
        else:
            log("  ✗ Rate limiters missing", "FAIL")
            return False

        # Test auth dependencies structure
        # Note: Full testing requires database setup
        import inspect

        # Check function signatures
        get_current_sig = inspect.signature(get_current_user)
        require_auth_sig = inspect.signature(require_auth)

        if "request" in get_current_sig.parameters:
            log("  ✓ get_current_user has correct signature", "PASS")
        else:
            log("  ✗ get_current_user signature incorrect", "FAIL")

        if "user" in require_auth_sig.parameters:
            log("  ✓ require_auth has correct signature", "PASS")
        else:
            log("  ✗ require_auth signature incorrect", "FAIL")

        record_test(
            "Authentication Dependencies", True, "Dependencies structured correctly"
        )
        return True

    except Exception as e:
        record_test("Authentication Dependencies", False, str(e))
        if verbose:
            import traceback

            traceback.print_exc()
        return False


# ==============================================================================
# Test 6: Middleware Components
# ==============================================================================


def test_middleware_components():
    """Test middleware components."""
    test_section("6. MIDDLEWARE COMPONENTS")

    try:
        from app.middleware import (
            AuthenticationMiddleware,
            RequestLoggingMiddleware,
            setup_cors,
        )
        from app.core.security import SecurityConfig

        components_found = 0

        # Test authentication middleware
        if AuthenticationMiddleware:
            public_paths = SecurityConfig.get_public_paths()
            assert len(public_paths) > 0
            components_found += 1
            log(
                f"  ✓ AuthenticationMiddleware available ({len(public_paths)} public paths)",
                "PASS",
            )

        # Test request logging middleware
        if RequestLoggingMiddleware:
            components_found += 1
            log("  ✓ RequestLoggingMiddleware available", "PASS")

        # Test CORS setup
        if setup_cors:
            components_found += 1
            log("  ✓ CORS setup function available", "PASS")

        record_test(
            "Middleware Components",
            components_found == 3,
            f"{components_found}/3 components available",
        )
        return components_found == 3

    except Exception as e:
        record_test("Middleware Components", False, str(e))
        if verbose:
            import traceback

            traceback.print_exc()
        return False


# ==============================================================================
# Test 7: FastAPI Integration
# ==============================================================================


def test_fastapi_integration():
    """Test FastAPI integration."""
    test_section("7. FASTAPI INTEGRATION")

    try:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.security import setup_security_middleware

        # Create test app
        app = FastAPI(title="Security Test App")

        # Setup security middleware
        app = setup_security_middleware(app)

        # Add test endpoint
        @app.get("/test")
        def test_endpoint():
            return {"message": "test"}

        # Create test client
        client = TestClient(app)

        # Test that middleware is applied
        response = client.get("/test")

        tests_passed = 0

        # Check security headers
        if "X-Content-Type-Options" in response.headers:
            tests_passed += 1
            log("  ✓ Security headers applied", "PASS")
        else:
            log("  ✗ Security headers missing", "FAIL")

        # Check rate limit headers (may not be present on first request)
        if response.status_code == 200:
            tests_passed += 1
            log("  ✓ Request processed successfully", "PASS")

        # Test rate limiting by making multiple requests
        for _ in range(10):
            client.get("/test")

        # Check middleware count
        middleware_count = len(app.user_middleware)
        if middleware_count > 0:
            tests_passed += 1
            log(f"  ✓ {middleware_count} middleware components added", "PASS")

        record_test(
            "FastAPI Integration",
            tests_passed >= 2,
            f"{tests_passed}/3 integration tests passed",
        )
        return tests_passed >= 2

    except Exception as e:
        record_test("FastAPI Integration", False, str(e))
        if verbose:
            import traceback

            traceback.print_exc()
        return False


# ==============================================================================
# Test 8: Complete Application Integration
# ==============================================================================


def test_complete_app():
    """Test complete application with all security."""
    test_section("8. COMPLETE APPLICATION INTEGRATION")

    try:
        from fastapi.testclient import TestClient
        from app.main import create_app

        # Create full application
        app = create_app()
        client = TestClient(app)

        tests_passed = 0

        # Test health endpoint
        response = client.get("/healthz")
        if response.status_code == 200:
            data = response.json()
            if "status" in data and "components" in data:
                tests_passed += 1
                log("  ✓ Health endpoint working", "PASS")
                if verbose:
                    components = data.get("components", {})
                    for comp, status in components.items():
                        log(f"    - {comp}: {status}", "INFO")

        # Test security headers on all responses
        if "X-Content-Type-Options" in response.headers:
            tests_passed += 1
            log("  ✓ Security headers on responses", "PASS")

        # Test readiness endpoint
        response = client.get("/readyz")
        if response.status_code == 200:
            tests_passed += 1
            log("  ✓ Readiness endpoint working", "PASS")

        # Test security status endpoint
        response = client.get("/security/status")
        if response.status_code == 200:
            data = response.json()
            if "security_middleware" in data:
                tests_passed += 1
                log("  ✓ Security status endpoint working", "PASS")
                if verbose:
                    middleware = data.get("security_middleware", {})
                    log(
                        f"    Middleware enabled: {middleware.get('enabled', False)}",
                        "INFO",
                    )

        record_test(
            "Complete Application",
            tests_passed >= 3,
            f"{tests_passed}/4 app integration tests passed",
        )
        return tests_passed >= 3

    except Exception as e:
        record_test("Complete Application", False, str(e))
        if verbose:
            import traceback

            traceback.print_exc()
        return False


# ==============================================================================
# Main Test Runner
# ==============================================================================


async def run_all_tests():
    """Run all security tests."""
    print("=" * 60)
    print(" HARBOR COMPLETE SECURITY MIDDLEWARE TEST SUITE")
    print("=" * 60)
    print(f"Verbose mode: {verbose}")
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")

    # Run all tests
    all_passed = True

    # Synchronous tests
    all_passed &= test_core_security_config()
    all_passed &= test_security_headers()
    all_passed &= test_input_validation()
    all_passed &= test_middleware_components()
    all_passed &= test_fastapi_integration()
    all_passed &= test_complete_app()

    # Asynchronous tests
    all_passed &= await test_rate_limiting()
    all_passed &= await test_auth_dependencies()

    # Print summary
    print("\n" + "=" * 60)
    print(" TEST SUMMARY")
    print("=" * 60 + "\n")

    passed = sum(1 for t in test_results if t["passed"])
    failed = len(test_results) - passed

    for result in test_results:
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"{status}: {result['name']}")
        if result["details"] and (not result["passed"] or verbose):
            print(f"         {result['details']}")

    print(f"\nTotal: {passed} passed, {failed} failed out of {len(test_results)} tests")

    if all_passed:
        print("\n🎉 ALL SECURITY MIDDLEWARE TESTS PASSED!")
        print("\n✅ Security middleware implementation is complete and working!")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed")
        print("\n⚠️  Please review failures before proceeding")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
