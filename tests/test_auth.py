"""
Tests for authentication endpoints.
"""
import pytest
from httpx import AsyncClient

from tests.conftest import auth_header


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test root endpoint."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_admin):
    """Test successful login."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@test.com",
            "password": "testpassword",
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "admin@test.com"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient, test_admin):
    """Test login with invalid credentials."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@test.com",
            "password": "wrongpassword",
        }
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login with nonexistent user."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@test.com",
            "password": "password",
        }
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, admin_token: str):
    """Test getting current user profile."""
    response = await client.get(
        "/api/v1/auth/me",
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@test.com"
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_get_current_user_unauthorized(client: AsyncClient):
    """Test getting current user without authentication."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, test_admin):
    """Test token refresh."""
    # First login
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@test.com",
            "password": "testpassword",
        }
    )
    refresh_token = login_response.json()["refresh_token"]

    # Refresh token
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, test_admin):
    """Test logout."""
    # First login
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@test.com",
            "password": "testpassword",
        }
    )
    access_token = login_response.json()["access_token"]
    refresh_token = login_response.json()["refresh_token"]

    # Logout
    response = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
        headers=auth_header(access_token),
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_password_change(client: AsyncClient, test_admin, admin_token: str):
    """Test password change."""
    response = await client.post(
        "/api/v1/auth/password/change",
        json={
            "current_password": "testpassword",
            "new_password": "newpassword123",
            "confirm_password": "newpassword123",
        },
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200

    # Try logging in with new password
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@test.com",
            "password": "newpassword123",
        }
    )
    assert login_response.status_code == 200
