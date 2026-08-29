"""
Unit and integration tests for Branded Support Transcript & Resolution Exporter.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

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

@pytest.mark.anyio
class TestTranscriptExportAPI:
    async def test_transcript_html_export(self, client):
        # Create turns
        await client.post("/api/chat", json={
            "session_id": "test-transcript-session-99",
            "message": "Can you check my order #QD-1234?",
            "language": "English"
        })

        # Fetch transcript
        res = await client.get("/api/sessions/test-transcript-session-99/transcript-export")
        assert res.status_code == 200
        assert "text/html" in res.headers["content-type"]
        assert "QueryDesk Support Transcript" in res.text
        assert "test-transcript-session-99" in res.text
        assert "RESOLUTION VERIFIED" in res.text
