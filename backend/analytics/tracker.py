import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

class AnalyticsTracker:
    def __init__(self, db_manager: Any):
        """
        Initialize AnalyticsTracker.
        
        Args:
            db_manager: Reference to the DatabaseManager instance.
        """
        self.db_manager = db_manager

    async def track_conversation_started(self, session_id: str) -> None:
        """Track when a conversation is started."""
        await self.db_manager.log_event('conversation_started', session_id, {})

    async def track_message_sent(self, session_id: str, role: str, intent: str, confidence: float, sentiment: float, response_source: str) -> None:
        """Track when a message is sent."""
        data = {
            'role': role,
            'intent': intent,
            'confidence': confidence,
            'sentiment': sentiment,
            'response_source': response_source
        }
        await self.db_manager.log_event('message_sent', session_id, data)

    async def track_intent_missed(self, session_id: str, message: str, confidence: float) -> None:
        """Track when an intent prediction falls below a confidence threshold."""
        data = {
            'message': message,
            'confidence': confidence
        }
        await self.db_manager.log_event('intent_missed', session_id, data)

    async def track_escalation(self, session_id: str, reason: str, priority: str) -> None:
        """Track when a conversation is escalated to a human agent."""
        data = {
            'reason': reason,
            'priority': priority
        }
        await self.db_manager.log_event('escalation', session_id, data)

    async def track_resolution(self, session_id: str) -> None:
        """Track when a conversation is successfully resolved."""
        await self.db_manager.log_event('resolution', session_id, {})

    async def track_feedback(self, session_id: str, message_id: str, rating: str) -> None:
        """Track user feedback on a message."""
        data = {
            'message_id': message_id,
            'rating': rating
        }
        await self.db_manager.log_event('feedback', session_id, data)

    async def track_gemini_usage(self, session_id: str, tokens_used: int) -> None:
        """Track the number of tokens used by Gemini API."""
        data = {
            'tokens_used': tokens_used
        }
        await self.db_manager.log_event('gemini_usage', session_id, data)

    async def track_response_time(self, session_id: str, latency_seconds: float) -> None:
        """Track response latency for system replies."""
        data = {
            'latency_seconds': latency_seconds
        }
        await self.db_manager.log_event('response_time', session_id, data)
