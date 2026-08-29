"""
Knowledge Base CMS & AI Article Generation Service for QueryDesk.
Provides CRUD article management, dynamic vector RAG index rebuilding,
and automated AI article generation.
"""

import json
import logging
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from backend.knowledge.knowledge_base import KnowledgeBase
from backend.knowledge.rag_engine import RAGEngine

logger = logging.getLogger(__name__)

class KBCMSService:
    def __init__(self, kb: KnowledgeBase, rag_engine: Optional[RAGEngine] = None, gemini_client: Optional[Any] = None):
        self.kb = kb
        self.rag_engine = rag_engine
        self.gemini_client = gemini_client
        self.data_path = Path(__file__).parent.parent / 'data' / 'articles.json'

    def _save_to_disk(self) -> None:
        """Persist current articles list to JSON file and rebuild RAG index."""
        try:
            self.data_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump({"articles": self.kb.articles}, f, indent=2)
            self.kb.reload()
            if self.rag_engine:
                self.rag_engine.rebuild_index()
            logger.info("Knowledge Base persisted to disk and RAG index refreshed.")
        except Exception as e:
            logger.error(f"Failed to save articles to disk: {e}")
            raise

    def list_articles(self, search: Optional[str] = None, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """List articles with optional keyword and category filtering."""
        articles = self.kb.get_all_articles()
        if category:
            articles = [a for a in articles if a.get("category", "").lower() == category.lower()]
        if search:
            q = search.lower()
            articles = [
                a for a in articles
                if q in a.get("title", "").lower() or q in a.get("content", "").lower() or any(q in t.lower() for t in a.get("tags", []))
            ]
        return articles

    def create_article(self, title: str, content: str, category: str = "General", tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create and index a new support article."""
        article_id = f"art-{uuid.uuid4().hex[:8]}"
        new_article = {
            "id": article_id,
            "title": title.strip(),
            "category": category.strip(),
            "tags": tags or [category.lower(), "help"],
            "content": content.strip()
        }
        self.kb.articles.append(new_article)
        self._save_to_disk()
        return new_article

    def update_article(self, article_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing article and update vector index."""
        for i, a in enumerate(self.kb.articles):
            if a.get("id") == article_id:
                if "title" in updates:
                    a["title"] = updates["title"].strip()
                if "content" in updates:
                    a["content"] = updates["content"].strip()
                if "category" in updates:
                    a["category"] = updates["category"].strip()
                if "tags" in updates:
                    a["tags"] = updates["tags"]
                self.kb.articles[i] = a
                self._save_to_disk()
                return a
        return None

    def delete_article(self, article_id: str) -> bool:
        """Delete an article from the knowledge base."""
        original_len = len(self.kb.articles)
        self.kb.articles = [a for a in self.kb.articles if a.get("id") != article_id]
        if len(self.kb.articles) < original_len:
            self._save_to_disk()
            return True
        return False

    def generate_ai_article(self, topic: str, category: str = "Support") -> Dict[str, Any]:
        """Generate a complete structured support article using Gemini AI with fallback."""
        if self.gemini_client and hasattr(self.gemini_client, 'is_available') and self.gemini_client.is_available():
            try:
                prompt = (
                    f"Write a comprehensive customer support knowledge base article about: '{topic}'. "
                    f"Format in clear markdown with an Overview, Step-by-Step Instructions, and FAQ. "
                    f"Return in category '{category}'."
                )
                response = self.gemini_client.client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt
                )
                if response and response.text:
                    return self.create_article(
                        title=f"Guide: {topic.title()}",
                        content=response.text,
                        category=category,
                        tags=[category.lower(), "ai-generated", topic.lower().split()[0]]
                    )
            except Exception as e:
                logger.warning(f"Gemini article generator failed: {e}. Using structured builder.")

        # Structured template fallback
        content = (
            f"## Overview: {topic.title()}\n\n"
            f"This guide provides official QueryDesk policies and step-by-step resolution for **{topic}**.\n\n"
            f"### Key Steps & Solutions:\n"
            f"1. **Verification**: Check your account dashboard or order confirmation email for reference numbers.\n"
            f"2. **Action Requirements**: Ensure all relevant documentation (receipts or screenshots) are prepared.\n"
            f"3. **Resolution Timeline**: Most requests regarding {topic} are resolved within 24–48 hours.\n\n"
            f"### Frequently Asked Questions:\n"
            f"- **Q: Who do I contact for urgent escalation?**\n"
            f"  **A:** You can request live human agent handover directly in the chat at any time.\n"
            f"- **Q: Are there additional processing fees?**\n"
            f"  **A:** No, standard QueryDesk support and return label generation are complimentary."
        )
        return self.create_article(
            title=f"Guide: {topic.title()}",
            content=content,
            category=category,
            tags=[category.lower(), "guide", "faq"]
        )
