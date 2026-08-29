"""Pydantic v2 data models for the Customer Support Chatbot API.

Defines schemas for chat requests, chat responses, feedback, escalation,
analytics, conversation logs, and service health checks.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Payload for incoming customer chat messages."""

    message: str = Field(..., description="User message text", min_length=1)
    session_id: str = Field(..., description="Unique session identifier")
    language: str = Field(default="English", description="User preferred language")
    attachment_info: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional metadata for attached files/images"
    )


class ChatResponse(BaseModel):
    """Response payload returned to customer chat client."""

    reply: str = Field(..., description="Chatbot response text")
    intent: str = Field(..., description="Detected intent tag")
    confidence: float = Field(..., description="Intent classification confidence score")
    sentiment: float = Field(..., description="Compound sentiment score (-1.0 to 1.0)")
    sentiment_label: str = Field(..., description="Categorical sentiment label (positive, neutral, negative)")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Extracted entities from user input")
    suggested_actions: List[str] = Field(
        default_factory=list, description="Recommended next action buttons or quick replies"
    )
    message_id: str = Field(..., description="Unique ID for this response turn")
    products: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Optional recommended product cards or catalog items"
    )


class FeedbackRequest(BaseModel):
    """Payload for user feedback on a chatbot reply."""

    session_id: str = Field(..., description="Session identifier")
    message_id: str = Field(..., description="Message ID being rated")
    rating: Literal["up", "down"] = Field(..., description="User rating (thumbs up or thumbs down)")
    comment: str = Field(default="", description="Optional feedback comments")


class EscalateRequest(BaseModel):
    """Payload to trigger human agent escalation."""

    session_id: str = Field(..., description="Session identifier")
    priority: str = Field(default="normal", description="Escalation priority (low, normal, high, urgent)")
    reason: str = Field(default="", description="Reason for escalation")


class AnalyticsSummary(BaseModel):
    """Aggregated support analytics summary."""

    total_conversations: int = Field(..., description="Total count of customer conversations")
    active_conversations: int = Field(..., description="Currently active conversation sessions")
    resolution_rate: float = Field(..., description="Percentage of conversations resolved without escalation")
    avg_resolution_time_seconds: float = Field(..., description="Average duration of resolved conversations in seconds")
    csat_score: float = Field(..., description="Customer satisfaction score percentage")
    escalation_rate: float = Field(..., description="Percentage of conversations escalated to human agents")
    top_intents: List[Dict[str, Any]] = Field(default_factory=list, description="Top detected intents with frequencies")
    avg_response_latency: float = Field(..., description="Average response generation latency in milliseconds")
    gemini_usage_rate: float = Field(..., description="Percentage of turns handled or augmented by Gemini LLM")


class ConversationTurn(BaseModel):
    """Represents a single message turn in a conversation history."""

    role: str = Field(..., description="Message sender role (user, assistant, system)")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(..., description="ISO 8601 formatted timestamp")
    intent: str = Field(default="", description="Associated intent tag if applicable")
    confidence: float = Field(default=0.0, description="Confidence score")
    sentiment: float = Field(default=0.0, description="Sentiment score")
    message_id: str = Field(default="", description="Unique message identifier")


class HealthResponse(BaseModel):
    """Service health and diagnostic status."""

    status: str = Field(..., description="Overall service status (healthy, degraded, error)")
    nlp_loaded: bool = Field(..., description="Whether NLP and intent models are loaded")
    db_connected: bool = Field(..., description="Whether SQLite database is connected and accessible")
    gemini_available: bool = Field(..., description="Whether Gemini API is configured and operational")
    uptime_seconds: float = Field(..., description="Server uptime in seconds")
