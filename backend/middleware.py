import time
import logging
import json
from collections import defaultdict
from typing import Dict, List

class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int = 60):
        """
        Initialize RateLimiter.
        
        Args:
            max_requests (int): Maximum allowed requests per window.
            window_seconds (int): Time window in seconds.
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = defaultdict(list)

    def check(self, session_id: str) -> bool:
        """
        Check if the session has exceeded the rate limit.
        
        Args:
            session_id (str): The session ID to check.
            
        Returns:
            bool: True if under limit, False if exceeded.
        """
        now = time.time()
        self._cleanup()
        
        reqs = self.requests[session_id]
        if len(reqs) >= self.max_requests:
            return False
            
        reqs.append(now)
        return True

    def _cleanup(self) -> None:
        """Remove expired entries."""
        cutoff = time.time() - self.window_seconds
        for session_id in list(self.requests.keys()):
            self.requests[session_id] = [t for t in self.requests[session_id] if t > cutoff]
            if not self.requests[session_id]:
                del self.requests[session_id]


class RequestLogger:
    def __init__(self):
        """Setup Python logging with structured format."""
        self.logger = logging.getLogger("RequestLogger")
        self.logger.setLevel(logging.INFO)
        # Avoid adding multiple handlers if already configured
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log_request(self, session_id: str, message: str, intent: str, confidence: float, latency_ms: float, response_source: str) -> None:
        """Log structured JSON line for a request."""
        log_entry = {
            "type": "request",
            "session_id": session_id,
            "message": message,
            "intent": intent,
            "confidence": confidence,
            "latency_ms": latency_ms,
            "response_source": response_source,
            "timestamp": time.time()
        }
        self.logger.info(json.dumps(log_entry))

    def log_error(self, session_id: str, error_type: str, details: str) -> None:
        """Log structured JSON line for an error."""
        log_entry = {
            "type": "error",
            "session_id": session_id,
            "error_type": error_type,
            "details": details,
            "timestamp": time.time()
        }
        self.logger.error(json.dumps(log_entry))


class SessionManager:
    def __init__(self, ttl_minutes: int = 30):
        """
        Initialize SessionManager.
        
        Args:
            ttl_minutes (int): Time-to-live for a session in minutes.
        """
        self.ttl_seconds = ttl_minutes * 60
        self.sessions: Dict[str, float] = {}

    def touch(self, session_id: str) -> None:
        """Update last activity timestamp for a session."""
        self.sessions[session_id] = time.time()

    def is_expired(self, session_id: str) -> bool:
        """Check if a session has exceeded its TTL."""
        if session_id not in self.sessions:
            return True
        return (time.time() - self.sessions[session_id]) > self.ttl_seconds

    def cleanup_expired(self) -> list[str]:
        """Return and remove expired session IDs."""
        now = time.time()
        expired = []
        for session_id, last_activity in list(self.sessions.items()):
            if (now - last_activity) > self.ttl_seconds:
                expired.append(session_id)
                del self.sessions[session_id]
        return expired

    def get_active_count(self) -> int:
        """Return count of currently active sessions."""
        self.cleanup_expired()
        return len(self.sessions)
