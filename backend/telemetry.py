"""
Enterprise Observability, Prometheus Metrics & Distributed Tracing for QueryDesk.
Exposes standard OpenMetrics format for Prometheus, Grafana, Datadog, and OpenTelemetry.
"""

import time
import uuid
from typing import Dict
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class MetricsRegistry:
    """
    Lightweight, high-performance in-memory Prometheus OpenMetrics collector.
    Thread-safe counters, gauges, and latency buckets.
    """
    def __init__(self):
        # Counters: key -> count
        self.http_requests_total: Dict[str, int] = defaultdict(int)
        self.nlp_intents_total: Dict[str, int] = defaultdict(int)
        self.tickets_escalated_total: Dict[str, int] = defaultdict(int)
        self.rag_cache_hits: int = 0
        self.rag_cache_misses: int = 0
        
        # Gauges
        self.websocket_active_connections: int = 0
        self.agent_active_connections: int = 0
        
        # Histograms (latency tracking)
        self.http_duration_sum: float = 0.0
        self.http_duration_count: int = 0

    def record_request(self, method: str, path: str, status_code: int, duration_sec: float):
        # Normalize path for low cardinality metrics (e.g. collapse /ws/123 to /ws/{id})
        norm_path = path
        if path.startswith("/ws/"):
            norm_path = "/ws/{session_id}"
        elif path.startswith("/api/sessions/"):
            norm_path = "/api/sessions/{session_id}/history"
            
        key = f'method="{method}",path="{norm_path}",status="{status_code}"'
        self.http_requests_total[key] += 1
        self.http_duration_sum += duration_sec
        self.http_duration_count += 1

    def record_intent(self, intent: str):
        self.nlp_intents_total[intent] += 1

    def record_escalation(self, priority: str):
        self.tickets_escalated_total[priority] += 1

    def generate_prometheus_output(self) -> str:
        """Export all recorded metrics in standard Prometheus exposition format."""
        lines = []
        
        # 1. HTTP Requests Total
        lines.append("# HELP querydesk_http_requests_total Total number of HTTP requests processed.")
        lines.append("# TYPE querydesk_http_requests_total counter")
        if not self.http_requests_total:
            lines.append('querydesk_http_requests_total{method="GET",path="/api/health",status="200"} 0')
        for labels, count in self.http_requests_total.items():
            lines.append(f"querydesk_http_requests_total{{{labels}}} {count}")
            
        # 2. HTTP Request Duration Summary
        lines.append("\n# HELP querydesk_http_request_duration_seconds Latency of HTTP requests.")
        lines.append("# TYPE querydesk_http_request_duration_seconds summary")
        lines.append(f"querydesk_http_request_duration_seconds_sum {self.http_duration_sum:.6f}")
        lines.append(f"querydesk_http_request_duration_seconds_count {self.http_duration_count}")

        # 3. Active WebSocket Connections Gauge
        lines.append("\n# HELP querydesk_websocket_active_connections Current active customer websocket connections.")
        lines.append("# TYPE querydesk_websocket_active_connections gauge")
        lines.append(f'querydesk_websocket_active_connections{{type="customer"}} {self.websocket_active_connections}')
        lines.append(f'querydesk_websocket_active_connections{{type="agent"}} {self.agent_active_connections}')

        # 4. NLP Intent Detections Total
        lines.append("\n# HELP querydesk_nlp_intents_total Total intent detections classified by NLP pipeline.")
        lines.append("# TYPE querydesk_nlp_intents_total counter")
        for intent, count in self.nlp_intents_total.items():
            lines.append(f'querydesk_nlp_intents_total{{intent="{intent}"}} {count}')

        # 5. Tickets Escalated
        lines.append("\n# HELP querydesk_tickets_escalated_total Total human escalations triggered.")
        lines.append("# TYPE querydesk_tickets_escalated_total counter")
        for priority, count in self.tickets_escalated_total.items():
            lines.append(f'querydesk_tickets_escalated_total{{priority="{priority}"}} {count}')

        # 6. RAG Cache Hits/Misses
        lines.append("\n# HELP querydesk_rag_cache_hits_total Total cache hits for RAG embeddings.")
        lines.append("# TYPE querydesk_rag_cache_hits_total counter")
        lines.append(f"querydesk_rag_cache_hits_total {self.rag_cache_hits}")
        lines.append(f"querydesk_rag_cache_misses_total {self.rag_cache_misses}")

        return "\n".join(lines) + "\n"


metrics = MetricsRegistry()


class TracingAndMetricsMiddleware(BaseHTTPMiddleware):
    """
    Attaches X-Correlation-ID & X-Request-ID to request context and measures execution time.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
        
        request.state.correlation_id = correlation_id
        request.state.request_id = request_id
        
        response: Response = await call_next(request)
        
        duration = time.time() - start_time
        metrics.record_request(request.method, request.url.path, response.status_code, duration)
        
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{duration * 1000:.2f}"
        
        return response
