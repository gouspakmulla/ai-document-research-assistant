import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_flow(client: AsyncClient):
    payload = {
        "email": "scientist@university.edu",
        "password": "validPassword123!",
        "full_name": "Dr. Sarah Connor"
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "scientist@university.edu"
    assert data["full_name"] == "Dr. Sarah Connor"
    assert "hashed_password" not in data
    assert "doc_assistant_session" in response.cookies

@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {
        "email": "duplicate@university.edu",
        "password": "validPassword123!",
        "full_name": "Duplicate User"
    }
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]

@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    payload = {
        "email": "shortpass@university.edu",
        "password": "short",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_login_flow(client: AsyncClient):
    register_payload = {
        "email": "loginuser@university.edu",
        "password": "validPassword123!",
        "full_name": "Login User"
    }
    reg_res = await client.post("/api/v1/auth/register", json=register_payload)
    assert reg_res.status_code == 201

    # Login with valid credentials
    login_res = await client.post("/api/v1/auth/login", json={
        "email": "loginuser@university.edu",
        "password": "validPassword123!"
    })
    assert login_res.status_code == 200
    assert "doc_assistant_session" in login_res.cookies

    # Login with invalid password
    bad_login = await client.post("/api/v1/auth/login", json={
        "email": "loginuser@university.edu",
        "password": "wrongPassword!"
    })
    assert bad_login.status_code == 401

@pytest.mark.asyncio
async def test_session_me_and_csrf(client: AsyncClient):
    # Register and maintain cookies
    reg_res = await client.post("/api/v1/auth/register", json={
        "email": "sessionuser@university.edu",
        "password": "validPassword123!",
        "full_name": "Session User"
    })
    assert reg_res.status_code == 201

    # /api/v1/auth/me should return authenticated user details
    me_res = await client.get("/api/v1/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "sessionuser@university.edu"

    # /api/v1/auth/csrf should issue a valid CSRF token
    csrf_res = await client.get("/api/v1/auth/csrf")
    assert csrf_res.status_code == 200
    assert "csrf_token" in csrf_res.json()
    assert len(csrf_res.json()["csrf_token"]) > 20

@pytest.mark.asyncio
async def test_unauthenticated_access_denied(client: AsyncClient):
    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 401

@pytest.mark.asyncio
async def test_logout_clears_cookie(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "logoutuser@university.edu",
        "password": "validPassword123!",
    })
    logout_res = await client.post("/api/v1/auth/logout")
    assert logout_res.status_code == 200
