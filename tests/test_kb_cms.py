"""
Unit and integration tests for Knowledge Base CMS and AI Article Generator.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.kb_cms_service import KBCMSService
from backend.knowledge.knowledge_base import KnowledgeBase
from backend.knowledge.rag_engine import RAGEngine
from httpx import AsyncClient, ASGITransport
from backend.app import app

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def kb_cms():
    kb = KnowledgeBase()
    rag = RAGEngine(kb)
    return KBCMSService(kb, rag)

@pytest.fixture
async def client():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

def test_article_crud(kb_cms):
    # Create article
    art = kb_cms.create_article("Warranty Policy 2026", "All electronic goods have a 2-year warranty.", category="Warranty")
    assert art["title"] == "Warranty Policy 2026"
    assert "Warranty" in art["category"]

    # Read/List
    articles = kb_cms.list_articles(search="Warranty Policy 2026")
    assert len(articles) >= 1

    # Update
    updated = kb_cms.update_article(art["id"], {"title": "Extended Warranty Policy 2026"})
    assert updated["title"] == "Extended Warranty Policy 2026"

    # Delete
    deleted = kb_cms.delete_article(art["id"])
    assert deleted is True

def test_ai_article_generator_fallback(kb_cms):
    generated = kb_cms.generate_ai_article("Drone Repair & Calibration", category="Repairs")
    assert "Drone Repair" in generated["title"]
    assert "Overview" in generated["content"]
    # Clean up test article
    kb_cms.delete_article(generated["id"])

@pytest.mark.anyio
class TestKBCMSAPI:
    async def test_kb_api_endpoints(self, client):
        # List
        res = await client.get("/api/kb/articles")
        assert res.status_code == 200
        data = res.json()
        assert "articles" in data

        # AI Generate
        res_gen = await client.post("/api/kb/generate-ai", json={
            "topic": "Smart Watch Battery Replacement",
            "category": "Hardware"
        })
        assert res_gen.status_code == 200
        gen_data = res_gen.json()
        assert "article" in gen_data
        art_id = gen_data["article"]["id"]

        # Delete
        res_del = await client.delete(f"/api/kb/articles/{art_id}")
        assert res_del.status_code == 200
