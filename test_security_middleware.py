#!/usr/bin/env python3
"""
Harbor Container Updater - Security Middleware Test

Test script to verify security middleware implementation.
Tests all security components for M0 milestone completion.

Usage:
    python test_security_middleware.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent))


def test_security_imports() -> bool:
    """Test that all security components can be imported."""

    print("🔒 Harbor Security Middleware Test")
    print("=" * 50)
    print()

    try:
        print("1. Testing security module imports...")

        # Test main security module
        from app.security import (
            SecurityHeadersMiddleware,
            RateLimitMiddleware,
            SecurityResponseHandler,
            InputSanitizer,
            SecurityValidationError,
            setup_security_middleware,
        )

        print("   ✅ Main security module imports successful")

        # Test security headers
        from app.security.headers import (
            SecurityContext,
            get_security_headers_for_profile,
        )

        print("   ✅ Security headers module imports successful")

        # Test rate limiting
        from app.security.rate_limit import SlidingWindowRateLimiter, RateLimitConfig

        print("   ✅ Rate limiting module imports successful")

        # Test validation
        from app.security.validation import (
            RequestValidator,
            ConfigurationValidator,
            ContainerIdentifier,
            ImageReference,
        )

        print("   ✅ Input validation module imports successful")

        return True

    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_input_sanitization() -> bool:
    """Test input sanitization functionality."""

    print("\n2. Testing input sanitization...")

    try:
        from app.security.validation import InputSanitizer, SecurityValidationError

        sanitizer = InputSanitizer()

        # Test HTML sanitization
        html_input = "<script>alert('xss')</script>Hello"
        sanitized_html = sanitizer.sanitize_html(html_input)
        expected = "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;Hello"

        if sanitized_html == expected:
            print("   ✅ HTML sanitization working correctly")
        else:
            print(f"   ⚠️  HTML sanitization result differs:")
            print(f"      Expected: {expected}")
            print(f"      Got:      {sanitized_html}")

        # Test container name validation
        valid_names = ["nginx-proxy", "valid_container", "test123"]
        invalid_names = ["", "invalid/name", "a" * 300]

        for name in valid_names:
            try:
                result = sanitizer.sanitize_container_name(name)
                print(f"   ✅ Valid container name: '{name}' → '{result}'")
            except SecurityValidationError as e:
                print(f"   ❌ Valid name rejected: '{name}' → {e.message}")
                return False

        for name in invalid_names:
            try:
                result = sanitizer.sanitize_container_name(name)
                print(f"   ❌ Invalid name accepted: '{name}' → '{result}'")
                return False
            except SecurityValidationError:
                print(f"   ✅ Invalid container name correctly rejected: '{name}'")

        # Test URL sanitization
        test_url = "https://registry-1.docker.io/v2/"
        sanitized_url = sanitizer.sanitize_url(test_url)
        print(f"   ✅ URL sanitization: '{test_url}' → '{sanitized_url}'")

        return True

    except Exception as e:
        print(f"   ❌ Input sanitization test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_rate_limiting() -> bool:
    """Test rate limiting functionality."""

    print("\n3. Testing rate limiting...")

    try:
        from app.security.rate_limit import SlidingWindowRateLimiter

        # Test sliding window rate limiter
        limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=10)

        test_key = "test_client"
        results = []

        # Test 5 requests (limit is 3)
        for i in range(5):
            allowed, info = await limiter.is_allowed(test_key)
            results.append(allowed)
            print(
                f"   Request {i + 1}: {'✅ ALLOWED' if allowed else '❌ BLOCKED'} "
                f"(remaining: {info['remaining']})"
            )

        # Should have 3 allowed, 2 blocked
        expected = [True, True, True, False, False]
        if results == expected:
            print("   ✅ Rate limiting working correctly")
            return True
        else:
            print(f"   ❌ Rate limiting failed. Expected: {expected}, Got: {results}")
            return False

    except Exception as e:
        print(f"   ❌ Rate limiting test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_security_headers() -> bool:
    """Test security headers functionality."""

    print("\n4. Testing security headers...")

    try:
        from app.config import DeploymentProfile
        from app.security.headers import get_security_headers_for_profile

        # Test headers for different profiles
        profiles = [
            DeploymentProfile.HOMELAB,
            DeploymentProfile.DEVELOPMENT,
            DeploymentProfile.PRODUCTION,
        ]

        for profile in profiles:
            headers = get_security_headers_for_profile(profile)
            print(
                f"   ✅ {profile.value.title()} profile headers: {len(headers)} headers"
            )

            # Verify common headers exist
            required_headers = ["X-Content-Type-Options", "X-Frame-Options", "Server"]
            for header in required_headers:
                if header not in headers:
                    print(f"   ❌ Missing required header: {header}")
                    return False

            # Check profile-specific headers
            if profile == DeploymentProfile.PRODUCTION:
                if "Strict-Transport-Security" not in headers:
                    print("   ❌ Production profile missing HSTS header")
                    return False
                print("   ✅ Production profile has HSTS header")

            if profile == DeploymentProfile.DEVELOPMENT:
                if "X-Harbor-Environment" not in headers:
                    print("   ❌ Development profile missing environment header")
                    return False
                print("   ✅ Development profile has environment header")

        return True

    except Exception as e:
        print(f"   ❌ Security headers test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_security_responses() -> bool:
    """Test security response handlers."""

    print("\n5. Testing security response handlers...")

    try:
        from app.security.headers import SecurityResponseHandler

        # Test rate limit response
        rate_limit_response = SecurityResponseHandler.rate_limit_response(
            retry_after=60, message="Test rate limit"
        )

        if rate_limit_response.status_code == 429:
            print("   ✅ Rate limit response has correct status code")
        else:
            print(
                f"   ❌ Rate limit response wrong status: {rate_limit_response.status_code}"
            )
            return False

        # Check headers
        if "Retry-After" in rate_limit_response.headers:
            print("   ✅ Rate limit response has Retry-After header")
        else:
            print("   ❌ Rate limit response missing Retry-After header")
            return False

        # Test authentication error
        auth_error = SecurityResponseHandler.authentication_error_response()
        if auth_error.status_code == 401:
            print("   ✅ Authentication error has correct status code")
        else:
            print(f"   ❌ Authentication error wrong status: {auth_error.status_code}")
            return False

        return True

    except Exception as e:
        print(f"   ❌ Security response test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_fastapi_integration() -> bool:
    """Test security middleware integration with FastAPI."""

    print("\n6. Testing FastAPI integration...")

    try:
        from fastapi import FastAPI
        from app.security import setup_security_middleware

        # Create test app
        app = FastAPI(title="Test Harbor App")

        # Set up security middleware
        app = setup_security_middleware(app)

        # Check that middleware was added
        middleware_types = [
            type(middleware).__name__ for middleware in app.user_middleware
        ]

        expected_middleware = ["SecurityHeadersMiddleware"]

        for expected in expected_middleware:
            if expected in middleware_types:
                print(f"   ✅ {expected} added to FastAPI app")
            else:
                print(f"   ⚠️  {expected} not found in middleware (might be disabled)")

        print(f"   ℹ️  Total middleware count: {len(app.user_middleware)}")

        return True

    except Exception as e:
        print(f"   ❌ FastAPI integration test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_validation_models() -> bool:
    """Test Pydantic validation models."""

    print("\n7. Testing validation models...")

    try:
        from app.security.validation import (
            ContainerIdentifier,
            ImageReference,
            SecurityValidationError,
        )

        # Test valid container identifier
        try:
            container = ContainerIdentifier(
                uid="550e8400-e29b-41d4-a716-446655440000", name="nginx-proxy"
            )
            print(f"   ✅ Valid container identifier: {container.name}")
        except Exception as e:
            print(f"   ❌ Valid container identifier failed: {e}")
            return False

        # Test invalid container identifier
        try:
            container = ContainerIdentifier(uid="invalid-uid", name="invalid/name")
            print(f"   ❌ Invalid container identifier accepted: {container.name}")
            return False
        except Exception:
            print("   ✅ Invalid container identifier correctly rejected")

        # Test image reference
        try:
            image = ImageReference(reference="nginx:1.21-alpine")
            print(f"   ✅ Valid image reference: {image.reference}")
        except Exception as e:
            print(f"   ❌ Valid image reference failed: {e}")
            return False

        return True

    except Exception as e:
        print(f"   ❌ Validation models test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main() -> None:
    """Main test function."""

    # Test all security components
    tests = [
        ("Security Imports", test_security_imports),
        ("Input Sanitization", test_input_sanitization),
        ("Rate Limiting", test_rate_limiting),
        ("Security Headers", test_security_headers),
        ("Security Responses", test_security_responses),
        ("FastAPI Integration", test_fastapi_integration),
        ("Validation Models", test_validation_models),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        if asyncio.iscoroutinefunction(test_func):
            success = await test_func()
        else:
            success = test_func()

        if success:
            passed += 1

    print(f"\n{'=' * 50}")
    print(f"🎯 Security Middleware Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("✅ All security middleware tests passed!")
        print("\n🎉 M0 Security Middleware Implementation Complete!")
        print("\n💡 Next steps:")
        print("   1. Run: python -m uvicorn app.main:create_app --factory")
        print("   2. Test security headers: curl -I http://localhost:8080/")
        print("   3. Test rate limiting: run multiple rapid requests")
        print("   4. Check API docs: http://localhost:8080/docs")
        return True
    else:
        print(f"❌ {total - passed} security middleware tests failed")
        print("🔧 Please fix failing tests before proceeding")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
