"""Configuration settings for the QueryDesk Customer Support Platform.

Loads environment variables using python-dotenv and exposes centralized
configuration values for thresholds, models, rate limits, security, and paths.
"""

import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()


class Config:
    """Application configuration parameters and thresholds."""

    # --- Environment ---
    ENVIRONMENT: str = os.getenv('ENVIRONMENT', 'development')
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'info').lower()

    # --- Paths ---
    BASE_DIR: Path = Path(__file__).parent
    DATA_DIR: Path = BASE_DIR / 'data'
    DATABASE_PATH: str = os.getenv('DATABASE_PATH', str(BASE_DIR / 'data' / 'chatbot.db'))

    # --- Server ---
    HOST: str = os.getenv('HOST', '0.0.0.0')
    PORT: int = int(os.getenv('PORT', '5000'))

    # --- AI & NLP ---
    GEMINI_API_KEY: str = os.getenv('GEMINI_API_KEY', '')
    GEMINI_MODEL: str = 'gemini-2.0-flash'
    EMBEDDING_MODEL: str = 'all-MiniLM-L6-v2'
    SPACY_MODEL: str = 'en_core_web_sm'

    # --- Thresholds ---
    INTENT_CONFIDENCE_THRESHOLD: float = float(os.getenv('INTENT_CONFIDENCE_THRESHOLD', '0.75'))
    RAG_SIMILARITY_THRESHOLD: float = float(os.getenv('RAG_SIMILARITY_THRESHOLD', '0.70'))
    SENTIMENT_ESCALATION_THRESHOLD: float = float(os.getenv('SENTIMENT_ESCALATION_THRESHOLD', '-0.5'))

    # --- Security & Auth ---
    JWT_SECRET: str = os.getenv('JWT_SECRET', 'querydesk-dev-secret-' + secrets.token_hex(16))

    # --- Session & Rate Limiting ---
    SESSION_TTL_MINUTES: int = int(os.getenv('SESSION_TTL_MINUTES', '30'))
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv('RATE_LIMIT_PER_MINUTE', '30'))
    MAX_CONVERSATION_TURNS: int = int(os.getenv('MAX_CONVERSATION_TURNS', '50'))
    MAX_CONTEXT_TURNS: int = 10
