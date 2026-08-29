"""
Unit and Integration tests for the CRM & Helpdesk Integration Service.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.crm_service import CRMService
from httpx import AsyncClient, ASGITransport
from backend.app import app

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def crm():
    return CRMService()

@pytest.fixture
async def client():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

def test_zendesk_export_schema(crm):
    messages = [
        {"role": "user", "content": "I was double charged on my card"},
        {"role": "assistant", "content": "Let me look up your billing transaction"}
    ]
    ticket = crm.export_zendesk_ticket("session-12345", messages, priority="high", language="en")
    assert "ticket" in ticket
    assert "QueryDesk Escalation" in ticket["ticket"]["subject"]
    assert ticket["ticket"]["priority"] == "urgent"
    assert "double charged" in ticket["ticket"]["comment"]["body"]
    assert "querydesk_ai" in ticket["ticket"]["tags"]

def test_jira_export_schema(crm):
    messages = [
        {"role": "user", "content": "The website gives error 500"},
        {"role": "assistant", "content": "Checking our server status"}
    ]
    issue = crm.export_jira_issue("session-jira-99", messages, priority="critical")
    assert "fields" in issue
    assert issue["fields"]["project"]["key"] == "SUP"
    assert issue["fields"]["priority"]["name"] == "High"
    assert "error 500" in str(issue["fields"]["description"])

def test_freshdesk_export_schema(crm):
    messages = [{"role": "user", "content": "Where is my package?"}]
    fd = crm.export_freshdesk_ticket("session-fd-77", messages, priority="low")
    assert "subject" in fd
    assert fd["priority"] == 2
    assert "package" in fd["description"]

def test_webhook_hmac_signing(crm):
    payload = b'{"event":"test"}'
    secret = "test-secret"
    sig = crm.sign_webhook_payload(payload, secret)
    assert sig.startswith("sha256=")
    assert len(sig) == 7 + 64

@pytest.mark.anyio
class TestCRMAPI:
    async def test_crm_sync_ticket(self, client):
        # Create a conversation turn first
        await client.post("/api/chat", json={
            "session_id": "crm-test-session",
            "message": "I need help with my billing invoice",
            "language": "English"
        })

        # Sync to Zendesk
        response = await client.post("/api/crm/sync-ticket", json={
            "session_id": "crm-test-session",
            "provider": "zendesk"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "synced"
        assert data["provider"] == "zendesk"
        assert data["external_ticket_id"].startswith("ZENDESK-")

    async def test_crm_export_ticket(self, client):
        response = await client.get("/api/crm/export/crm-test-session?format=jira")
        assert response.status_code == 200
        data = response.json()
        assert "fields" in data
        assert "crm-test-session" in str(data)

    async def test_crm_webhooks_list(self, client):
        response = await client.get("/api/crm/webhooks")
        assert response.status_code == 200
        data = response.json()
        assert "webhooks" in data
        assert len(data["webhooks"]) > 0
