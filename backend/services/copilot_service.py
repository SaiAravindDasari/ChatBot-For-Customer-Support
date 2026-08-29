"""
AI Agent Copilot & Smart Suggestion Engine for QueryDesk.
Generates context-aware response drafts, conversation intent summaries,
and recommends relevant Knowledge Base articles directly into the Live Agent Console.
"""

import logging
from typing import Dict, Any, List, Optional
from backend.knowledge.rag_engine import RAGEngine

logger = logging.getLogger(__name__)

class CopilotService:
    def __init__(self, rag_engine: Optional[RAGEngine] = None):
        self.rag_engine = rag_engine

    def generate_copilot_assist(
        self,
        session_id: str,
        messages: List[Dict[str, Any]],
        sentiment_score: float = 0.0,
        priority: str = "Medium"
    ) -> Dict[str, Any]:
        """
        Analyze the full conversation context and generate:
        1. Contextual suggested replies for the human agent.
        2. 1-sentence customer sentiment & intent summary.
        3. Recommended Knowledge Base articles to insert with 1 click.
        """
        if not messages:
            return {
                "summary": "New conversation initialized.",
                "suggested_drafts": [
                    "Hello! I am reviewing your inquiry now. How can I best help you today?",
                    "Hi there, thanks for reaching out to QueryDesk support. What issue are you experiencing?"
                ],
                "recommended_articles": []
            }

        last_user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user_msg = m.get("content", "")
                break

        # Sentiment summary
        sentiment_label = "Positive" if sentiment_score > 0.3 else ("Frustrated / Urgent" if sentiment_score < -0.3 else "Neutral")
        summary = f"Customer inquiry regarding: '{last_user_msg[:60]}...' (Mood: {sentiment_label}, Priority: {priority})"

        # Generate contextual drafts based on user inquiry keywords
        lower_msg = last_user_msg.lower()
        drafts = []

        if any(w in lower_msg for w in ["order", "track", "delivery", "where", "shipping"]):
            drafts = [
                "I've pulled up your shipping details. Your package is currently in transit with the carrier and scheduled for on-time delivery.",
                "Could you please confirm your shipping zip code so I can authorize expedited courier tracking?",
                "I have contacted our logistics depot to prioritize your parcel delivery."
            ]
        elif any(w in lower_msg for w in ["return", "refund", "charge", "bill", "money", "damaged"]):
            drafts = [
                "I have approved your return request. A prepaid return shipping label (PDF) has been emailed to you.",
                "I reviewed your billing statement and processed a full credit adjustment to your original payment method.",
                "Please accept our sincere apologies for the item condition. Would you prefer a free replacement or an immediate refund?"
            ]
        elif any(w in lower_msg for w in ["password", "login", "account", "email", "reset"]):
            drafts = [
                "I have sent a secure password reset link to your verified email address.",
                "Your account security settings have been refreshed. Please try signing in now.",
                "I can help unlock your profile. Please check your inbox for a 6-digit confirmation code."
            ]
        else:
            drafts = [
                "Thank you for your patience. I am reviewing your account history to resolve this right away.",
                "Could you provide a few more details so I can ensure we get this sorted out for you?",
                "I've escalated this inquiry to our senior technical tier and will personally track it to completion."
            ]

        # Knowledge Base matches
        recommended_articles = []
        if self.rag_engine and last_user_msg:
            try:
                results = self.rag_engine.search(last_user_msg, top_k=2)
                for res in results:
                    art = res.get("article", {})
                    recommended_articles.append({
                        "title": art.get("title", "Support Guide"),
                        "excerpt": art.get("content", "")[:120] + "...",
                        "full_content": art.get("content", "")
                    })
            except Exception as e:
                logger.warning(f"Error fetching KB suggestions in copilot: {e}")

        return {
            "session_id": session_id,
            "summary": summary,
            "suggested_drafts": drafts,
            "recommended_articles": recommended_articles
        }
