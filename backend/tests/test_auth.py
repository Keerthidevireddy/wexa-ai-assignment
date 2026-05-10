"""Tests for all authentication & API key endpoints.

Endpoints tested:
  POST /auth/signup        - Register new user + org
  POST /auth/login         - Login with credentials
  POST /auth/refresh       - Refresh expired access token
  GET  /auth/me            - Get current user profile
  POST /auth/invite        - Invite user to org (admin+)
  POST /auth/api-keys      - Generate new API key (admin+)
  GET  /auth/api-keys      - List active API keys (admin+)
  DELETE /auth/api-keys/id - Revoke an API key (admin+)
"""

import pytest
from httpx import AsyncClient
from tests.conftest import create_test_user


# ════════════════════════════════════════════════
#  SIGNUP
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_signup_success(client: AsyncClient):
    """POST /auth/signup — successful registration returns 201 with tokens."""
    response = await client.post("/api/v1/auth/signup", json={
        "email": "signup_success@test.com",
        "password": "securepassword123",
        "full_name": "New User",
        "org_name": "New Org",
    })
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "signup_success@test.com"
    assert data["user"]["role"] == "owner"
    assert data["user"]["org_id"] is not None
    assert data["user"]["is_active"] is True


@pytest.mark.asyncio
async def test_signup_duplicate_email(client: AsyncClient):
    """POST /auth/signup — duplicate email returns 409 Conflict."""
    payload = {
        "email": "duplicate@test.com",
        "password": "securepassword123",
        "full_name": "User One",
        "org_name": "Org One",
    }
    r1 = await client.post("/api/v1/auth/signup", json=payload)
    assert r1.status_code == 201

    r2 = await client.post("/api/v1/auth/signup", json={
        **payload, "full_name": "User Two", "org_name": "Org Two",
    })
    assert r2.status_code == 409, f"Expected 409, got {r2.status_code}: {r2.text}"
    assert r2.json()["error"]["code"] == "CONFLICT"


