"""
Tests for intent classification accuracy.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestIntentClassifier:
    """Tests for semantic intent classification."""

    def setup_method(self):
        from backend.nlp.intent_classifier import IntentClassifier
        self.classifier = IntentClassifier()

    # ---- Order Status ----
    def test_order_status_direct(self):
        intent, conf = self.classifier.classify("Where is my order?")
        assert intent == "order_status", f"Expected order_status, got {intent}"
        assert conf > 0.5

    def test_order_status_paraphrase(self):
        intent, conf = self.classifier.classify("I want to track my package")
        assert intent == "order_status", f"Expected order_status, got {intent}"

    def test_order_status_informal(self):
        intent, conf = self.classifier.classify("when will my stuff arrive")
        assert intent in ("order_status", "shipping_info"), f"Got {intent}"

    # ---- Returns ----
    def test_return_request(self):
        intent, conf = self.classifier.classify("I want to return this item")
        assert intent == "return_request", f"Expected return_request, got {intent}"

    def test_return_policy(self):
        intent, conf = self.classifier.classify("What is your return policy?")
        assert intent == "return_request", f"Expected return_request, got {intent}"

    # ---- Refund ----
    def test_refund_status(self):
        intent, conf = self.classifier.classify("When will I get my refund?")
        assert intent == "refund_status", f"Expected refund_status, got {intent}"

    def test_refund_not_received(self):
        intent, conf = self.classifier.classify("I still haven't received my money back")
        assert intent == "refund_status", f"Expected refund_status, got {intent}"

    # ---- Billing ----
    def test_billing_issue(self):
        intent, conf = self.classifier.classify("I was charged twice for my order")
        assert intent == "billing_issue", f"Expected billing_issue, got {intent}"

    def test_billing_wrong_amount(self):
        intent, conf = self.classifier.classify("The amount on my bill is wrong")
        assert intent == "billing_issue", f"Expected billing_issue, got {intent}"

    # ---- Technical ----
    def test_technical_issue(self):
        intent, conf = self.classifier.classify("The app keeps crashing")
        assert intent == "technical_issue", f"Expected technical_issue, got {intent}"

    def test_technical_website(self):
        intent, conf = self.classifier.classify("Your website isn't loading properly")
        assert intent == "technical_issue", f"Expected technical_issue, got {intent}"

    # ---- Account ----
    def test_account_help(self):
        intent, conf = self.classifier.classify("I can't log in to my account")
        assert intent == "account_help", f"Expected account_help, got {intent}"

    def test_password_reset(self):
        intent, conf = self.classifier.classify("How do I reset my password?")
        assert intent in ("account_help",), f"Got {intent}"

    # ---- Shipping ----
    def test_shipping_info(self):
        intent, conf = self.classifier.classify("How much does shipping cost?")
        assert intent == "shipping_info", f"Expected shipping_info, got {intent}"

    # ---- Cancel ----
    def test_cancel_order(self):
        intent, conf = self.classifier.classify("I want to cancel my order")
        assert intent == "cancel_order", f"Expected cancel_order, got {intent}"

    # ---- Greeting ----
    def test_greeting_hello(self):
        intent, conf = self.classifier.classify("Hello!")
        assert intent == "greeting", f"Expected greeting, got {intent}"

    def test_greeting_hi(self):
        intent, conf = self.classifier.classify("Hi there, I need help")
        assert intent == "greeting", f"Expected greeting, got {intent}"

    # ---- Farewell ----
    def test_farewell(self):
        intent, conf = self.classifier.classify("Thanks, that's all I needed. Bye!")
        assert intent in ("farewell", "positive_feedback"), f"Got {intent}"

    # ---- Escalation ----
    def test_escalation_request(self):
        intent, conf = self.classifier.classify("I want to talk to a real person")
        assert intent == "escalation", f"Expected escalation, got {intent}"

    # ---- Complaint ----
    def test_complaint(self):
        intent, conf = self.classifier.classify("This is the worst service I've ever experienced")
        assert intent == "complaint", f"Expected complaint, got {intent}"

    # ---- Positive ----
    def test_positive_feedback(self):
        intent, conf = self.classifier.classify("You've been so helpful, thank you!")
        assert intent == "positive_feedback", f"Expected positive_feedback, got {intent}"

    # ---- Confidence thresholds ----
    def test_high_confidence_clear_intent(self):
        _, conf = self.classifier.classify("I want to return this product")
        assert conf > 0.5, f"Expected confidence > 0.5, got {conf}"

    def test_low_confidence_ambiguous(self):
        _, conf = self.classifier.classify("asdfghjkl random gibberish xyz")
        assert conf < 0.7, f"Expected low confidence for gibberish, got {conf}"

    # ---- Response retrieval ----
    def test_get_response_valid_intent(self):
        response = self.classifier.get_response("greeting")
        assert isinstance(response, str)
        assert len(response) > 0

    def test_get_response_unknown_intent(self):
        response = self.classifier.get_response("nonexistent_intent")
        assert isinstance(response, str)
