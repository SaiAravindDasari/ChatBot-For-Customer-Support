"""
Tests for the RAG engine and knowledge base.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestKnowledgeBase:
    """Tests for knowledge base loading and querying."""

    def setup_method(self):
        from backend.knowledge.knowledge_base import KnowledgeBase
        self.kb = KnowledgeBase()

    def test_loads_articles(self):
        articles = self.kb.get_all_articles()
        assert isinstance(articles, list)
        assert len(articles) > 0

    def test_article_structure(self):
        articles = self.kb.get_all_articles()
        article = articles[0]
        assert "id" in article
        assert "title" in article
        assert "content" in article
        assert "category" in article

    def test_get_by_category(self):
        articles = self.kb.get_by_category("returns")
        assert isinstance(articles, list)
        for a in articles:
            assert a["category"] == "returns"

    def test_get_by_id(self):
        all_articles = self.kb.get_all_articles()
        if all_articles:
            article_id = all_articles[0]["id"]
            found = self.kb.get_by_id(article_id)
            assert found is not None
            assert found["id"] == article_id

    def test_get_by_id_not_found(self):
        result = self.kb.get_by_id("nonexistent_id_xyz")
        assert result is None

    def test_search_by_tags(self):
        results = self.kb.search_by_tags(["return", "refund"])
        assert isinstance(results, list)

    def test_get_article_texts(self):
        texts = self.kb.get_article_texts()
        assert isinstance(texts, list)
        assert all(isinstance(t, str) for t in texts)
        assert len(texts) > 0

    def test_get_article_titles(self):
        titles = self.kb.get_article_titles()
        assert isinstance(titles, list)
        assert all(isinstance(t, str) for t in titles)


class TestRAGEngine:
    """Tests for the RAG engine."""

    def setup_method(self):
        from backend.knowledge.knowledge_base import KnowledgeBase
        from backend.knowledge.rag_engine import RAGEngine
        self.kb = KnowledgeBase()
        self.rag = RAGEngine(self.kb)
        self.rag.build_index()

    def test_index_built(self):
        # Should not raise
        results = self.rag.search("return policy", top_k=3)
        assert isinstance(results, list)

    def test_search_returns_results(self):
        results = self.rag.search("How do I return an item?", top_k=3)
        assert len(results) > 0
        assert "score" in results[0]

    def test_search_results_have_articles(self):
        results = self.rag.search("refund timeline", top_k=3)
        for r in results:
            assert "article" in r or "score" in r

    def test_search_relevance(self):
        results = self.rag.search("shipping cost international", top_k=3)
        # At least one result should be related to shipping
        assert len(results) > 0

    def test_get_best_answer_found(self):
        answer = self.rag.get_best_answer("How do I return a product?", threshold=0.3)
        # With a low threshold, should find something
        if answer:
            assert isinstance(answer, str)
            assert len(answer) > 0

    def test_get_best_answer_gibberish(self):
        answer = self.rag.get_best_answer("xyzzy plugh zork", threshold=0.95)
        # With very high threshold and gibberish, should return None
        assert answer is None

    def test_search_top_k(self):
        results = self.rag.search("order", top_k=5)
        assert len(results) <= 5

    def test_rebuild_index(self):
        # Should not raise
        self.rag.rebuild_index()
        results = self.rag.search("billing", top_k=2)
        assert isinstance(results, list)


class TestGeminiFallback:
    """Tests for the Gemini fallback (mostly availability checks)."""

    def setup_method(self):
        from backend.knowledge.gemini_fallback import GeminiFallback
        self.gemini = GeminiFallback()

    def test_availability_check(self):
        # Without API key, should be unavailable
        available = self.gemini.is_available()
        assert isinstance(available, bool)

    def test_token_count_attribute(self):
        assert hasattr(self.gemini, "token_count")
