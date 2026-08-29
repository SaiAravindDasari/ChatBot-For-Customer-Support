from dataclasses import dataclass
from typing import Dict, Any
import logging

from .preprocessor import TextPreprocessor
from .intent_classifier import IntentClassifier
from .entity_extractor import EntityExtractor
from .sentiment import SentimentAnalyzer

logger = logging.getLogger(__name__)

@dataclass
class NLPResult:
    intent: str
    confidence: float
    entities: dict
    sentiment: float
    sentiment_label: str
    preprocessed_text: str
    language_detected: str
    frustration_level: str
    suggested_response: str

class NLPPipeline:
    def __init__(self):
        logger.info("Initializing NLP Pipeline...")
        self.preprocessor = TextPreprocessor()
        self.intent_classifier = IntentClassifier()
        self.entity_extractor = EntityExtractor()
        self.sentiment_analyzer = SentimentAnalyzer()
        self._ready = True
        logger.info("NLP Pipeline initialized successfully.")

    def analyze(self, text: str) -> NLPResult:
        cleaned = self.preprocessor.full_preprocess(text)
        lang = self.preprocessor.detect_language(text)
        
        intent, conf = self.intent_classifier.classify(text)
        entities = self.entity_extractor.extract_all(text)
        
        sentiment_score, sentiment_label = self.sentiment_analyzer.analyze(text)
        frustration = self.sentiment_analyzer.get_frustration_level(text)
        
        response = ""
        if conf >= 0.3 and intent != 'unknown':
            response = self.intent_classifier.get_response(intent)
            
        return NLPResult(
            intent=intent,
            confidence=conf,
            entities=entities,
            sentiment=sentiment_score,
            sentiment_label=sentiment_label,
            preprocessed_text=cleaned,
            language_detected=lang,
            frustration_level=frustration,
            suggested_response=response
        )

    def is_ready(self) -> bool:
        return self._ready
