# tests/integration/test_api_key_flow.py
"""
Integration tests for API key authentication flow.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import create_app
from app.db.models.user import User
from app.auth.password import hash_password


@pytest.mark.asyncio
async def test_api_key_creation_and_usage(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Test complete API key creation and usage flow."""
    # Create a test user
    user = User(
        username="testuser",
        password_hash=hash_password("TestPass123!"),
        is_admin=True,
    )
    db_session.add(user)
    await db_session.commit()

    # Login to get session
    login_response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "TestPass123!",  # pragma: allowlist secret
        },  # pragma: allowlist secret
    )
    assert login_response.status_code == 200

    # Get CSRF token from login response
    csrf_token = login_response.json()["csrf_token"]

    # Create API key
    create_response = await async_client.post(
        "/api/v1/auth/api-keys",
        json={
            "name": "test-key",
            "description": "Test API key",
            "expires_days": 30,
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert create_response.status_code == 200

    api_key = create_response.json()["api_key"]
    assert api_key.startswith("sk_harbor_")

    # Use API key to access protected endpoint
    me_response = await async_client.get(
        "/api/v1/auth/me", headers={"X-API-Key": api_key}
    )
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "testuser"

    # List API keys
    list_response = await async_client.get(
        "/api/v1/auth/api-keys", headers={"X-API-Key": api_key}
    )
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["name"] == "test-key"

    # Revoke API key
    key_id = list_response.json()[0]["id"]
    revoke_response = await async_client.delete(
        f"/api/v1/auth/api-keys/{key_id}", headers={"X-CSRF-Token": csrf_token}
    )
    assert revoke_response.status_code == 200

    # Verify revoked key doesn't work
    me_response = await async_client.get(
        "/api/v1/auth/me", headers={"X-API-Key": api_key}
    )
    assert me_response.status_code == 401