@pytest.mark.asyncio
async def test_signup_validation_short_password(client: AsyncClient):
    """POST /auth/signup — password too short returns 422."""
    response = await client.post("/api/v1/auth/signup", json={
        "email": "short@test.com",
        "password": "short",
        "full_name": "User",
        "org_name": "Org",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_signup_validation_invalid_email(client: AsyncClient):
    """POST /auth/signup — invalid email format returns 422."""
    response = await client.post("/api/v1/auth/signup", json={
        "email": "not-an-email",
        "password": "securepassword123",
        "full_name": "User",
        "org_name": "Org",
    })
    assert response.status_code == 422


# ════════════════════════════════════════════════
#  LOGIN
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """POST /auth/login — valid credentials returns tokens."""
    await create_test_user(client, "login_ok@test.com")
    response = await client.post("/api/v1/auth/login", json={
        "email": "login_ok@test.com",
        "password": "securepassword123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "login_ok@test.com"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """POST /auth/login — wrong password returns 401."""
    await create_test_user(client, "login_bad@test.com")
    response = await client.post("/api/v1/auth/login", json={
        "email": "login_bad@test.com",
        "password": "wrongpassword",
    })
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_ERROR"


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """POST /auth/login — non-existent email returns 401."""
    response = await client.post("/api/v1/auth/login", json={
        "email": "ghost@test.com",
        "password": "securepassword123",
    })
    assert response.status_code == 401


# ════════════════════════════════════════════════
#  REFRESH TOKEN
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_refresh_token_success(client: AsyncClient):
    """POST /auth/refresh — valid refresh token returns new access token."""
    user_data = await create_test_user(client, "refresh@test.com")
    response = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": user_data["refresh_token"],
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert len(data["access_token"]) > 20  # valid JWT


@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient):
    """POST /auth/refresh — invalid token returns 401."""
    response = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": "invalid.token.here",
    })
    assert response.status_code == 401


# ════════════════════════════════════════════════
#  GET /auth/me
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_me_unauthenticated(client: AsyncClient):
    """GET /auth/me — no token returns 401 (HTTPBearer auto)."""
    response = await client.get("/api/v1/auth/me")
    # HTTPBearer returns 403 by default when no credentials provided
    assert response.status_code in [401, 403]


@pytest.mark.asyncio
async def test_me_authenticated(client: AsyncClient):
    """GET /auth/me — valid token returns user profile."""
    user_data = await create_test_user(client, "me@test.com")
    response = await client.get("/api/v1/auth/me", headers=user_data["headers"])
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@test.com"
    assert data["full_name"] == "Test User"
    assert "id" in data
    assert "org_id" in data


# ════════════════════════════════════════════════
#  INVITE
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_invite_user(client: AsyncClient):
    """POST /auth/invite — admin can invite a new user."""
    admin = await create_test_user(client, "inviter@test.com")
    response = await client.post("/api/v1/auth/invite", json={
        "email": "invited@test.com",
        "role": "analyst",
    }, headers=admin["headers"])
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "invited@test.com"


# ════════════════════════════════════════════════
#  API KEYS
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_api_key(client: AsyncClient):
    """POST /auth/api-keys — create returns raw key (shown once)."""
    user_data = await create_test_user(client, "apikey_create@test.com")
    response = await client.post("/api/v1/auth/api-keys", json={
        "name": "Production Key",
    }, headers=user_data["headers"])
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Production Key"
    assert "raw_key" in data
    assert data["raw_key"].startswith("ak_")
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_list_api_keys(client: AsyncClient):
    """GET /auth/api-keys — list returns active keys (without raw key)."""
    user_data = await create_test_user(client, "apikey_list@test.com")
    # Create a key first
    await client.post("/api/v1/auth/api-keys", json={"name": "Key 1"}, headers=user_data["headers"])
    
    response = await client.get("/api/v1/auth/api-keys", headers=user_data["headers"])
    assert response.status_code == 200
    keys = response.json()
    assert len(keys) >= 1
    assert "raw_key" not in keys[0]  # raw_key should not be in list
    assert "key_prefix" in keys[0]


@pytest.mark.asyncio
async def test_revoke_api_key(client: AsyncClient):
    """DELETE /auth/api-keys/{id} — revoke makes key inactive."""
    user_data = await create_test_user(client, "apikey_revoke@test.com")
    create_resp = await client.post("/api/v1/auth/api-keys", json={"name": "Temp Key"}, headers=user_data["headers"])
    key_id = create_resp.json()["id"]

    response = await client.delete(f"/api/v1/auth/api-keys/{key_id}", headers=user_data["headers"])
    assert response.status_code == 204

    # Verify it's gone from list
    list_resp = await client.get("/api/v1/auth/api-keys", headers=user_data["headers"])
    key_ids = [k["id"] for k in list_resp.json()]
    assert key_id not in key_ids


@pytest.mark.asyncio
async def test_revoke_nonexistent_api_key(client: AsyncClient):
    """DELETE /auth/api-keys/{id} — non-existent key returns 404."""
    user_data = await create_test_user(client, "apikey_404@test.com")
    response = await client.delete("/api/v1/auth/api-keys/fake-id", headers=user_data["headers"])
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_rotate_api_key(client: AsyncClient):
    """POST /auth/api-keys/{id}/rotate — rotate revokes old, creates new."""
    user_data = await create_test_user(client, "apikey_rotate@test.com")
    create_resp = await client.post("/api/v1/auth/api-keys", json={"name": "Rotate Me"}, headers=user_data["headers"])
    old_key = create_resp.json()
    old_id = old_key["id"]

    rotate_resp = await client.post(f"/api/v1/auth/api-keys/{old_id}/rotate", headers=user_data["headers"])
    assert rotate_resp.status_code == 201
    new_key = rotate_resp.json()
    assert new_key["name"] == "Rotate Me"
    assert new_key["raw_key"].startswith("ak_")
    assert new_key["id"] != old_id  # new key, different ID

    # Old key should no longer be in active list
    list_resp = await client.get("/api/v1/auth/api-keys", headers=user_data["headers"])
    active_ids = [k["id"] for k in list_resp.json()]
    assert old_id not in active_ids
    assert new_key["id"] in active_ids


# ════════════════════════════════════════════════
#  HTTP-ONLY COOKIE (Refresh Token)
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_signup_sets_refresh_cookie(client: AsyncClient):
    """POST /auth/signup — response sets refresh_token as HTTP-only cookie."""
    response = await client.post("/api/v1/auth/signup", json={
        "email": "cookie_signup@test.com",
        "password": "securepassword123",
        "full_name": "Cookie User",
        "org_name": "Cookie Org",
    })
    assert response.status_code == 201
    # Check the Set-Cookie header
    cookie_header = response.headers.get("set-cookie", "")
    assert "refresh_token=" in cookie_header
    assert "httponly" in cookie_header.lower()


@pytest.mark.asyncio
async def test_login_sets_refresh_cookie(client: AsyncClient):
    """POST /auth/login — response sets refresh_token as HTTP-only cookie."""
    await create_test_user(client, "cookie_login@test.com")
    response = await client.post("/api/v1/auth/login", json={
        "email": "cookie_login@test.com",
        "password": "securepassword123",
    })
    assert response.status_code == 200
    cookie_header = response.headers.get("set-cookie", "")
    assert "refresh_token=" in cookie_header
    assert "httponly" in cookie_header.lower()


@pytest.mark.asyncio
async def test_logout_clears_cookie(client: AsyncClient):
    """POST /auth/logout — clears the refresh_token cookie."""
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 204
    cookie_header = response.headers.get("set-cookie", "")
    assert "refresh_token=" in cookie_header


# ════════════════════════════════════════════════
#  GOOGLE OAUTH2
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_google_login_no_config(client: AsyncClient):
    """GET /auth/google — returns error when not configured."""
    response = await client.get("/api/v1/auth/google")
    # GOOGLE_CLIENT_ID is empty in tests, so this should return auth error
    assert response.status_code == 401
    assert "not configured" in response.json()["error"]["message"].lower()
