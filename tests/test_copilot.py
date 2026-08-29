"""
Unit and integration tests for AI Agent Copilot & Smart Suggestion Engine.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.copilot_service import CopilotService
from backend.knowledge.knowledge_base import KnowledgeBase
from backend.knowledge.rag_engine import RAGEngine
from httpx import AsyncClient, ASGITransport
from backend.app import app

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def copilot():
    kb = KnowledgeBase()
    rag = RAGEngine(kb)
    return CopilotService(rag)

@pytest.fixture
async def client():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

def test_copilot_order_drafts(copilot):
    messages = [
        {"role": "user", "content": "Where is my package? I ordered it 3 days ago."}
    ]
    assist = copilot.generate_copilot_assist("test-session-copilot", messages, sentiment_score=-0.2, priority="Medium")
    assert "summary" in assist
    assert len(assist["suggested_drafts"]) >= 2
    assert any("shipping" in d.lower() or "package" in d.lower() or "transit" in d.lower() for d in assist["suggested_drafts"])

def test_copilot_refund_drafts(copilot):
    messages = [
        {"role": "user", "content": "I want a refund for my damaged item"}
    ]
    assist = copilot.generate_copilot_assist("test-session-copilot-2", messages, sentiment_score=-0.6, priority="High")
    assert "Urgent" in assist["summary"] or "Frustrated" in assist["summary"]
    assert any("refund" in d.lower() or "return" in d.lower() for d in assist["suggested_drafts"])

@pytest.mark.anyio
class TestCopilotAPI:
    async def test_copilot_endpoint(self, client):
        # Create a message turn first
        await client.post("/api/chat", json={
            "session_id": "copilot-api-session",
            "message": "My order has not arrived yet",
            "language": "English"
        })

        response = await client.get("/api/agent/copilot/copilot-api-session")
        assert response.status_code == 200
        data = response.json()
        assert "suggested_drafts" in data
        assert len(data["suggested_drafts"]) > 0
