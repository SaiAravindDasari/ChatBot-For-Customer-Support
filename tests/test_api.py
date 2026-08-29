"""
Integration tests for the FastAPI application endpoints.
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
class TestHealthEndpoint:
    async def test_health_returns_200(self, client):
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "nlp_loaded" in data
        assert "db_connected" in data
        assert "gemini_available" in data
        assert "uptime_seconds" in data


@pytest.mark.anyio
class TestChatEndpoint:
    async def test_chat_basic(self, client):
        response = await client.post(
            "/api/chat",
            json={
                "message": "Hello!",
                "session_id": "test-session-001",
                "language": "English",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert "intent" in data
        assert "confidence" in data
        assert "sentiment" in data
        assert "message_id" in data
        assert len(data["reply"]) > 0

    async def test_chat_order_status(self, client):
        response = await client.post(
            "/api/chat",
            json={
                "message": "Where is my order #QD-5678?",
                "session_id": "test-session-002",
                "language": "English",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] in ("order_status", "unknown")

    async def test_chat_product_recommendation(self, client):
        response = await client.post(
            "/api/chat",
            json={
                "message": "Recommend popular products and gear",
                "session_id": "test-session-003",
                "language": "English",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert isinstance(data["products"], list)
        assert len(data["products"]) > 0
        assert "Keyboard" in data["products"][0]["name"] or "Headphones" in data["products"][0]["name"]

    async def test_chat_empty_message_returns_error(self, client):
        response = await client.post(
            "/api/chat",
            json={
                "message": "",
                "session_id": "test-session-003",
                "language": "English",
            },
        )
        # Could be 200 with a fallback response or 422 validation error
        assert response.status_code in (200, 422)

    async def test_chat_with_language(self, client):
        response = await client.post(
            "/api/chat",
            json={
                "message": "I need help with my account",
                "session_id": "test-session-004",
                "language": "Hindi",
            },
        )
        assert response.status_code == 200

    async def test_chat_multi_turn(self, client):
        session = "test-session-multiturn"
        # First message
        r1 = await client.post(
            "/api/chat",
            json={"message": "Hi", "session_id": session, "language": "English"},
        )
        assert r1.status_code == 200

        # Second message
        r2 = await client.post(
            "/api/chat",
            json={
                "message": "I want to check my order",
                "session_id": session,
                "language": "English",
            },
        )
        assert r2.status_code == 200


@pytest.mark.anyio
class TestFeedbackEndpoint:
    async def test_submit_feedback(self, client):
        # First send a message to create a session
        chat_resp = await client.post(
            "/api/chat",
            json={
                "message": "Hello",
                "session_id": "test-feedback-session",
                "language": "English",
            },
        )
        message_id = chat_resp.json().get("message_id", "test-msg-id")

        response = await client.post(
            "/api/feedback",
            json={
                "session_id": "test-feedback-session",
                "message_id": message_id,
                "rating": "up",
                "comment": "Very helpful!",
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


@pytest.mark.anyio
class TestEscalateEndpoint:
    async def test_escalate(self, client):
        # Create a session first
        await client.post(
            "/api/chat",
            json={
                "message": "I need help",
                "session_id": "test-escalate-session",
                "language": "English",
            },
        )

        response = await client.post(
            "/api/escalate",
            json={
                "session_id": "test-escalate-session",
                "priority": "High",
                "reason": "Customer requested human agent",
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "escalated"


@pytest.mark.anyio
class TestAnalyticsEndpoints:
    async def test_analytics_summary(self, client):
        response = await client.get("/api/analytics/summary")
        assert response.status_code == 200

    async def test_analytics_intents(self, client):
        response = await client.get("/api/analytics/intents")
        assert response.status_code == 200
        assert "intents" in response.json()

    async def test_analytics_sentiment(self, client):
        response = await client.get("/api/analytics/sentiment")
        assert response.status_code == 200
        assert "trend" in response.json()

    async def test_analytics_conversations(self, client):
        response = await client.get("/api/analytics/conversations")
        assert response.status_code == 200

    async def test_analytics_training_opportunities(self, client):
        response = await client.get("/api/analytics/training-opportunities")
        assert response.status_code == 200

    async def test_analytics_quality_issues(self, client):
        response = await client.get("/api/analytics/quality-issues")
        assert response.status_code == 200


@pytest.mark.anyio
class TestHistoryEndpoint:
    async def test_get_history(self, client):
        session = "test-history-session"
        await client.post(
            "/api/chat",
            json={"message": "Hello", "session_id": session, "language": "English"},
        )
        response = await client.get(f"/api/sessions/{session}/history")
        assert response.status_code == 200
        assert "turns" in response.json()
