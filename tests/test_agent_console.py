"""
Integration tests for the Live Human Agent Console endpoints and takeover functionality.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from httpx import AsyncClient, ASGITransport
from backend.app import app, live_manager
from backend.auth import create_access_token

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def auth_headers():
    token = create_access_token({"sub": "admin@querydesk.io", "name": "Alex Admin", "role": "admin"})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
async def client():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

@pytest.mark.anyio
class TestAgentConsole:
    async def test_unauthenticated_agent_tickets_rejected(self, client):
        response = await client.get("/api/agent/tickets")
        assert response.status_code == 401

    async def test_get_agent_tickets_empty_or_list(self, client, auth_headers):
        response = await client.get("/api/agent/tickets", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "tickets" in data
        assert isinstance(data["tickets"], list)

    async def test_agent_takeover(self, client, auth_headers):
        # Create a session first
        await client.post("/api/chat", json={
            "session_id": "test-agent-session-1",
            "message": "I need help with my account",
            "language": "English"
        })

        # Agent takes over
        response = await client.post("/api/agent/takeover", json={
            "session_id": "test-agent-session-1",
            "agent_name": "Agent Marcus"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["agent_name"] == "Agent Marcus"
        assert live_manager.taken_over_sessions.get("test-agent-session-1") == "Agent Marcus"

    async def test_agent_tickets_reflects_takeover(self, client, auth_headers):
        response = await client.get("/api/agent/tickets", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        target = next((t for t in data["tickets"] if t["id"] == "test-agent-session-1"), None)
        assert target is not None
        assert target["taken_over_by"] == "Agent Marcus"

    async def test_instant_connect_agent(self, client):
        response = await client.post("/api/agent/instant-connect", json={
            "session_id": "test-instant-session-2",
            "agent_name": "Sarah Connor"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["agent_name"] == "Sarah Connor"
        assert "welcome_text" in data
        assert live_manager.taken_over_sessions.get("test-instant-session-2") == "Sarah Connor"

    async def test_escalation_triggers_priority_ticket(self, client, auth_headers):
        response = await client.post("/api/chat", json={
            "session_id": "test-escalate-session-3",
            "message": "i am not able to connect to the human agents",
            "language": "English"
        })
        assert response.status_code == 200
        data = response.json()
        assert "Connecting" in data["reply"] or "Live Support" in data["reply"] or data["intent"] == "escalation"

        # Verify ticket in agent queue
        agent_res = await client.get("/api/agent/tickets", headers=auth_headers)
        assert agent_res.status_code == 200
        tickets = agent_res.json().get("tickets", [])
        target = next((t for t in tickets if t["id"] == "test-escalate-session-3"), None)
        assert target is not None
        assert target["escalated"] == 1

    async def test_taken_over_session_auto_response_standby(self, client):
        # When taken over and no human is connected via WS, standby gives an intelligent agent reply
        live_manager.taken_over_sessions["test-standby-session-4"] = "Agent Sarah"
        response = await client.post("/api/chat", json={
            "session_id": "test-standby-session-4",
            "message": "Can you check my return status?",
            "language": "English"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "agent_assisted"
        assert len(data["reply"]) > 0
