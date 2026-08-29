"""
Unit and integration tests for CSAT 5-Star Survey & Advanced Analytics Reports.
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
class TestCSATAndAnalyticsAPI:
    async def test_csat_submission_and_breakdown(self, client):
        # Submit a 5-star CSAT survey
        res = await client.post("/api/csat/submit", json={
            "session_id": "csat-session-01",
            "rating": 5,
            "categories": ["Fast Resolution", "Accurate Info"],
            "feedback_text": "Super quick response!"
        })
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

        # Fetch CSAT breakdown
        res_breakdown = await client.get("/api/analytics/csat-breakdown")
        assert res_breakdown.status_code == 200
        data = res_breakdown.json()
        assert data["total_surveys"] >= 1
        assert data["average_stars"] >= 1.0
        assert "Fast Resolution" in data["categories"]

    async def test_hourly_traffic_endpoint(self, client):
        res = await client.get("/api/analytics/hourly-traffic")
        assert res.status_code == 200
        data = res.json()
        assert "traffic" in data
        assert isinstance(data["traffic"], list)

    async def test_csat_recent_endpoint(self, client):
        res = await client.get("/api/analytics/csat-recent?limit=5")
        assert res.status_code == 200
        data = res.json()
        assert "surveys" in data
        assert isinstance(data["surveys"], list)
        if len(data["surveys"]) > 0:
            survey = data["surveys"][0]
            assert "rating" in survey
            assert "categories" in survey
            assert "feedback_text" in survey
