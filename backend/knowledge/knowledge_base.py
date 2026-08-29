import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class KnowledgeBase:
    def __init__(self):
        self.articles = []
        self.data_path = Path(__file__).parent.parent / 'data' / 'articles.json'
        self.reload()

    def reload(self) -> None:
        try:
            if self.data_path.exists():
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # Handle both {"articles": [...]} and plain [...] formats
                if isinstance(data, dict) and "articles" in data:
                    self.articles = data["articles"]
                elif isinstance(data, list):
                    self.articles = data
                else:
                    logger.warning("Unexpected articles.json format")
                    self.articles = []
                logger.info(f"Loaded {len(self.articles)} knowledge base articles")
            else:
                logger.warning(f"Articles file not found: {self.data_path}")
                self.articles = []
        except Exception as e:
            logger.error(f"Error loading articles: {e}")
            self.articles = []

    def get_all_articles(self) -> List[Dict[str, Any]]:
        return self.articles

    def get_by_category(self, category: str) -> List[Dict[str, Any]]:
        return [a for a in self.articles if a.get("category") == category]

    def get_by_id(self, article_id: str) -> Optional[Dict[str, Any]]:
        for a in self.articles:
            if a.get("id") == article_id:
                return a
        return None

    def search_by_tags(self, tags: List[str]) -> List[Dict[str, Any]]:
        results = []
        for a in self.articles:
            a_tags = set(a.get("tags", []))
            if any(t in a_tags for t in tags):
                results.append(a)
        return results

    def get_article_texts(self) -> List[str]:
        texts = []
        for a in self.articles:
            title = a.get("title", "")
            category = a.get("category", "")
            tags = " ".join(a.get("tags", []))
            content = a.get("content", "")
            combined = f"{title}. {category}. {tags}. {content}".strip()
            texts.append(combined if combined else content)
        return texts

    def get_article_titles(self) -> List[str]:
        return [a.get("title", "") for a in self.articles]
