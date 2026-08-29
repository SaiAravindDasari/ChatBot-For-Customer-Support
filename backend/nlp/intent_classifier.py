import json
import logging
import random
from typing import Tuple, List, Dict, Any Optional
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity as st_cosine_similarity
except ImportError:
    SentenceTransformer = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    TfidfVectorizer = None

from pathlib import Path
from .preprocessor import TextPreprocessor

logger = logging.getLogger(__name__)

class IntentClassifier:
    def __init__(self, intents_path: Optional[str] = None):
        self.preprocessor = TextPreprocessor()
        if not intents_path:
            intents_path = str(Path(__file__).parent.parent / "data" / "intents.json")
        self.intents_data = self._load_intents(intents_path)
        
        self.mode = "transformer"
        self.model = None
        self.tfidf = None
        
        self.pattern_vectors = None
        self.pattern_tags = []
        
        if SentenceTransformer:
            try:
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                self._encode_patterns_transformer()
                logger.info("Initialized SentenceTransformer intent classifier.")
            except Exception as e:
                logger.error(f"Error loading SentenceTransformer: {e}")
                self._fallback_to_tfidf()
        else:
            self._fallback_to_tfidf()

    def _load_intents(self, path: str) -> List[Dict[str, Any]]:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('intents', [])
        except Exception as e:
            logger.error(f"Failed to load intents from {path}: {e}")
            return []

    def _fallback_to_tfidf(self):
        self.mode = "tfidf"
        if TfidfVectorizer is None:
            logger.error("TfidfVectorizer is not available.")
            return
        
        self.tfidf = TfidfVectorizer()
        self._encode_patterns_tfidf()
        logger.info("Initialized TF-IDF intent classifier.")

    def _encode_patterns_transformer(self):
        patterns = []
        self.pattern_tags = []
        for intent in self.intents_data:
            tag = intent.get('tag')
            for pattern in intent.get('patterns', []):
                cleaned = self.preprocessor.full_preprocess(pattern)
                patterns.append(cleaned)
                self.pattern_tags.append(tag)
        
        if patterns:
            self.pattern_vectors = self.model.encode(patterns)

    def _encode_patterns_tfidf(self):
        patterns = []
        self.pattern_tags = []
        for intent in self.intents_data:
            tag = intent.get('tag')
            for pattern in intent.get('patterns', []):
                cleaned = self.preprocessor.full_preprocess(pattern)
                patterns.append(cleaned)
                self.pattern_tags.append(tag)
                
        if patterns:
            self.pattern_vectors = self.tfidf.fit_transform(patterns)

    def classify(self, text: str) -> Tuple[str, float]:
        if not self.pattern_tags:
            return ('unknown', 0.0)
            
        cleaned = self.preprocessor.full_preprocess(text)
        
        if self.mode == "transformer" and self.model:
            text_vector = self.model.encode([cleaned])
            similarities = st_cosine_similarity(text_vector, self.pattern_vectors)[0]
        elif self.mode == "tfidf" and self.tfidf:
            text_vector = self.tfidf.transform([cleaned])
            similarities = cosine_similarity(text_vector, self.pattern_vectors)[0]
        else:
            return ('unknown', 0.0)
            
        best_index = np.argmax(similarities)
        best_score = float(similarities[best_index])
        
        if best_score < 0.3:
            return ('unknown', 0.0)
            
        return (self.pattern_tags[best_index], best_score)

    def get_response(self, intent_tag: str) -> str:
        for intent in self.intents_data:
            if intent.get('tag') == intent_tag:
                responses = intent.get('responses', [])
                if responses:
                    return random.choice(responses)
        return ""

    def test(self):
        test_phrases = [
            "I want to return my item", "how do I talk to a human?",
            "my order is missing", "cancel my subscription", "you guys are awful"
        ]
        logger.info("Testing intent classifier:")
        for phrase in test_phrases:
            tag, score = self.classify(phrase)
            logger.info(f"'{phrase}' -> {tag} (confidence: {score:.2f})")
