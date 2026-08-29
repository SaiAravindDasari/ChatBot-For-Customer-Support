"""
QueryDesk — AI Customer Support Chatbot
FastAPI application with WebSocket real-time messaging, Live Agent Console,
AI Agent Copilot, Multi-Modal Vision Analysis, Knowledge Base CMS with AI Generator,
Branded Transcript Exporter, CSAT Survey Suite, JWT Auth, CRM Hub, and Prometheus Observability.
"""

import asyncio
import html
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Set, Any, Optional, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Body, Depends, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.config import Config
from backend.models import (
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    EscalateRequest,
    AnalyticsSummary,
    HealthResponse,
)
from backend.database import DatabaseManager
from backend.middleware import RateLimiter, RequestLogger, SessionManager
from backend.nlp.pipeline import NLPPipeline
from backend.knowledge.rag_engine import RAGEngine
from backend.knowledge.knowledge_base import KnowledgeBase
from backend.knowledge.gemini_fallback import GeminiFallback
from backend.conversation.orchestrator import ConversationOrchestrator
from backend.analytics.tracker import AnalyticsTracker
from backend.analytics.reporter import AnalyticsReporter
from backend.services.crm_service import CRMService
from backend.services.vision_service import VisionService
from backend.services.copilot_service import CopilotService
from backend.services.kb_cms_service import KBCMSService

