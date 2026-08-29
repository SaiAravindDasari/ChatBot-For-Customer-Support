"""
Unit and integration tests for Multi-Modal Vision & Document Analysis Service.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.vision_service import VisionService
from httpx import AsyncClient, ASGITransport
from backend.app import app

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def vision():
    return VisionService()

@pytest.fixture
async def client():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

def test_analyze_receipt_heuristic(vision):
    sample_invoice = b"Invoice #QD-5678 Total Amount: $129.99 Date: 2026-08-19"
    result = vision.analyze_document("invoice_5678.pdf", sample_invoice, mime_type="application/pdf")
    assert result["success"] is True
    assert result["order_id"] == "#QD-5678"
    assert result["detected_amount"] == "$129.99"
    assert result["is_damaged"] is False

def test_analyze_damaged_item_photo(vision):
    sample_img = b"JPEG_DATA_DAMAGE_CRACKED_SCREEN"
    result = vision.analyze_document("damaged_screen_photo.jpg", sample_img, mime_type="image/jpeg")
    assert result["success"] is True
    assert result["is_damaged"] is True
    assert "damaged" in result["description"].lower() or "damage" in result["description"].lower()

@pytest.mark.anyio
class TestVisionAPI:
    async def test_upload_and_analyze_endpoint(self, client):
        files = {
            "file": ("order_receipt_QD-1234.png", b"ORDER ID #QD-1234 TOTAL: $49.99", "image/png")
        }
        response = await client.post("/api/upload/analyze", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["order_id"] == "#QD-1234"
