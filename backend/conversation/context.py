import datetime
from typing import List, Dict, Any, Optional

class ConversationContext:
    def __init__(self, session_id: str):
        self.session_id: str = session_id
        self.turns: List[Dict[str, Any]] = []
        self.active_intent: Optional[str] = None
        self.filled_slots: Dict[str, Any] = {}
        self.sentiment_history: List[float] = []
        self.escalated: bool = False
        self.resolved: bool = False
        self.created_at: str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.language: str = "English"
        self.priority: str = "normal"

    def add_turn(self, role: str, content: str, intent: str = '', confidence: float = 0.0, sentiment: float = 0.0, message_id: str = '') -> None:
        turn = {
            "role": role,
            "content": content,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "intent": intent,
            "confidence": confidence,
            "sentiment": sentiment,
            "message_id": message_id
        }
        self.turns.append(turn)
        if len(self.turns) > 50:
            self.turns.pop(0)
        
        self.sentiment_history.append(sentiment)
        if len(self.sentiment_history) > 50:
            self.sentiment_history.pop(0)

    def get_recent_turns(self, n: int = 10) -> List[Dict[str, Any]]:
        return self.turns[-n:]

    def get_sentiment_trajectory(self) -> List[float]:
        return self.sentiment_history

    def reset_intent(self) -> None:
        self.active_intent = None
        self.filled_slots = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "turns": self.turns,
            "turns_count": len(self.turns),
            "active_intent": self.active_intent,
            "filled_slots": self.filled_slots,
            "sentiment_history": self.sentiment_history,
            "escalated": self.escalated,
            "resolved": self.resolved,
            "created_at": self.created_at,
            "language": self.language,
            "priority": self.priority
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationContext':
        ctx = cls(data["session_id"])
        ctx.turns = data.get("turns", [])
        ctx.active_intent = data.get("active_intent")
        ctx.filled_slots = data.get("filled_slots", {})
        ctx.sentiment_history = data.get("sentiment_history", [])
        ctx.escalated = data.get("escalated", False)
        ctx.resolved = data.get("resolved", False)
        ctx.created_at = data.get("created_at", datetime.datetime.now(datetime.timezone.utc).isoformat())
        ctx.language = data.get("language", "English")
        ctx.priority = data.get("priority", "normal")
        return ctx

    def get_context_summary(self) -> str:
        """Generate a concise string representation of the conversation state with recent turns."""
        turns_summary = " ".join([t.get("content", "") for t in self.turns[-5:]])
        return (
            f"Session: {self.session_id} | Intent: {self.active_intent} | "
            f"Slots: {self.filled_slots} | Turns: {len(self.turns)} | "
            f"Recent: {turns_summary} | Escalated: {self.escalated}"
        )
