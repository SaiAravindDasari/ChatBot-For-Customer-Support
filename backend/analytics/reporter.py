from typing import Any, Dict, List

class AnalyticsReporter:
    def __init__(self, db_manager: Any):
        """
        Initialize AnalyticsReporter.
        
        Args:
            db_manager: Reference to the DatabaseManager instance.
        """
        self.db_manager = db_manager

    async def get_summary(self) -> Dict[str, Any]:
        """Get aggregated metrics for the overall chatbot performance."""
        return await self.db_manager.get_analytics_summary()

    async def get_intent_distribution(self) -> List[Dict[str, Any]]:
        """Get the distribution of detected intents."""
        return await self.db_manager.get_intent_distribution()

    async def get_sentiment_trend(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get the trend of user sentiment over the specified number of days."""
        return await self.db_manager.get_sentiment_trend(days)

    async def get_recent_conversations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recently updated conversations."""
        return await self.db_manager.get_recent_conversations(limit)

    async def get_training_opportunities(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get low confidence queries for further model training."""
        return await self.db_manager.get_low_confidence_queries(threshold=0.5, limit=limit)

    async def get_quality_issues(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get negative feedback on chatbot responses to address quality issues."""
        return await self.db_manager.get_negative_feedback(limit)
