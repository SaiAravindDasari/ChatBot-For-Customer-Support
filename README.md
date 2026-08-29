# QueryDesk — Enterprise AI Customer Support Platform

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/Tests-156%2F156%20Passing-brightgreen.svg?logo=pytest&logoColor=white)](tests/)
[![Docker](https://img.shields.io/badge/Docker-Multi--Stage-2496ED.svg?logo=docker&logoColor=white)](Dockerfile)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Observability](https://img.shields.io/badge/Metrics-OpenMetrics%20%2F%20Prometheus-E6522C.svg?logo=prometheus&logoColor=white)](backend/telemetry.py)

**QueryDesk** is an enterprise-ready, autonomous AI customer support platform built for high-throughput multi-channel environments. It combines semantic NLP, vector-backed RAG, multimodal vision OCR, real-time WebSockets, live agent takeover, and bi-directional CRM synchronization into a unified, zero-configuration architecture.

---

## 🌟 12 Production Capabilities

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                 QUERYDESK PLATFORM CORE                                  │
├──────────────────────────┬───────────────────────────┬──────────────────────────────────┤
│  1. E-Commerce Tracking  │  2. Live Agent Takeover   │  3. Voice Audio I/O (STT/TTS)    │
│  4. CRM & Helpdesk Hub   │  5. Multi-Modal Vision    │  6. AI Agent Copilot             │
│  7. Smart SLA Timers     │  8. 5-Star CSAT Surveys   │  9. Live 4-Stage GPS Radar Map   │
│ 10. Knowledge Base CMS   │ 11. Printable Transcripts │ 12. Slash Macros & Leaderboard   │
└──────────────────────────┴───────────────────────────┴──────────────────────────────────┘
```

### 1. 📦 Mock E-Commerce & Dynamic Order Tracking
- Deterministic order resolution using SHA-256 seeding (`QD-1234`, `QD-4567`, `QD-5678`, `QD-9012`, or any arbitrary ID).
- Returns live carrier tracking, carrier names, dynamic delivery progress (0–100%), and route metadata.

### 2. 👩‍💼 Live Human Agent Takeover Console
- Seamless, bidirectional WebSocket handoff between automated AI and human agents (`/ws/admin/agent`).
- Agent takeover lock prevents duplicate agent assignments with real-time status broadcasting across all connected operator consoles.

### 3. 🎙️ Voice Audio I/O (STT & TTS)
- Native Web Speech API integration with real-time Speech-to-Text input and customizable Text-to-Speech synthesis.
- Visual audio frequency equalizer animations and listening pulse effects during speech capture.

### 4. 🔗 Multi-Provider CRM & Helpdesk Hub
- One-click export and bidirectional synchronization for **Zendesk**, **Jira Software**, and **Freshdesk**.
- Secure HMAC-SHA256 authenticated webhook dispatch on ticket escalation and resolution events.

### 5. 👁️ Multi-Modal Vision & Invoice OCR
- Automatic image document classification for invoices, receipts, and product damage (`POST /api/upload/analyze`).
- Extracts vendor names, invoice numbers, line items, monetary totals, and damage severity assessments.

### 6. 🤖 AI Agent Copilot & Smart Drafts
- Generates 3 contextual response drafts (Empathic, Professional, Action-Oriented) for live human agents.
- Real-time customer intent summaries and sentiment breakdown computed on-the-fly (`GET /api/agent/copilot/{session_id}`).

### 7. ⏱️ Smart SLA Timers & Inactivity Re-Engagement
- Priority-based dynamic SLA countdown timers (Critical: 2 min, High: 5 min, Normal: 15 min, Low: 30 min) with breach pulse alerts.
- Automatic customer idle detection with 90-second gentle re-engagement prompts.

### 8. ⭐ 5-Star CSAT Survey Suite & Live Customer Voice Feed
- Multi-dimensional customer satisfaction ratings with interactive star selectors, category tags, and feedback submission.
- Real-time rating distribution, average CSAT calculation, and dedicated live customer reviews feed on the admin dashboard.

### 9. 🚚 Interactive 4-Stage Stepper, Return Vouchers & GPS Radar
- Embedded in-chat shipment tracking card with interactive 4-stage milestone stepper and animated courier truck pin (`🚚`).
- Sweeping 360° GPS Radar telemetry map with real-time courier coordinates and speed.
- Digital prepaid return pass voucher cards with barcode simulation and 1-click download/pickup actions.

### 10. 📚 Knowledge Base CMS & AI Article Generator
- Full CRUD management of knowledge base articles with persistent disk storage (`backend/data/articles.json`).
- In-memory vector RAG index automatically rebuilt in milliseconds on create, update, or delete.
- Built-in AI article generation using Gemini API with intelligent offline fallback.

### 11. 📄 Branded Transcript & Resolution Certificate Exporter
- Generates print-ready, styled HTML resolution certificates with cryptographic session verification timestamps (`GET /api/sessions/{session_id}/transcript-export`).
- Full turn-by-turn audit trail suitable for customer delivery or compliance archiving.

### 12. ⚡ Agent Slash Command Macro Engine & Team Leaderboard
- Quick-response macro auto-expansion in operator console (`/refund`, `/order`, `/return`, `/apology`, `/closing`).
- Real-time agent performance leaderboard ranking operators by resolved ticket volume, First Response Time (FRT), and CSAT.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLIENT INTERACTION LAYER                          │
│  Customer Web UI (index.html)     │     Live Agent Console (admin.html)     │
│  • Glassmorphism Dark/Light Theme │     • Live Ticket Queue & Copilot       │
│  • Voice Input & Web Audio Synth  │     • Slash Macros & Leaderboard        │
│  • GPS Shipment Progress Map      │     • KB CMS & Real-time WebSockets     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ WebSocket / REST (JSON)
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                        SECURITY & GATEWAY MIDDLEWARE                        │
│  • Content Security Policy (CSP)  │  • Anti-XSS Sanitization Engine         │
│  • PBKDF2-HMAC Password Hashing   │  • HS256 JWT Role-Based Access Control  │
│  • Token-Bucket Rate Limiting     │  • OpenMetrics / Prometheus Collector   │
│  • Request Tracing (X-Request-ID) │  • Session TTL Manager (Auto-Cleanup)   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                         INTELLIGENCE & NLP PIPELINE                         │
│  • Semantic Classifier (Sentence-Transformers / TF-IDF Fallback)            │
│  • Entity Extractor (SpaCy NER + Regex for Orders, Emails, Amounts)         │
│  • Sentiment Analyzer (VADER Sentiment with Domain Support Lexicon)         │
│  • Dialog State Machine & Slot Filler (Multi-turn Contextual Flows)         │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                         KNOWLEDGE & SERVICES LAYER                          │
│  • RAG Engine (FAISS Vector Index)│  • Multi-Modal Vision OCR Service       │
│  • Knowledge Base (30+ Articles)  │  • AI Copilot & Draft Generator         │
│  • Google Gemini 2.0 Flash LLM    │  • E-Commerce & GPS Telemetry Service   │
│  • KB CMS (CRUD + Auto-Reindexing)│  • CRM Hub (Zendesk / Jira / Freshdesk) │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                               PERSISTENCE LAYER                             │
│  • SQLite3 (WAL Mode, PRAGMA synchronous=NORMAL, Composite Indexes)         │
│  • Tables: conversations, messages, feedback, csat_surveys, events          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+ or 3.12+
- `pip` package manager

### 1. Clone & Install
```bash
git clone https://github.com/your-org/chatbot-for-customer-support.git
cd "Chatbot For Customer Support"
pip install -r requirements.txt
```

### 2. Environment Configuration (Optional)
```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```
*Note: QueryDesk works completely offline out-of-the-box! Adding a `GEMINI_API_KEY` enables Gemini 2.0 Flash enhancements.*

### 3. Run First-Time Setup
```bash
python setup.py
# Or use Makefile:
make setup
```

### 4. Start Development Server
```bash
# Windows / Linux / macOS
python -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 5000

# Or Windows 1-Click:
run.bat

# Or using Makefile:
make dev
```

### 5. Access the Interfaces
- **Customer Chat UI**: [http://localhost:5000](http://localhost:5000)
- **Live Agent Console & Analytics**: [http://localhost:5000/admin](http://localhost:5000/admin)
- **Interactive API Docs (Swagger UI)**: [http://localhost:5000/docs](http://localhost:5000/docs)
- **Prometheus Metrics**: [http://localhost:5000/metrics](http://localhost:5000/metrics)

---

## 🐳 Docker Deployment

### Run with Docker Compose
```bash
docker-compose up -d --build
```

### Build & Run Container Manually
```bash
docker build -t querydesk:latest .
docker run -d -p 5000:5000 --name querydesk_app querydesk:latest
```

---

## 🔌 API Reference

### Core Chat & Sessions
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/chat` | Synchronous REST chat with intent & entity detection |
| `WS` | `/ws/{session_id}` | Bidirectional WebSocket for customer live chat |
| `GET` | `/api/sessions/{id}/history` | Retrieve complete message history for a session |
| `GET` | `/api/sessions/{id}/transcript-export` | Download printable, verified HTML transcript certificate |
| `POST` | `/api/feedback` | Submit thumbs-up / thumbs-down response rating |
| `POST` | `/api/csat/submit` | Submit 5-star CSAT survey with category tags |
| `POST` | `/api/escalate` | Trigger human agent escalation and webhook dispatch |

### Knowledge Base CMS
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/kb/articles` | List and search articles with category filter |
| `POST` | `/api/kb/articles` | Create new article and rebuild RAG vector index |
| `PUT` | `/api/kb/articles/{id}` | Update article and synchronize vector embeddings |
| `DELETE` | `/api/kb/articles/{id}` | Delete article and update index |
| `POST` | `/api/kb/generate-ai` | Use AI to draft and index support articles |

### Live Agent Console & Copilot
| Method | Endpoint | Description |
|---|---|---|
| `WS` | `/ws/admin/agent` | Real-time WebSocket connection for live agent console |
| `GET` | `/api/agent/tickets` | List active, pending, and escalated tickets |
| `GET` | `/api/agent/copilot/{id}` | Fetch AI Copilot suggested draft responses |
| `POST` | `/api/agent/takeover` | Assign operator to customer conversation |
| `POST` | `/api/agent/resolve` | Mark ticket as resolved |

### CRM & Integrations
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/crm/export/{id}` | Export ticket in Zendesk, Jira, or Freshdesk JSON format |
| `POST` | `/api/crm/sync-ticket` | Synchronize conversation session to external CRM |
| `GET` | `/api/crm/webhooks` | List registered enterprise webhook destinations |
| `POST` | `/api/crm/webhooks` | Register new HMAC-authenticated webhook |

### Observability & Telemetry
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/metrics` | Standard OpenMetrics / Prometheus exposition format |
| `GET` | `/health/live` | Kubernetes liveness probe |
| `GET` | `/health/ready` | Kubernetes readiness probe (checks DB & NLP readiness) |
| `GET` | `/api/health` | Comprehensive system health and diagnostic status |
| `GET` | `/api/analytics/summary` | Aggregated conversation and resolution metrics |
| `GET` | `/api/analytics/leaderboard` | Live agent performance rankings |
| `GET` | `/api/analytics/csat-breakdown` | CSAT star ratings and tag distribution |
| `GET` | `/api/analytics/csat-recent` | Live customer CSAT reviews & sentiment feedback feed |
| `GET` | `/api/analytics/hourly-traffic` | 24-hour message volume distribution |

---

## 🧪 Testing

QueryDesk includes a comprehensive test suite covering 100% of capabilities across 16 test files:

```bash
# Run all 150+ tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=backend --cov-report=term-missing
```

| Test Suite | Coverage Area |
|---|---|
| `test_api.py` | Core REST chat, sessions, feedback, rate limiting |
| `test_agent_console.py` | Live agent takeover, WebSockets, ticket assignment |
| `test_kb_cms.py` | Article CRUD, AI generator, RAG index updates |
| `test_transcript_export.py` | HTML transcript generator & certificate output |
| `test_copilot.py` | AI Copilot draft generation & sentiment context |
| `test_csat_analytics.py` | 5-star CSAT submissions & analytics breakdown |
| `test_ecommerce.py` | Order tracking, carrier routing, deterministic IDs |
| `test_crm.py` | Zendesk, Jira, Freshdesk exports & HMAC webhooks |
| `test_vision.py` | Multimodal invoice, receipt, and damage analysis |
| `test_auth.py` | PBKDF2 hashing, JWT tokens, RBAC permissions |
| `test_security.py` | XSS sanitization, CSP headers, frame protection |
| `test_telemetry.py` | Prometheus metrics, latency tracking, health probes |
| `test_state_machine.py` | Dialog FSM, slot filling, contextual multi-turn |
| `test_nlp_pipeline.py` | Tokenization, NER, sentiment, intent classification |
| `test_intent_classifier.py` | Intent accuracy and confidence scoring |
| `test_rag_engine.py` | FAISS vector search, similarity thresholding |

---

## 🔒 Security Hardening

- **Anti-XSS Sanitization**: Control characters stripped, HTML entities escaped, input length enforced.
- **Enterprise Security Headers**: Strict CSP, `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy: strict-origin-when-cross-origin`.
- **Cryptographic Auth**: PBKDF2-HMAC-SHA256 password hashing with 100,000 iterations, HS256 signed JWTs with expiration.
- **Rate Limiting**: Sliding window in-memory rate limiter per session with configurable thresholds.

---

## 📁 Repository Structure

```
Chatbot For Customer Support/
├── .github/
│   └── workflows/
│       └── ci.yml                  # GitHub Actions CI/CD matrix pipeline
├── backend/
│   ├── app.py                      # FastAPI application & route definitions
│   ├── auth.py                     # PBKDF2 hashing & JWT authentication
│   ├── config.py                   # Centralized configuration & environment loader
│   ├── database.py                 # SQLite async ORM with WAL mode & indexes
│   ├── middleware.py               # Rate limiting, structured logging, session TTL
│   ├── models.py                   # Pydantic v2 data schemas
│   ├── security.py                 # CSP middleware & XSS input sanitization
│   ├── telemetry.py                # Prometheus OpenMetrics collector & tracing
│   ├── analytics/
│   │   ├── reporter.py             # Analytics reporting & aggregations
│   │   └── tracker.py              # Event tracking & database logging
│   ├── conversation/
│   │   ├── context.py              # Multi-turn context manager
│   │   ├── orchestrator.py         # End-to-end conversation controller
│   │   ├── slot_filler.py          # Dynamic slot extraction
│   │   └── state_machine.py        # Finite State Machine dialog engine
│   ├── data/
│   │   ├── articles.json           # Knowledge base articles
│   │   ├── dialog_flows.json       # FSM state definitions
│   │   ├── entities.json           # Entity extraction patterns
│   │   └── intents.json            # 15 intent categories & training patterns
│   ├── knowledge/
│   │   ├── gemini_fallback.py      # Google Gemini 2.0 Flash integration
│   │   ├── knowledge_base.py       # Article indexer & loader
│   │   └── rag_engine.py           # FAISS vector similarity engine
│   ├── nlp/
│   │   ├── entity_extractor.py     # SpaCy NER + regex extraction
│   │   ├── intent_classifier.py    # Transformer embeddings + TF-IDF classifier
│   │   ├── pipeline.py             # NLP pipeline orchestrator
│   │   ├── preprocessor.py         # Text normalization & cleaning
│   │   └── sentiment.py            # VADER sentiment analysis
│   └── services/
│       ├── copilot_service.py      # AI Copilot draft suggestion engine
│       ├── crm_service.py          # Zendesk/Jira/Freshdesk integration & webhooks
│       ├── ecommerce_service.py    # Order tracking & GPS shipment telemetry
│       ├── kb_cms_service.py       # Knowledge Base CRUD & AI generator
│       └── vision_service.py       # Multimodal OCR & document analysis
├── frontend/
│   ├── admin.html                  # Live Agent & Admin Analytics Console
│   └── index.html                  # Customer Chat Interface
├── nginx/
│   └── nginx.conf                  # Production reverse proxy configuration
├── tests/                          # 16 comprehensive pytest suites (150+ tests)
├── .dockerignore                   # Docker build exclusions
├── .env.example                    # Environment variable template
├── .gitignore                      # Git ignored files & patterns
├── Dockerfile                      # Production multi-stage Docker container
├── docker-compose.yml              # Multi-container orchestration (App + Nginx)
├── LICENSE                         # MIT License
├── Makefile                        # Developer commands (install, dev, test, lint)
├── README.md                       # Comprehensive platform documentation
├── requirements.txt                # Pinned production dependencies
└── setup.py                        # Automated model download & database initializer
```

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.
