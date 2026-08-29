"""
Unit and Integration tests for Security Headers and Input Sanitization.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.security import sanitize_input
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

def test_sanitize_input_xss_prevention():
    malicious = "<script>alert('XSS')</script>Hello & welcome"
    cleaned = sanitize_input(malicious)
    assert "<script>" not in cleaned
    assert "&lt;script&gt;" in cleaned
    assert "&amp;" in cleaned

def test_sanitize_input_control_characters():
    dirty = "Valid text\x00with null\x08bytes"
    cleaned = sanitize_input(dirty)
    assert "\x00" not in cleaned
    assert "\x08" not in cleaned

@pytest.mark.anyio
class TestSecurityHeaders:
    async def test_security_headers_present(self, client):
        response = await client.get("/api/health")
        assert response.status_code == 200
        headers = response.headers
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "SAMEORIGIN"
        assert "Content-Security-Policy" in headers
        assert "X-Correlation-ID" in headers
        assert "X-Response-Time-Ms" in headers
