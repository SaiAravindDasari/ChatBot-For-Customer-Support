"""
Unit and Integration tests for Observability, Prometheus Metrics, and Health Probes.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.telemetry import metrics
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
class TestTelemetry:
    async def test_liveness_probe(self, client):
        response = await client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "live"

    async def test_readiness_probe(self, client):
        response = await client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["db"] is True
        assert data["nlp"] is True

    async def test_prometheus_metrics_endpoint(self, client):
        # Trigger a request to populate metrics
        await client.get("/api/health")
        
        response = await client.get("/metrics")
        assert response.status_code == 200
        text = response.text
        assert "querydesk_http_requests_total" in text
        assert "querydesk_websocket_active_connections" in text
        assert "querydesk_nlp_intents_total" in text
