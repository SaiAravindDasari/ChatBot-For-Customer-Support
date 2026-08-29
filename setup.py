"""
QueryDesk — Setup Script
Downloads required NLP models and initializes the database.
Run this once after installing requirements: python setup.py
"""

import subprocess
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("setup")


def download_nltk_data():
    """Download required NLTK datasets."""
    logger.info("📥 Downloading NLTK data …")
    import nltk
    datasets = ["punkt", "punkt_tab", "stopwords", "wordnet", "averaged_perceptron_tagger", "averaged_perceptron_tagger_eng", "vader_lexicon"]
    for ds in datasets:
        try:
            nltk.download(ds, quiet=True)
            logger.info("  ✅ %s", ds)
        except Exception as e:
            logger.warning("  ⚠️ Failed to download %s: %s", ds, e)


def download_spacy_model():
    """Download the SpaCy English model."""
    logger.info("📥 Downloading SpaCy model (en_core_web_sm) …")
    try:
        import spacy
        try:
            spacy.load("en_core_web_sm")
            logger.info("  ✅ en_core_web_sm already installed")
        except OSError:
            subprocess.check_call(
                [sys.executable, "-m", "spacy", "download", "en_core_web_sm"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info("  ✅ en_core_web_sm downloaded")
    except ImportError:
        logger.warning("  ⚠️ SpaCy not installed — entity extraction will use regex only")


def test_sentence_transformers():
    """Test if sentence-transformers can load the embedding model."""
    logger.info("📥 Testing sentence-transformers model …")
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        _ = model.encode(["test"])
        logger.info("  ✅ all-MiniLM-L6-v2 loaded (will be cached for future use)")
    except ImportError:
        logger.warning("  ⚠️ sentence-transformers not installed — will fall back to TF-IDF")
    except Exception as e:
        logger.warning("  ⚠️ Could not load model: %s — will fall back to TF-IDF", e)


def initialize_database():
    """Create the SQLite database with schema."""
    logger.info("🗄️ Initializing database …")
    import asyncio
    from backend.database import DatabaseManager
    from backend.config import Config

    db_path = Config.DATABASE_PATH
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async def _init():
        db = DatabaseManager(db_path)
        await db.initialize()
        logger.info("  ✅ Database created at %s", db_path)

    asyncio.run(_init())


def verify_data_files():
    """Check that all required data files exist."""
    logger.info("📋 Verifying data files …")
    data_dir = Path(__file__).parent / "backend" / "data"
    required = ["intents.json", "articles.json", "dialog_flows.json", "entities.json"]
    for fname in required:
        fpath = data_dir / fname
        if fpath.exists():
            logger.info("  ✅ %s (%d bytes)", fname, fpath.stat().st_size)
        else:
            logger.error("  ❌ %s — MISSING!", fname)


def main():
    logger.info("=" * 60)
    logger.info("  QueryDesk — AI Customer Support Chatbot Setup")
    logger.info("=" * 60)
    logger.info("")

    # Step 1: NLTK
    download_nltk_data()
    logger.info("")

    # Step 2: SpaCy
    download_spacy_model()
    logger.info("")

    # Step 3: Sentence-Transformers
    test_sentence_transformers()
    logger.info("")

    # Step 4: Data files
    verify_data_files()
    logger.info("")

    # Step 5: Database
    initialize_database()
    logger.info("")

    logger.info("=" * 60)
    logger.info("  ✅ Setup complete!")
    logger.info("")
    logger.info("  To start the server:")
    logger.info("    cd \"%s\"", Path(__file__).parent)
    logger.info("    python -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 5000")
    logger.info("    (Or simply double-click run.bat)")
    logger.info("")
    logger.info("  Then open http://localhost:5000 in your browser.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