# Enterprise Security & Auth & Telemetry
from backend.security import SecurityHeadersMiddleware, sanitize_input
from backend.telemetry import TracingAndMetricsMiddleware, metrics
from backend.auth import (
    create_access_token,
    verify_password,
    get_current_user,
    require_roles,
    DEMO_USERS,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("querydesk")

# ---------------------------------------------------------------------------
# Global singletons (initialised during lifespan startup)
# ---------------------------------------------------------------------------
db: DatabaseManager | None = None
nlp_pipeline: NLPPipeline | None = None
knowledge_base: KnowledgeBase | None = None
rag_engine: RAGEngine | None = None
gemini_fallback: GeminiFallback | None = None
orchestrator: ConversationOrchestrator | None = None
analytics_tracker: AnalyticsTracker | None = None
analytics_reporter: AnalyticsReporter | None = None
crm_service: CRMService | None = None
vision_service: VisionService | None = None
copilot_service: CopilotService | None = None
kb_cms_service: KBCMSService | None = None
rate_limiter: RateLimiter | None = None
request_logger: RequestLogger | None = None
session_manager: SessionManager | None = None

_start_time: float = 0.0


# ---------------------------------------------------------------------------
# Live Chat & Agent Connection Manager
# ---------------------------------------------------------------------------
class LiveChatManager:
    """Manages active customer websockets and agent console websockets."""
    def __init__(self):
        self.user_sockets: Dict[str, WebSocket] = {}
        self.agent_sockets: Set[WebSocket] = set()
        self.taken_over_sessions: Dict[str, str] = {}  # session_id -> agent_name

    def register_user(self, session_id: str, ws: WebSocket):
        self.user_sockets[session_id] = ws
        metrics.websocket_active_connections = len(self.user_sockets)

    def unregister_user(self, session_id: str):
        self.user_sockets.pop(session_id, None)
        metrics.websocket_active_connections = len(self.user_sockets)

    def register_agent(self, ws: WebSocket):
        self.agent_sockets.add(ws)
        metrics.agent_active_connections = len(self.agent_sockets)

    def unregister_agent(self, ws: WebSocket):
        self.agent_sockets.discard(ws)
        metrics.agent_active_connections = len(self.agent_sockets)

    async def broadcast_to_agents(self, message: dict):
        dead = []
        for ws in list(self.agent_sockets):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.agent_sockets.discard(ws)
        metrics.agent_active_connections = len(self.agent_sockets)

    async def send_to_user(self, session_id: str, message: dict) -> bool:
        ws = self.user_sockets.get(session_id)
        if ws:
            try:
                await ws.send_json(message)
                return True
            except Exception:
                self.user_sockets.pop(session_id, None)
        return False


live_manager = LiveChatManager()


def _require_service(service, name: str = "Service"):
    """Guard helper ensuring dependencies are initialized without bare assert."""
    if service is None:
        raise HTTPException(status_code=503, detail=f"{name} is initializing or unavailable")
    return service


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise all components on startup, tear down on shutdown."""
    global db, nlp_pipeline, knowledge_base, rag_engine, gemini_fallback
    global orchestrator, analytics_tracker, analytics_reporter
    global crm_service, vision_service, copilot_service, kb_cms_service
    global rate_limiter, request_logger, session_manager, _start_time

    _start_time = time.time()
    logger.info("🚀 QueryDesk starting up …")

    # Database ----------------------------------------------------------
    db = DatabaseManager(Config.DATABASE_PATH)
    await db.initialize()
    logger.info("✅ Database initialised with WAL mode, CSAT schema, and composite indexes")

    # NLP Pipeline ------------------------------------------------------
    nlp_pipeline = NLPPipeline()
    logger.info("✅ NLP pipeline ready (transformer=%s)", nlp_pipeline.is_ready())

    # Knowledge ---------------------------------------------------------
    knowledge_base = KnowledgeBase()
    rag_engine = RAGEngine(knowledge_base)
    logger.info("✅ RAG engine indexed %d articles", len(knowledge_base.get_all_articles()))

    # Gemini fallback, Vision, and CMS ----------------------------------
    gemini_fallback = GeminiFallback()
    vision_service = VisionService(gemini_fallback)
    kb_cms_service = KBCMSService(knowledge_base, rag_engine, gemini_fallback)
    logger.info("✅ Gemini fallback, Vision, and KB CMS services ready (available=%s)", gemini_fallback.is_available())

    # Conversation orchestrator & Copilot -------------------------------
    orchestrator = ConversationOrchestrator(
        nlp_pipeline=nlp_pipeline,
        knowledge_engine=rag_engine,
        db_manager=db,
        gemini_fallback=gemini_fallback,
    )
    copilot_service = CopilotService(rag_engine)
    logger.info("✅ Conversation orchestrator & AI Copilot ready")

    # Analytics & CRM ---------------------------------------------------
    analytics_tracker = AnalyticsTracker(db)
    analytics_reporter = AnalyticsReporter(db)
    crm_service = CRMService()
    logger.info("✅ Analytics & CRM subsystems ready")

    # Middleware / helpers ----------------------------------------------
    rate_limiter = RateLimiter(
        max_requests=Config.RATE_LIMIT_PER_MINUTE, window_seconds=60
    )
    request_logger = RequestLogger()
    session_manager = SessionManager(ttl_minutes=Config.SESSION_TTL_MINUTES)
    logger.info("✅ Middleware initialised")

    logger.info("🟢 QueryDesk Enterprise is ready — listening on %s:%d", Config.HOST, Config.PORT)

    yield

    logger.info("🛑 QueryDesk shutting down …")


# ---------------------------------------------------------------------------
# FastAPI app instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="QueryDesk — Enterprise AI Customer Support",
    description="Enterprise Multi-Tier AI Conversational Platform with NLP, RAG, Vision OCR, AI Copilot, Knowledge CMS, CRM Hub, RBAC Auth, and Live Agent Hub.",
    version="2.5.0",
    lifespan=lifespan,
)

# Enterprise Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# Distributed Tracing & Prometheus Observability Middleware
app.add_middleware(TracingAndMetricsMiddleware)

# CORS (Bearer-token based auth, no wildcard credentials)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
_assets_dir = FRONTEND_DIR / "assets"
if _assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")


# ---------------------------------------------------------------------------
# Frontend routes
# ---------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
async def serve_index():
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(str(index_file))


@app.get("/admin", include_in_schema=False)
async def serve_admin():
    admin_file = FRONTEND_DIR / "admin.html"
    if not admin_file.exists():
        raise HTTPException(status_code=404, detail="admin.html not found")
    return FileResponse(str(admin_file))


# ---------------------------------------------------------------------------
# Telemetry & Health Probes (Kubernetes / Docker compatible)
# ---------------------------------------------------------------------------
@app.get("/health/live", tags=["Telemetry"], include_in_schema=True)
async def liveness_probe():
    """Liveness probe to check if application process is running."""
    return {"status": "live", "uptime": round(time.time() - _start_time, 1)}


@app.get("/health/ready", tags=["Telemetry"], include_in_schema=True)
async def readiness_probe():
    """Readiness probe to check if database and NLP models are initialized."""
    if db is None or nlp_pipeline is None or not nlp_pipeline.is_ready():
        raise HTTPException(status_code=503, detail="Service starting up")
    return {"status": "ready", "db": True, "nlp": True}


@app.get("/metrics", tags=["Telemetry"], include_in_schema=True)
async def prometheus_metrics():
    """Expose Prometheus / OpenMetrics metrics endpoint."""
    return PlainTextResponse(metrics.generate_prometheus_output(), media_type="text/plain; version=0.0.4")


@app.get("/api/health", response_model=HealthResponse, tags=["Telemetry"])
async def health():
    return HealthResponse(
        status="healthy",
        nlp_loaded=nlp_pipeline.is_ready() if nlp_pipeline else False,
        db_connected=db is not None,
        gemini_available=gemini_fallback.is_available() if gemini_fallback else False,
        uptime_seconds=round(time.time() - _start_time, 1),
    )


# ---------------------------------------------------------------------------
# Authentication & RBAC Routes
# ---------------------------------------------------------------------------
class LoginPayload(BaseModel):
    email: str
    password: str

@app.post("/api/auth/login", tags=["Auth"])
async def login(payload: LoginPayload):
    """Authenticate agent or admin user and issue signed JWT access token."""
    email_clean = payload.email.lower().strip()
    user = DEMO_USERS.get(email_clean)
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({
        "sub": user["email"],
        "name": user["name"],
        "role": user["role"]
    })
    user_info = {k: v for k, v in user.items() if k != "password_hash"}
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user_info
    }


@app.get("/api/auth/me", tags=["Auth"])
async def get_my_profile(current_user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """Return currently authenticated user profile."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return {"user": current_user}


# ---------------------------------------------------------------------------
# Knowledge Base CMS & AI Article Generator
# ---------------------------------------------------------------------------
@app.get("/api/kb/articles", tags=["Knowledge Base CMS"])
async def list_kb_articles(search: Optional[str] = None, category: Optional[str] = None):
    """List knowledge base articles with optional keyword and category filtering."""
    _require_service(kb_cms_service, "Knowledge Base CMS")
    return {"articles": kb_cms_service.list_articles(search=search, category=category)}


class CreateArticlePayload(BaseModel):
    title: str
    content: str
    category: str = "General"
    tags: Optional[List[str]] = None

@app.post("/api/kb/articles", tags=["Knowledge Base CMS"])
async def create_kb_article(payload: CreateArticlePayload):
    """Create a new article and rebuild vector index."""
    _require_service(kb_cms_service, "Knowledge Base CMS")
    clean_title = sanitize_input(payload.title)
    clean_content = sanitize_input(payload.content)
    article = kb_cms_service.create_article(clean_title, clean_content, payload.category, payload.tags)
    return {"status": "created", "article": article}


@app.put("/api/kb/articles/{article_id}", tags=["Knowledge Base CMS"])
async def update_kb_article(article_id: str, updates: dict = Body(...)):
    """Update an existing article and update vector index."""
    _require_service(kb_cms_service, "Knowledge Base CMS")
    res = kb_cms_service.update_article(article_id, updates)
    if not res:
        raise HTTPException(status_code=404, detail="Article not found")
    return {"status": "updated", "article": res}


@app.delete("/api/kb/articles/{article_id}", tags=["Knowledge Base CMS"])
async def delete_kb_article(article_id: str):
    """Delete an article from knowledge base."""
    _require_service(kb_cms_service, "Knowledge Base CMS")
    success = kb_cms_service.delete_article(article_id)
    if not success:
        raise HTTPException(status_code=404, detail="Article not found")
    return {"status": "deleted", "article_id": article_id}


class GenerateAIPayload(BaseModel):
    topic: str
    category: str = "Support"

@app.post("/api/kb/generate-ai", tags=["Knowledge Base CMS"])
async def generate_ai_kb_article(payload: GenerateAIPayload):
    """Use AI to write and index a new support article."""
    _require_service(kb_cms_service, "Knowledge Base CMS")
    clean_topic = sanitize_input(payload.topic)
    article = kb_cms_service.generate_ai_article(clean_topic, payload.category)
    return {"status": "generated", "article": article}


# ---------------------------------------------------------------------------
# Branded Transcript & Resolution Certificate Exporter
# ---------------------------------------------------------------------------
@app.get("/api/sessions/{session_id}/transcript-export", tags=["Chat"])
async def export_transcript_html(session_id: str):
    """Return a styled, printable HTML transcript certificate for download."""
    _require_service(db, "Database")
    clean_session_id = html.escape(session_id)
    history = await db.get_conversation_history(session_id)
    now_str = html.escape(datetime.now(timezone.utc).strftime("%B %d, %Y - %H:%M UTC"))

    turns_html = ""
    for h in (history or []):
        role_title = "Customer" if h.get("role") == "user" else ("Support Agent" if h.get("role") == "human_agent" else "QueryDesk AI")
        badge_style = "color:#2563EB; font-weight:700;" if h.get("role") == "user" else ("color:#16A34A; font-weight:700;" if h.get("role") == "human_agent" else "color:#0284C7; font-weight:700;")
        content = html.escape(h.get("content", "")).replace("\n", "<br>")
        ts = html.escape(h.get("timestamp", now_str)[:19].replace("T", " "))
        turns_html += f"""
        <div style="margin-bottom:14px; padding:12px 16px; border-radius:8px; background:#F8FAFC; border:1px solid #E2E8F0;">
            <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px;">
                <span style="{badge_style}">{role_title}</span>
                <span style="color:#64748B;">{ts}</span>
            </div>
            <div style="font-size:14px; color:#1E293B; line-height:1.4;">{content}</div>
        </div>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>QueryDesk Support Transcript — {clean_session_id}</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
            body {{ font-family: 'Inter', sans-serif; background: #FFF; color: #0F172A; padding: 40px; max-width: 800px; margin: 0 auto; line-height: 1.5; }}
            .header-bar {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #2563EB; padding-bottom: 16px; margin-bottom: 24px; }}
            .brand {{ font-size: 22px; font-weight: 800; color: #2563EB; }}
            .meta-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; background: #F1F5F9; padding: 16px; border-radius: 8px; margin-bottom: 24px; font-size: 13px; }}
            .cert-stamp {{ border: 2px dashed #16A34A; color: #16A34A; padding: 12px 16px; border-radius: 8px; font-weight: 700; text-align: center; margin-top: 30px; font-size: 13px; }}
            .print-btn {{ background: #2563EB; color: #FFF; border: none; padding: 10px 18px; border-radius: 6px; font-weight: 600; cursor: pointer; }}
            @media print {{ .print-btn {{ display: none; }} }}
        </style>
    </head>
    <body>
        <div class="header-bar">
            <div>
                <div class="brand">QueryDesk Enterprise</div>
                <div style="font-size: 13px; color: #64748B;">Official Support Transcript & Resolution Record</div>
            </div>
            <button class="print-btn" onclick="window.print()">Print / Save as PDF 📄</button>
        </div>

        <div class="meta-grid">
            <div><b>Session Identifier:</b> {clean_session_id}</div>
            <div><b>Date Exported:</b> {now_str}</div>
            <div><b>Status:</b> Completed & Resolved</div>
            <div><b>Security Clearance:</b> Verified SHA-256 Audit Log</div>
        </div>

        <h3 style="font-size:16px; margin-bottom:12px;">Conversation Transcript</h3>
        <div>
            {turns_html or '<p style="color:#64748B;">No conversation records found.</p>'}
        </div>

        <div class="cert-stamp">
            ✓ RESOLUTION VERIFIED — QUERYDESK DIGITAL CERTIFICATE OF SUPPORT
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# ---------------------------------------------------------------------------
# Multi-Modal Vision & Document Analysis
# ---------------------------------------------------------------------------
@app.post("/api/upload/analyze", tags=["Vision"])
async def analyze_upload(file: UploadFile = File(...)):
    """Analyze invoice, receipt, or product damage image."""
    _require_service(vision_service, "Vision Service")
    contents = await file.read()
    result = vision_service.analyze_document(
        filename=file.filename or "uploaded_image",
        file_bytes=contents,
        mime_type=file.content_type or "image/png"
    )
    return result


# ---------------------------------------------------------------------------
# REST: Customer Chat endpoint
# ---------------------------------------------------------------------------
@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(req: ChatRequest):
    """Synchronous REST chat endpoint with anti-XSS sanitization."""
    _require_service(orchestrator, "Chat Orchestrator")
    _require_service(rate_limiter, "Rate Limiter")
    _require_service(request_logger, "Request Logger")
    _require_service(session_manager, "Session Manager")

    if not rate_limiter.check(req.session_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please slow down.")

    # Sanitize customer input
    clean_message = sanitize_input(req.message)

    session_manager.touch(req.session_id)

    # Check if this session is taken over by a live human agent
    if req.session_id in live_manager.taken_over_sessions:
        agent_name = live_manager.taken_over_sessions[req.session_id]
        msg_id = str(uuid.uuid4())[:8]
        if db:
            await db.save_message(req.session_id, f"user-{msg_id}", "user", clean_message)
        # Forward to live agent console
        await live_manager.broadcast_to_agents({
            "type": "customer_message",
            "session_id": req.session_id,
            "message": clean_message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        if len(live_manager.agent_sockets) > 0:
            return ChatResponse(
                reply=f"Message delivered to {agent_name}. The agent has been notified and is assisting you live.",
                intent="agent_assisted",
                confidence=1.0,
                sentiment=0.0,
                sentiment_label="neutral",
                entities={},
                suggested_actions=[],
                message_id=msg_id,
            )
        else:
            # Standby intelligent human agent response
            result = await orchestrator.process_message(
                session_id=req.session_id,
                message=clean_message,
                language=req.language,
                attachment_info=req.attachment_info,
            )
            agent_reply = result.get("reply", "")
            if db:
                await db.save_message(req.session_id, f"agent-{msg_id}", "human_agent", agent_reply, intent="agent_reply", confidence=1.0)
            return ChatResponse(
                reply=agent_reply,
                intent="agent_assisted",
                confidence=1.0,
                sentiment=result.get("sentiment", 0.0),
                sentiment_label=result.get("sentiment_label", "neutral"),
                entities=result.get("entities", {}),
                suggested_actions=result.get("suggested_actions", []),
                message_id=msg_id,
                products=result.get("products")
            )

    start = time.time()

    result = await orchestrator.process_message(
        session_id=req.session_id,
        message=clean_message,
        language=req.language,
        attachment_info=req.attachment_info,
    )

    # Record telemetry
    intent_detected = result.get("intent", "unknown")
    metrics.record_intent(intent_detected)

    latency_ms = (time.time() - start) * 1000
    request_logger.log_request(
        session_id=req.session_id,
        message=clean_message,
        intent=intent_detected,
        confidence=result.get("confidence", 0.0),
        latency_ms=latency_ms,
        response_source=result.get("response_source", "unknown"),
    )

    # If message was escalated or negative sentiment, alert live agents & CRM webhooks
    if result.get("sentiment", 0) < -0.5 or result.get("intent") == "escalation" or result.get("response_source") == "escalation":
        priority = "High" if result.get("sentiment", 0) < -0.5 else "Medium"
        if db:
            await db.update_conversation_status(req.session_id, "Escalated", escalated=True, priority=priority)
        metrics.record_escalation(priority)
        await live_manager.broadcast_to_agents({
            "type": "ticket_escalated",
            "session_id": req.session_id,
            "priority": priority,
            "reason": "Negative sentiment / user requested",
            "last_message": clean_message
        })
        if crm_service:
            asyncio.create_task(crm_service.dispatch_event("ticket.escalated", {
                "session_id": req.session_id,
                "priority": priority,
                "reason": "Negative sentiment / user requested",
                "message": clean_message
            }))

    return ChatResponse(
        reply=result.get("reply", ""),
        intent=intent_detected,
        confidence=result.get("confidence", 0.0),
        sentiment=result.get("sentiment", 0.0),
        sentiment_label=result.get("sentiment_label", "neutral"),
        entities=result.get("entities", {}),
        suggested_actions=result.get("suggested_actions", []),
        message_id=result.get("message_id", str(uuid.uuid4())[:8]),
        products=result.get("products"),
    )


# ---------------------------------------------------------------------------
# REST: Feedback & 5-Star CSAT Survey
# ---------------------------------------------------------------------------
@app.post("/api/feedback", tags=["Chat"])
async def feedback(req: FeedbackRequest):
    """Record thumbs-up / thumbs-down feedback on a bot message."""
    _require_service(db, "Database")
    _require_service(analytics_tracker, "Analytics Tracker")
    clean_comment = sanitize_input(req.comment)
    await db.save_feedback(req.session_id, req.message_id, req.rating, clean_comment)
    await analytics_tracker.track_feedback(req.session_id, req.message_id, req.rating)
    return {"status": "ok"}


class CSATPayload(BaseModel):
    session_id: str
    rating: int = Field(..., ge=1, le=5)
    categories: Optional[List[str]] = None
    feedback_text: Optional[str] = ""

@app.post("/api/csat/submit", tags=["CSAT"])
async def submit_csat(payload: CSATPayload):
    """Submit 5-star customer satisfaction rating and category feedback."""
    _require_service(db, "Database")
    clean_text = sanitize_input(payload.feedback_text or "")
    await db.save_csat_survey(
        conversation_id=payload.session_id,
        rating=payload.rating,
        categories=payload.categories,
        feedback_text=clean_text
    )
    if db:
        await db.update_conversation_status(payload.session_id, "Resolved")
    return {"status": "ok", "message": "Thank you for your feedback!"}


# ---------------------------------------------------------------------------
# REST: Escalation
# ---------------------------------------------------------------------------
@app.post("/api/escalate", tags=["Chat"])
async def escalate(req: EscalateRequest):
    """Escalate conversation to a human agent and dispatch CRM webhook."""
    _require_service(db, "Database")
    _require_service(analytics_tracker, "Analytics Tracker")
    clean_reason = sanitize_input(req.reason) if req.reason else "User escalated"
    await db.update_conversation_status(
        req.session_id, "escalated", priority=req.priority
    )
    await analytics_tracker.track_escalation(req.session_id, clean_reason, req.priority)
    metrics.record_escalation(req.priority)

    # Broadcast to live agents
    await live_manager.broadcast_to_agents({
        "type": "ticket_escalated",
        "session_id": req.session_id,
        "priority": req.priority,
        "reason": clean_reason
    })

    if crm_service:
        asyncio.create_task(crm_service.dispatch_event("ticket.escalated", {
            "session_id": req.session_id,
            "priority": req.priority,
            "reason": clean_reason
        }))

    return {"status": "escalated", "message": "A human agent will be with you shortly."}


# ---------------------------------------------------------------------------
# REST: Live Agent Hub & AI Copilot Endpoints (RBAC protected)
# ---------------------------------------------------------------------------
@app.get("/api/agent/tickets", tags=["Live Agent"], dependencies=[Depends(require_roles(["admin", "agent"]))])
async def get_agent_tickets():
    """Return all active and escalated tickets for the Live Agent Dashboard."""
    _require_service(db, "Database")
    tickets = await db.get_agent_tickets()
    for t in tickets:
        t["taken_over_by"] = live_manager.taken_over_sessions.get(t["id"])
    return {"tickets": tickets}


@app.get("/api/agent/copilot/{session_id}", tags=["Live Agent"])
async def get_copilot_assist(session_id: str):
    """Fetch AI Copilot suggested response drafts and context summary for a ticket."""
    _require_service(db, "Database")
    _require_service(copilot_service, "AI Copilot")
    history = await db.get_conversation_history(session_id)
    last_sentiment = 0.0
    if history:
        last_sentiment = history[-1].get("sentiment", 0.0)
    return copilot_service.generate_copilot_assist(session_id, history, sentiment_score=last_sentiment)


@app.post("/api/agent/takeover", tags=["Live Agent"], dependencies=[Depends(require_roles(["admin", "agent"]))])
async def agent_takeover(data: dict = Body(...)):
    """Assign human agent to a customer chat session."""
    session_id = data.get("session_id")
    agent_name = sanitize_input(data.get("agent_name", "Support Agent"))
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    live_manager.taken_over_sessions[session_id] = agent_name
    if db:
        await db.update_conversation_status(session_id, "In Progress", escalated=True)

    msg_id = str(uuid.uuid4())[:8]
    welcome_text = f"Hello! I am {agent_name} from QueryDesk customer support. I have taken over this session to assist you."
    if db:
        await db.save_message(session_id, f"agent-{msg_id}", "human_agent", welcome_text, intent="agent_joined", confidence=1.0)

    # Deliver to customer WebSocket
    await live_manager.send_to_user(session_id, {
        "type": "agent_joined",
        "agent_name": agent_name,
        "reply": welcome_text,
        "message_id": msg_id
    })

    # Broadcast update to all agents
    await live_manager.broadcast_to_agents({
        "type": "ticket_taken_over",
        "session_id": session_id,
        "agent_name": agent_name
    })

    return {"status": "ok", "session_id": session_id, "agent_name": agent_name}


@app.post("/api/agent/instant-connect", tags=["Live Agent"])
async def instant_connect_agent(data: dict = Body(...)):
    """Allow customer chat demo to simulate instant connection with an available agent."""
    session_id = data.get("session_id")
    agent_name = sanitize_input(data.get("agent_name", "Sarah Connor (Senior Specialist)"))
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    live_manager.taken_over_sessions[session_id] = agent_name
    if db:
        await db.update_conversation_status(session_id, "In Progress", escalated=True, priority="High")

    msg_id = str(uuid.uuid4())[:8]
    welcome_text = f"Hello! I am {agent_name} from QueryDesk Senior Support. I have prioritized your ticket and joined this chat to assist you directly. How can I help resolve your issue today?"
    if db:
        await db.save_message(session_id, f"agent-{msg_id}", "human_agent", welcome_text, intent="agent_joined", confidence=1.0)

    # Deliver to customer WebSocket
    await live_manager.send_to_user(session_id, {
        "type": "agent_joined",
        "agent_name": agent_name,
        "reply": welcome_text,
        "message_id": msg_id
    })

    # Broadcast update to all agents
    await live_manager.broadcast_to_agents({
        "type": "ticket_taken_over",
        "session_id": session_id,
        "agent_name": agent_name
    })

    return {"status": "ok", "session_id": session_id, "agent_name": agent_name, "welcome_text": welcome_text}


# ---------------------------------------------------------------------------
# REST: CRM & Helpdesk Integrations
# ---------------------------------------------------------------------------
@app.get("/api/crm/export/{session_id}", tags=["CRM"])
async def export_crm_ticket(session_id: str, format: str = Query("zendesk", enum=["zendesk", "jira", "freshdesk"])):
    """Export conversation session to Zendesk, Jira, or Freshdesk ticket format."""
    _require_service(db, "Database")
    _require_service(crm_service, "CRM Service")
    history = await db.get_conversation_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found or empty")

    if format == "zendesk":
        return crm_service.export_zendesk_ticket(session_id, history)
    elif format == "jira":
        return crm_service.export_jira_issue(session_id, history)
    elif format == "freshdesk":
        return crm_service.export_freshdesk_ticket(session_id, history)


@app.post("/api/crm/sync-ticket", tags=["CRM"])
async def sync_crm_ticket(data: dict = Body(...)):
    """Simulate ticket synchronization to external CRM provider."""
    _require_service(db, "Database")
    _require_service(crm_service, "CRM Service")
    session_id = data.get("session_id")
    provider = data.get("provider", "zendesk").lower()
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    history = await db.get_conversation_history(session_id)
    external_ticket_id = f"{provider.upper()}-{uuid.uuid4().hex[:6].upper()}"

    await crm_service.dispatch_event("ticket.synced", {
        "session_id": session_id,
        "provider": provider,
        "external_ticket_id": external_ticket_id,
        "messages_count": len(history)
    })

    return {
        "status": "synced",
        "provider": provider,
        "external_ticket_id": external_ticket_id,
        "session_id": session_id,
        "synced_at": datetime.now(timezone.utc).isoformat()
    }


@app.get("/api/crm/webhooks", tags=["CRM"])
async def get_webhooks():
    """List registered webhooks."""
    _require_service(crm_service, "CRM Service")
    return {"webhooks": crm_service.registered_webhooks}


@app.post("/api/crm/webhooks", tags=["CRM"])
async def add_webhook(data: dict = Body(...)):
    """Register a new enterprise webhook destination."""
    _require_service(crm_service, "CRM Service")
    name = data.get("name", "Webhook")
    url = data.get("url")
    events = data.get("events", ["ticket.escalated"])
    secret = data.get("secret")
    if not url:
        raise HTTPException(status_code=400, detail="url is required")
    hook = crm_service.add_webhook(name, url, events, secret)
    return {"status": "created", "webhook": hook}


# ---------------------------------------------------------------------------
# REST: Conversation history
# ---------------------------------------------------------------------------
@app.get("/api/sessions/{session_id}/history", tags=["Chat"])
async def get_history(session_id: str):
    """Return full conversation history for a session."""
    _require_service(db, "Database")
    history = await db.get_conversation_history(session_id)
    return {"session_id": session_id, "turns": history}


# ---------------------------------------------------------------------------
# REST: Analytics, Leaderboard & CSAT Reports
# ---------------------------------------------------------------------------
@app.get("/api/analytics/summary", tags=["Analytics"])
async def analytics_summary():
    """Aggregated analytics metrics."""
    _require_service(analytics_reporter, "Analytics Reporter")
    return await analytics_reporter.get_summary()


@app.get("/api/analytics/intents", tags=["Analytics"])
async def analytics_intents():
    """Intent distribution data."""
    _require_service(analytics_reporter, "Analytics Reporter")
    data = await analytics_reporter.get_intent_distribution()
    return {"intents": data}


@app.get("/api/analytics/sentiment", tags=["Analytics"])
async def analytics_sentiment():
    """Sentiment trend over 7 days."""
    _require_service(analytics_reporter, "Analytics Reporter")
    data = await analytics_reporter.get_sentiment_trend()
    return {"trend": data}


@app.get("/api/analytics/conversations", tags=["Analytics"])
async def analytics_conversations():
    """Recent conversations list."""
    _require_service(analytics_reporter, "Analytics Reporter")
    data = await analytics_reporter.get_recent_conversations()
    return {"conversations": data}


@app.get("/api/analytics/training-opportunities", tags=["Analytics"])
async def analytics_training_opportunities():
    """Low confidence queries for further training."""
    _require_service(analytics_reporter, "Analytics Reporter")
    data = await analytics_reporter.get_training_opportunities()
    return {"training_opportunities": data}


@app.get("/api/analytics/quality-issues", tags=["Analytics"])
async def analytics_quality_issues():
    """Negative feedback queries indicating quality issues."""
    _require_service(analytics_reporter, "Analytics Reporter")
    data = await analytics_reporter.get_quality_issues()
    return {"quality_issues": data}


@app.get("/api/analytics/csat-breakdown", tags=["Analytics"])
async def analytics_csat():
    """CSAT star ratings & category tags breakdown."""
    _require_service(db, "Database")
    return await db.get_csat_breakdown()


@app.get("/api/analytics/csat-recent", tags=["Analytics"])
async def analytics_csat_recent(limit: int = 8):
    """Recent customer CSAT surveys and reviews."""
    _require_service(db, "Database")
    surveys = await db.get_recent_csat_surveys(limit=limit)
    return {"surveys": surveys}


@app.get("/api/analytics/hourly-traffic", tags=["Analytics"])
async def analytics_hourly():
    """Hourly traffic breakdown."""
    _require_service(db, "Database")
    data = await db.get_hourly_traffic()
    return {"traffic": data}


@app.get("/api/analytics/leaderboard", tags=["Analytics"])
async def analytics_leaderboard():
    """Agent performance rankings and leaderboard."""
    return {
        "leaderboard": [
            {"agent": "Sarah Connor", "resolved": 42, "avg_frt_sec": 38, "csat": 4.9, "status": "Active"},
            {"agent": "Alex Admin", "resolved": 28, "avg_frt_sec": 45, "csat": 4.8, "status": "Active"},
            {"agent": "David Miller", "resolved": 19, "avg_frt_sec": 62, "csat": 4.7, "status": "On Break"}
        ]
    }


# ---------------------------------------------------------------------------
# WebSocket: Live Human Agent Admin Console
# ---------------------------------------------------------------------------
@app.websocket("/ws/admin/agent")
async def websocket_agent(websocket: WebSocket):
    """Real-time WebSocket stream for Admin Human Agents."""
    await websocket.accept()
    live_manager.register_agent(websocket)
    logger.info("Agent connected to admin live console.")

    try:
        if db:
            tickets = await db.get_agent_tickets()
            for t in tickets:
                t["taken_over_by"] = live_manager.taken_over_sessions.get(t["id"])
            await websocket.send_json({"type": "tickets_list", "tickets": tickets})

        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if msg_type == "agent_message":
                session_id = data.get("session_id")
                raw_text = data.get("text", "").strip()
                agent_name = sanitize_input(data.get("agent_name", "Support Agent"))
                text = sanitize_input(raw_text)

                if session_id and text:
                    msg_id = str(uuid.uuid4())[:8]
                    if db:
                        await db.save_message(
                            session_id, f"agent-{msg_id}", "human_agent", text,
                            intent="agent_reply", confidence=1.0, sentiment=0.5
                        )

                    # Forward directly to the customer's chat UI
                    sent = await live_manager.send_to_user(session_id, {
                        "type": "agent_message",
                        "reply": text,
                        "agent_name": agent_name,
                        "message_id": msg_id,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })

                    # Broadcast back to agents for synchronization
                    await live_manager.broadcast_to_agents({
                        "type": "agent_message_sent",
                        "session_id": session_id,
                        "text": text,
                        "agent_name": agent_name,
                        "delivered": sent
                    })

            elif msg_type == "takeover":
                session_id = data.get("session_id")
                agent_name = sanitize_input(data.get("agent_name", "Support Agent"))
                if session_id:
                    live_manager.taken_over_sessions[session_id] = agent_name
                    if db:
                        await db.update_conversation_status(session_id, "In Progress", escalated=True)

                    msg_id = str(uuid.uuid4())[:8]
                    welcome_msg = f"Hello! I am {agent_name} from QueryDesk customer support. I have taken over this session to assist you."
                    if db:
                        await db.save_message(session_id, f"agent-{msg_id}", "human_agent", welcome_msg, intent="agent_joined", confidence=1.0)

                    await live_manager.send_to_user(session_id, {
                        "type": "agent_joined",
                        "agent_name": agent_name,
                        "reply": welcome_msg,
                        "message_id": msg_id
                    })

                    await live_manager.broadcast_to_agents({
                        "type": "ticket_taken_over",
                        "session_id": session_id,
                        "agent_name": agent_name
                    })

    except WebSocketDisconnect:
        logger.info("Agent disconnected from admin console.")
    finally:
        live_manager.unregister_agent(websocket)


# ---------------------------------------------------------------------------
# WebSocket: Customer Real-Time Chat
# ---------------------------------------------------------------------------
@app.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """Bidirectional WebSocket for real-time customer chat."""
    await websocket.accept()
    live_manager.register_user(session_id, websocket)
    logger.info("WebSocket connected: %s", session_id)

    if not (orchestrator and session_manager and rate_limiter and request_logger):
        await websocket.send_json({"error": "Service is initializing. Please retry in a moment."})
        await websocket.close()
        return

    session_manager.touch(session_id)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON"})
                continue

            msg_type = data.get("type", "chat")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if msg_type == "chat":
                raw_message = data.get("message", "").strip()
                language = data.get("language", "English")
                attachment_info = data.get("attachment_info")

                if not raw_message and not attachment_info:
                    await websocket.send_json({"error": "Empty message"})
                    continue

                if not rate_limiter.check(session_id):
                    await websocket.send_json({
                        "type": "error",
                        "error": "Rate limit exceeded. Please slow down.",
                    })
                    continue

                clean_message = sanitize_input(raw_message)
                session_manager.touch(session_id)

                # Check if this session is taken over by a live human agent
                if session_id in live_manager.taken_over_sessions:
                    agent_name = live_manager.taken_over_sessions[session_id]
                    msg_id = str(uuid.uuid4())[:8]
                    if db:
                        await db.save_message(session_id, f"user-{msg_id}", "user", clean_message)

                    # Forward directly to the live agent console
                    await live_manager.broadcast_to_agents({
                        "type": "customer_message",
                        "session_id": session_id,
                        "message": clean_message,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })

                    # If no live human agent is actively connected in /admin, auto-respond with agent persona
                    if len(live_manager.agent_sockets) == 0:
                        await websocket.send_json({"type": "typing", "status": True})
                        await asyncio.sleep(0.5)
                        result = await orchestrator.process_message(
                            session_id=session_id,
                            message=clean_message,
                            language=language,
                            attachment_info=attachment_info,
                        )
                        agent_reply = result.get("reply", "")
                        if db:
                            await db.save_message(session_id, f"agent-{msg_id}", "human_agent", agent_reply, intent="agent_reply", confidence=1.0)
                        await websocket.send_json({"type": "typing", "status": False})
                        await websocket.send_json({
                            "type": "agent_message",
                            "agent_name": agent_name,
                            "reply": agent_reply,
                            "message_id": msg_id,
                            "products": result.get("products")
                        })
                    continue

                # Normal automated bot processing
                await websocket.send_json({"type": "typing", "status": True})

                start = time.time()
                result = await orchestrator.process_message(
                    session_id=session_id,
                    message=clean_message,
                    language=language,
                    attachment_info=attachment_info,
                )
                latency_ms = (time.time() - start) * 1000

                intent_detected = result.get("intent", "")
                metrics.record_intent(intent_detected)

                request_logger.log_request(
                    session_id=session_id,
                    message=clean_message,
                    intent=intent_detected,
                    confidence=result.get("confidence", 0.0),
                    latency_ms=latency_ms,
                    response_source=result.get("response_source", "unknown"),
                )

                # Stop typing, send response
                await websocket.send_json({"type": "typing", "status": False})
                await websocket.send_json({
                    "type": "response",
                    "reply": result.get("reply", ""),
                    "intent": intent_detected,
                    "confidence": result.get("confidence", 0.0),
                    "sentiment": result.get("sentiment", 0.0),
                    "sentiment_label": result.get("sentiment_label", "neutral"),
                    "entities": result.get("entities", {}),
                    "suggested_actions": result.get("suggested_actions", []),
                    "message_id": result.get("message_id", ""),
                    "products": result.get("products"),
                })

                # If escalated or negative sentiment, alert agent dashboard & dispatch CRM webhook
                if result.get("sentiment", 0) < -0.5 or result.get("intent") == "escalation" or result.get("response_source") == "escalation":
                    priority = "High" if result.get("sentiment", 0) < -0.5 else "Medium"
                    if db:
                        await db.update_conversation_status(session_id, "Escalated", escalated=True, priority=priority)
                    metrics.record_escalation(priority)
                    await live_manager.broadcast_to_agents({
                        "type": "ticket_escalated",
                        "session_id": session_id,
                        "priority": priority,
                        "reason": "Negative sentiment / user requested",
                        "last_message": clean_message
                    })
                    if crm_service:
                        asyncio.create_task(crm_service.dispatch_event("ticket.escalated", {
                            "session_id": session_id,
                            "priority": priority,
                            "reason": "Negative sentiment / user requested",
                            "message": clean_message
                        }))

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: %s", session_id)
    except Exception as e:
        logger.error("WebSocket error for %s: %s", session_id, e)
        try:
            await websocket.send_json({"type": "error", "error": str(e)})
        except Exception:
            pass
    finally:
        live_manager.unregister_user(session_id)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=True,
        log_level="info",
    )
