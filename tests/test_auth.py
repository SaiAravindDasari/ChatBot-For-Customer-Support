"""
Unit and Integration tests for Enterprise Authentication and RBAC.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
    DEMO_USERS
)
from httpx import AsyncClient, ASGITransport
from backend.app import app

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
async def client():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

def test_password_hashing():
    pwd = "EnterpriseSecret123"
    hashed = hash_password(pwd)
    assert "pbkdf2_sha256$" in hashed
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_jwt_token_lifecycle():
    payload = {"sub": "admin@querydesk.io", "role": "admin", "name": "Admin User"}
    token = create_access_token(payload, expires_in_hours=1)
    assert token is not None
    assert len(token.split('.')) == 3
    
    decoded = decode_access_token(token)
    assert decoded["sub"] == "admin@querydesk.io"
    assert decoded["role"] == "admin"
    assert decoded["name"] == "Admin User"

@pytest.mark.anyio
class TestAuthAPI:
    async def test_successful_admin_login(self, client):
        response = await client.post("/api/auth/login", json={
            "email": "admin@querydesk.io",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin"

    async def test_successful_agent_login(self, client):
        response = await client.post("/api/auth/login", json={
            "email": "agent.sarah@querydesk.io",
            "password": "agent123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "agent"

    async def test_invalid_login_rejected(self, client):
        response = await client.post("/api/auth/login", json={
            "email": "admin@querydesk.io",
            "password": "WrongPassword999"
        })
        assert response.status_code == 401
