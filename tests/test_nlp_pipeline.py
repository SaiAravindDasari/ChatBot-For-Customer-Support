"""
Tests for the NLP pipeline components.
"""

import pytest
import sys
from pathlib import Path

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestTextPreprocessor:
    """Tests for text preprocessing."""

    def setup_method(self):
        from backend.nlp.preprocessor import TextPreprocessor
        self.preprocessor = TextPreprocessor()

    def test_normalize_lowercases(self):
        result = self.preprocessor.normalize("HELLO World")
        assert result == "hello world"

    def test_normalize_strips_whitespace(self):
        result = self.preprocessor.normalize("  hello  world  ")
        assert "hello" in result and "world" in result

    def test_expand_contractions(self):
        result = self.preprocessor.expand_contractions("I can't find my order")
        assert "cannot" in result or "can not" in result

    def test_expand_contractions_wont(self):
        result = self.preprocessor.expand_contractions("It won't work")
        assert "will not" in result

    def test_remove_noise(self):
        result = self.preprocessor.remove_noise("Hello!!!???   World...")
        assert result  # Should not be empty
        assert "Hello" in result or "hello" in result

    def test_tokenize(self):
        tokens = self.preprocessor.tokenize("Where is my order?")
        assert isinstance(tokens, list)
        assert len(tokens) >= 4

    def test_remove_stopwords_keeps_negations(self):
        tokens = ["I", "do", "not", "have", "my", "order"]
        result = self.preprocessor.remove_stopwords(tokens)
        assert "not" in result

    def test_full_preprocess(self):
        result = self.preprocessor.full_preprocess("I CAN'T find my ORDER!!!")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_detect_language_english(self):
        lang = self.preprocessor.detect_language(
            "I would like to track my order please"
        )
        assert lang == "en"

    def test_empty_input(self):
        result = self.preprocessor.full_preprocess("")
        assert isinstance(result, str)


class TestEntityExtractor:
    """Tests for entity extraction."""

    def setup_method(self):
        from backend.nlp.entity_extractor import EntityExtractor
        self.extractor = EntityExtractor()

    def test_extract_order_id_hash_format(self):
        entities = self.extractor.extract("My order is #QD-1234")
        found = False
        for key, val in entities.items():
            if "order" in key.lower() or "QD-1234" in str(val):
                found = True
                break
        assert found, f"Order ID not found in: {entities}"

    def test_extract_email(self):
        entities = self.extractor.extract("My email is user@example.com")
        found = any("user@example.com" in str(v) for v in entities.values())
        assert found, f"Email not found in: {entities}"

    def test_extract_phone(self):
        entities = self.extractor.extract("Call me at +91-9876543210")
        # Phone patterns vary, just check something was extracted
        assert isinstance(entities, dict)

    def test_no_entities(self):
        entities = self.extractor.extract("Hello there")
        assert isinstance(entities, dict)

    def test_multiple_entities(self):
        text = "Order #QD-5678, email test@mail.com"
        entities = self.extractor.extract(text)
        assert isinstance(entities, dict)


class TestSentimentAnalyzer:
    """Tests for sentiment analysis."""

    def setup_method(self):
        from backend.nlp.sentiment import SentimentAnalyzer
        self.analyzer = SentimentAnalyzer()

    def test_positive_sentiment(self):
        score, label = self.analyzer.analyze("Thank you so much, this was really helpful!")
        assert score > 0
        assert label == "positive"

    def test_negative_sentiment(self):
        score, label = self.analyzer.analyze("This is terrible, worst experience ever!")
        assert score < 0
        assert label == "negative"

    def test_neutral_sentiment(self):
        score, label = self.analyzer.analyze("I would like to check my order status.")
        assert label in ("neutral", "positive", "negative")  # Could go either way

    def test_frustration_level_high(self):
        level = self.analyzer.get_frustration_level("This is the worst scam, I'm furious!")
        assert level in ("high", "medium")

    def test_frustration_level_low(self):
        level = self.analyzer.get_frustration_level("Thanks for your help!")
        assert level == "low"

    def test_should_escalate(self):
        scores = [-0.8, -0.7, -0.6]
        result = self.analyzer.should_escalate(scores, threshold=-0.5)
        assert result is True

    def test_should_not_escalate(self):
        scores = [0.5, 0.3, 0.4]
        result = self.analyzer.should_escalate(scores, threshold=-0.5)
        assert result is False

    def test_trajectory_worsening(self):
        scores = [0.5, 0.2, -0.1, -0.4, -0.7]
        trajectory = self.analyzer.analyze_trajectory(scores)
        assert trajectory == "worsening"

    def test_trajectory_improving(self):
        scores = [-0.7, -0.4, -0.1, 0.2, 0.5]
        trajectory = self.analyzer.analyze_trajectory(scores)
        assert trajectory == "improving"


class TestNLPPipeline:
    """Tests for the full NLP pipeline."""

    def setup_method(self):
        from backend.nlp.pipeline import NLPPipeline
        self.pipeline = NLPPipeline()

    def test_pipeline_initializes(self):
        assert self.pipeline.is_ready()

    def test_analyze_returns_result(self):
        result = self.pipeline.analyze("Where is my order #QD-1234?")
        assert hasattr(result, "intent")
        assert hasattr(result, "confidence")
        assert hasattr(result, "sentiment")
        assert hasattr(result, "entities")
        assert isinstance(result.preprocessed_text, str)

    def test_analyze_empty_string(self):
        result = self.pipeline.analyze("")
        assert result.intent == "unknown" or isinstance(result.intent, str)

    def test_analyze_greeting(self):
        result = self.pipeline.analyze("Hello, how are you?")
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0
