# test_auth_system.py
"""
Comprehensive Authentication System Tests

Tests authentication, session management, API keys, and security features.
Run with: python test_auth_system.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set test environment
os.environ["HARBOR_MODE"] = "development"
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from datetime import datetime, timedelta, UTC
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.user import User
from app.db.models.api_key import APIKey
from app.auth.manager import get_auth_manager
from app.auth.password import (
    hash_password,
    verify_password,
    validate_password,
    generate_password,
)
from app.auth.api_keys import generate_api_key, hash_api_key
from app.auth.sessions import SessionManager


# ============================================================================
# Test Infrastructure
# ============================================================================


async def get_test_db() -> tuple[async_sessionmaker, any]:
    """Create test database and return session factory."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    return SessionLocal, engine


async def create_test_user(session: AsyncSession, username: str = "testuser") -> User:
    """Helper to create a test user."""
    user = User(
        username=username,
        password_hash=hash_password("TestPass123!"),  # pragma: allowlist secret
        email=f"{username}@test.com",
        display_name=f"Test {username.title()}",
        is_admin=False,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    return user


# ============================================================================
# Password Tests
# ============================================================================


async def test_password_hashing():
    """Test password hashing and verification."""
    print("\n🔐 Testing Password Hashing")
    print("-" * 50)

    # Test basic hashing
    password = "StrongPass123!"  # pragma: allowlist secret
    hashed = hash_password(password)

    assert hashed != password, "❌ Password not hashed"
    assert hashed.startswith("$argon2id$"), "❌ Wrong hash format"
    print("✅ Password hashing works")

    # Test verification
    assert verify_password(password, hashed), "❌ Valid password rejected"
    assert not verify_password("WrongPass", hashed), "❌ Invalid password accepted"
    print("✅ Password verification works")

    # Test password validation
    valid, errors = validate_password("weak")
    assert not valid, "❌ Weak password accepted"
    assert len(errors) > 0, "❌ No validation errors returned"

    valid, errors = validate_password("StrongPass123!")
    assert valid, "❌ Strong password rejected"
    assert len(errors) == 0, "❌ Errors for valid password"
    print("✅ Password validation works")

    # Test secure generation
    generated = generate_password(16)
    assert len(generated) == 16, "❌ Wrong password length"
    valid, _ = validate_password(generated)
    assert valid, "❌ Generated password invalid"
    print("✅ Password generation works")


# ============================================================================
# Session Management Tests
# ============================================================================


async def test_session_management():
    """Test session creation and management."""
    print("\n🔑 Testing Session Management")
    print("-" * 50)

    session_manager = SessionManager()

    # Create session
    session = session_manager.create_session(
        user_id=1, username="testuser", is_admin=False, ip_address="127.0.0.1"
    )

    assert session.session_id, "❌ No session ID generated"
    assert session.csrf_token, "❌ No CSRF token generated"
    assert session.user_id == 1, "❌ Wrong user ID"
    assert session.expires_at > datetime.now(UTC), "❌ Session already expired"
    print("✅ Session creation works")

    # Retrieve session
    retrieved = session_manager.get_session(session.session_id)
    assert retrieved, "❌ Session not retrievable"
    assert retrieved.user_id == 1, "❌ Retrieved session has wrong data"
    print("✅ Session retrieval works")

    # CSRF validation
    valid = session_manager.validate_csrf_token(session.session_id, session.csrf_token)
    assert valid, "❌ Valid CSRF token rejected"

    invalid = session_manager.validate_csrf_token(session.session_id, "wrong_token")
    assert not invalid, "❌ Invalid CSRF token accepted"
    print("✅ CSRF validation works")

    # Session invalidation
    session_manager.invalidate_session(session.session_id)
    retrieved = session_manager.get_session(session.session_id)
    assert retrieved is None, "❌ Invalidated session still active"
    print("✅ Session invalidation works")


# ============================================================================
# User Authentication Tests
# ============================================================================


async def test_user_authentication():
    """Test user authentication flow."""
    print("\n👤 Testing User Authentication")
    print("-" * 50)

    SessionLocal, engine = await get_test_db()

    async with SessionLocal() as session:
        # Create test user
        user = await create_test_user(session)
        auth_manager = get_auth_manager()

        # Test successful authentication
        result = await auth_manager.authenticate_user(
            db=session,
            username="testuser",
            password="TestPass123!",  # pragma: allowlist secret
            ip_address="127.0.0.1",
        )

        assert result.success, f"❌ Authentication failed: {result.error_message}"
        assert result.user, "❌ No user returned"
        assert result.session, "❌ No session created"
        print("✅ User authentication works")

        # Test wrong password
        result = await auth_manager.authenticate_user(
            db=session,
            username="testuser",
            password="WrongPass",  # pragma: allowlist secret
            ip_address="127.0.0.1",
        )

        assert not result.success, "❌ Wrong password accepted"
        assert result.user is None, "❌ User returned for failed auth"
        assert "Invalid" in result.error_message, "❌ Wrong error message"
        print("✅ Invalid password rejected")

        # Test non-existent user
        result = await auth_manager.authenticate_user(
            db=session,
            username="nonexistent",
            password="TestPass123!",  # pragma: allowlist secret
            ip_address="127.0.0.1",
        )

        assert not result.success, "❌ Non-existent user authenticated"
        print("✅ Non-existent user rejected")

    await engine.dispose()


# ============================================================================
# Account Security Tests
# ============================================================================


async def test_account_security():
    """Test account lockout and security features."""
    print("\n🔒 Testing Account Security")
    print("-" * 50)

    SessionLocal, engine = await get_test_db()

    async with SessionLocal() as session:
        user = await create_test_user(session)
        auth_manager = get_auth_manager()

        # Simulate multiple failed attempts
        for i in range(6):
            result = await auth_manager.authenticate_user(
                db=session,
                username="testuser",
                password="WrongPass",  # pragma: allowlist secret
                ip_address="127.0.0.1",
            )
            assert not result.success, f"❌ Failed attempt {i + 1} succeeded"

        # Check account is locked
        result = await auth_manager.authenticate_user(
            db=session,
            username="testuser",
            password="TestPass123!",  # Even with correct password # pragma: allowlist secret
            ip_address="127.0.0.1",
        )

        assert not result.success, "❌ Locked account accessed"
        assert result.account_locked, "❌ Account not marked as locked"
        assert "locked" in result.error_message.lower(), "❌ No lockout message"
        print("✅ Account lockout works after 6 attempts")

        # Test inactive user (create a fresh user to avoid lockout interference)
        inactive_user = User(
            username="inactive_user",
            password_hash=hash_password("TestPass123!"),  # pragma: allowlist secret
            email="inactive@test.com",
            is_active=False,  # Created as inactive
        )
        session.add(inactive_user)
        await session.commit()

        result = await auth_manager.authenticate_user(
            db=session,
            username="inactive_user",
            password="TestPass123!",  # pragma: allowlist secret
            ip_address="127.0.0.1",
        )

        assert not result.success, "❌ Inactive account accessed"
        # The error could be either "disabled" or "inactive" depending on implementation
        assert any(
            word in result.error_message.lower()
            for word in ["disabled", "inactive", "locked"]
        ), "❌ No inactive/disabled message"
        print("✅ Inactive accounts blocked")

    await engine.dispose()


# ============================================================================
# API Key Tests
# ============================================================================


async def test_api_keys():
    """Test API key generation and management."""
    print("\n🔑 Testing API Keys")
    print("-" * 50)

    SessionLocal, engine = await get_test_db()

    async with SessionLocal() as session:
        user = await create_test_user(session)

        # Generate API key
        plain_key, hashed_key = generate_api_key()
        assert len(plain_key) > 40, "❌ API key too short"
        assert plain_key.startswith("sk_harbor_"), "❌ Wrong API key prefix"
        assert hashed_key != plain_key, "❌ API key not hashed"
        print("✅ API key generation works")

        # Create API key record
        api_key = APIKey(
            name="test-key",
            key_hash=hashed_key,
            created_by_user_id=user.id,
            description="Test API key",
        )
        api_key.scopes = ["read", "write"]  # Test scope setter

        session.add(api_key)
        await session.commit()

        # Test scope handling
        assert api_key.scopes == ["read", "write"], "❌ Scopes not set correctly"
        assert api_key.has_scope("read"), "❌ Scope check failed"
        assert not api_key.has_scope("admin"), "❌ Invalid scope accepted"
        print("✅ API key scopes work")

        # Test validity checks
        assert api_key.is_valid(), "❌ Valid key marked invalid"

        api_key.revoke()
        assert not api_key.is_valid(), "❌ Revoked key still valid"
        assert api_key.is_revoked(), "❌ Revoked status not set"
        print("✅ API key revocation works")

        # Test expiration
        api_key.expires_at = datetime.now(UTC) - timedelta(hours=1)
        assert api_key.is_expired(), "❌ Expired key not detected"
        assert not api_key.is_valid(), "❌ Expired key marked valid"
        print("✅ API key expiration works")

    await engine.dispose()


# ============================================================================
# Integration Tests
# ============================================================================


async def test_full_auth_flow():
    """Test complete authentication flow."""
    print("\n🔄 Testing Full Authentication Flow")
    print("-" * 50)

    SessionLocal, engine = await get_test_db()

    async with SessionLocal() as session:
        # 1. Create user
        user = User(
            username="fulltest",
            password_hash=hash_password("FullTest123!"),  # pragma: allowlist secret
            email="full@test.com",
            is_admin=True,
        )
        session.add(user)
        await session.commit()
        print("✅ User created")

        # 2. Authenticate
        auth_manager = get_auth_manager()
        result = await auth_manager.authenticate_user(
            db=session,
            username="fulltest",
            password="FullTest123!",  # pragma: allowlist secret
            ip_address="192.168.1.100",
        )

        assert result.success, "❌ Authentication failed"
        assert result.session, "❌ No session created"
        session_id = result.session.session_id
        print("✅ User authenticated")

        # 3. Use session
        session_data = auth_manager.session_manager.get_session(session_id)
        assert session_data, "❌ Session not found"
        assert session_data.username == "fulltest", "❌ Wrong session data"
        assert session_data.is_admin, "❌ Admin status not preserved"
        print("✅ Session active")

        # 4. Create API key
        plain_key, hashed_key = generate_api_key()
        api_key = APIKey(
            name="integration-key", key_hash=hashed_key, created_by_user_id=user.id
        )
        session.add(api_key)
        await session.commit()
        print("✅ API key created")

        # 5. Logout
        auth_manager.logout(session_id)
        session_data = auth_manager.session_manager.get_session(session_id)
        assert session_data is None, "❌ Session not invalidated"
        print("✅ User logged out")

    await engine.dispose()


# ============================================================================
# Main Test Runner
# ============================================================================


async def main():
    """Run all authentication tests."""
    print("\n" + "=" * 60)
    print("🧪 HARBOR AUTHENTICATION SYSTEM TESTS")
    print("=" * 60)

    try:
        await test_password_hashing()
        await test_session_management()
        await test_user_authentication()
        await test_account_security()
        await test_api_keys()
        await test_full_auth_flow()

        print("\n" + "=" * 60)
        print("✅ ALL AUTHENTICATION TESTS PASSED!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
