import logging
import numpy as np
from typing import List, Dict, Any, Optional
from .knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        HAS_SKLEARN = True
    except ImportError:
        HAS_SKLEARN = False

class RAGEngine:
    def __init__(self, knowledge_base: KnowledgeBase):
        self.knowledge_base = knowledge_base
        self.use_tfidf = not HAS_SENTENCE_TRANSFORMERS
        self.model = None
        self.index = None
        self.tfidf_vectorizer = None
        self.tfidf_matrix = None
        
        if not self.use_tfidf:
            try:
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
            except Exception as e:
                logger.error(f"Failed to load SentenceTransformer: {e}")
                self.use_tfidf = True
                
        if self.use_tfidf and HAS_SKLEARN:
            self.tfidf_vectorizer = TfidfVectorizer()
            
        self._query_cache = {}
        self.build_index()

    def build_index(self) -> None:
        texts = self.knowledge_base.get_article_texts()
        if not texts:
            logger.warning("No texts to build index from.")
            return

        if not self.use_tfidf and self.model:
            embeddings = self.model.encode(texts)
            dimension = embeddings.shape[1]
            self.index = faiss.IndexFlatIP(dimension)
            faiss.normalize_L2(embeddings)
            self.index.add(embeddings)
        elif self.use_tfidf and getattr(self, 'tfidf_vectorizer', None):
            self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)

    def rebuild_index(self) -> None:
        self._query_cache.clear()
        self.build_index()

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        cache_key = f"{query.strip().lower()}__top_{top_k}"
        if not hasattr(self, '_query_cache'):
            self._query_cache = {}

        if cache_key in self._query_cache:
            try:
                from backend.telemetry import metrics
                metrics.rag_cache_hits += 1
            except Exception:
                pass
            return self._query_cache[cache_key]

        try:
            from backend.telemetry import metrics
            metrics.rag_cache_misses += 1
        except Exception:
            pass

        articles = self.knowledge_base.get_all_articles()
        if not articles:
            return []

        results = []
        if not self.use_tfidf and self.model and self.index:
            query_emb = self.model.encode([query])
            faiss.normalize_L2(query_emb)
            distances, indices = self.index.search(query_emb, top_k)
            for i, idx in enumerate(indices[0]):
                if 0 <= idx < len(articles):
                    results.append({"article": articles[idx], "score": float(distances[0][i])})
        elif self.use_tfidf and getattr(self, 'tfidf_vectorizer', None) and self.tfidf_matrix is not None:
            query_vec = self.tfidf_vectorizer.transform([query])
            sim = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
            top_indices = sim.argsort()[-top_k:][::-1]
            for idx in top_indices:
                if sim[idx] > 0:
                    results.append({"article": articles[idx], "score": float(sim[idx])})

        # Cache top queries (limit cache size to 500)
        if len(self._query_cache) > 500:
            self._query_cache.pop(next(iter(self._query_cache)))
        self._query_cache[cache_key] = results

        return results

    def get_best_match(self, query: str, threshold: float = 0.12) -> Optional[Dict[str, Any]]:
        """Retrieve the top matching article and relevance score."""
        results = self.search(query, top_k=1)
        if results and results[0]["score"] >= threshold:
            return results[0]
        return None

    def get_best_answer(self, query: str, threshold: float = 0.15) -> Optional[str]:
        match = self.get_best_match(query, threshold)
        if match:
            return match["article"].get("content")
        return None
