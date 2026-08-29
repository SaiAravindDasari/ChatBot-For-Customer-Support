import aiosqlite
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str):
        """
        Initialize the DatabaseManager.
        
        Args:
            db_path (str): The path to the SQLite database file.
        """
        self.db_path = db_path

    async def initialize(self) -> None:
        """Create tables if they do not exist."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Production performance PRAGMAs
                await db.execute("PRAGMA journal_mode = WAL;")
                await db.execute("PRAGMA synchronous = NORMAL;")
                await db.execute("PRAGMA foreign_keys = ON;")
                
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS conversations (
                        id TEXT PRIMARY KEY,
                        status TEXT,
                        priority TEXT,
                        language TEXT,
                        created_at TEXT,
                        updated_at TEXT,
                        resolved_at TEXT,
                        escalated BOOLEAN DEFAULT 0
                    )
                ''')
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS messages (
                        id TEXT PRIMARY KEY,
                        conversation_id TEXT,
                        role TEXT,
                        content TEXT,
                        intent TEXT,
                        confidence REAL,
                        sentiment REAL,
                        entities TEXT,
                        timestamp TEXT,
                        FOREIGN KEY (conversation_id) REFERENCES conversations (id)
                    )
                ''')
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        conversation_id TEXT,
                        message_id TEXT,
                        rating TEXT,
                        comment TEXT,
                        timestamp TEXT
                    )
                ''')
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS analytics_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_type TEXT,
                        conversation_id TEXT,
                        data TEXT,
                        timestamp TEXT
                    )
                ''')
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS csat_surveys (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        conversation_id TEXT,
                        rating INTEGER,
                        categories TEXT,
                        feedback_text TEXT,
                        timestamp TEXT,
                        FOREIGN KEY (conversation_id) REFERENCES conversations (id)
                    )
                ''')
                
                # Performance composite indexes
                await db.execute('CREATE INDEX IF NOT EXISTS idx_messages_conv_time ON messages(conversation_id, timestamp);')
                await db.execute('CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status, priority, escalated, updated_at);')
                await db.execute('CREATE INDEX IF NOT EXISTS idx_feedback_conv ON feedback(conversation_id);')
                await db.execute('CREATE INDEX IF NOT EXISTS idx_events_type_time ON analytics_events(event_type, timestamp);')
                await db.execute('CREATE INDEX IF NOT EXISTS idx_csat_time ON csat_surveys(timestamp);')
                
                await db.commit()
                logger.info("Database initialized with WAL mode, CSAT schema, and composite performance indexes.")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    async def create_conversation(self, session_id: str, language: str = 'English', priority: str = 'Medium') -> None:
        """Create a new conversation record."""
        now = self._now()
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'INSERT OR IGNORE INTO conversations (id, status, priority, language, created_at, updated_at, escalated) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (session_id, 'Active', priority, language, now, now, 0)
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Error creating conversation {session_id}: {e}")

    async def save_message(self, conversation_id: str, message_id: str, role: str, content: str, intent: str = '', confidence: float = 0.0, sentiment: float = 0.0, entities: dict | None = None) -> None:
        """Save a message to the database."""
        now = self._now()
        entities_str = json.dumps(entities) if entities else None
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'INSERT INTO messages (id, conversation_id, role, content, intent, confidence, sentiment, entities, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (message_id, conversation_id, role, content, intent, confidence, sentiment, entities_str, now)
                )
                await db.execute(
                    'UPDATE conversations SET updated_at = ? WHERE id = ?',
                    (now, conversation_id)
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Error saving message {message_id} for conversation {conversation_id}: {e}")

    async def get_conversation_history(self, conversation_id: str) -> list[dict]:
        """Retrieve conversation history by conversation ID."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute('SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC', (conversation_id,)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting conversation history for {conversation_id}: {e}")
            return []

    async def update_conversation_status(self, conversation_id: str, status: str, **kwargs) -> None:
        """Update the status of a conversation and any other fields provided in kwargs."""
        now = self._now()
        updates = ['status = ?', 'updated_at = ?']
        values = [status, now]

        for k, v in kwargs.items():
            updates.append(f'{k} = ?')
            values.append(v)
            
        values.append(conversation_id)
        query = f"UPDATE conversations SET {', '.join(updates)} WHERE id = ?"
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(query, tuple(values))
                await db.commit()
        except Exception as e:
            logger.error(f"Error updating conversation status for {conversation_id}: {e}")

    async def save_feedback(self, conversation_id: str, message_id: str, rating: str, comment: str = '') -> None:
        """Save user feedback on a message."""
        now = self._now()
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'INSERT INTO feedback (conversation_id, message_id, rating, comment, timestamp) VALUES (?, ?, ?, ?, ?)',
                    (conversation_id, message_id, rating, comment, now)
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Error saving feedback for message {message_id}: {e}")

    async def log_event(self, event_type: str, conversation_id: str = '', data: dict | None = None) -> None:
        """Log an analytics event."""
        now = self._now()
        data_str = json.dumps(data) if data else None
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'INSERT INTO analytics_events (event_type, conversation_id, data, timestamp) VALUES (?, ?, ?, ?)',
                    (event_type, conversation_id, data_str, now)
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Error logging event {event_type}: {e}")

    async def get_analytics_summary(self) -> dict:
        """Query aggregated metrics for analytics."""
        summary = {
            'total_conversations': 0,
            'active_conversations': 0,
            'resolution_rate': 0.0,
            'avg_resolution_time': 0.0,
            'csat_score': 0.0,
            'escalation_rate': 0.0,
            'avg_response_latency': 0.0
        }
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Total and Active
                async with db.execute('SELECT COUNT(id) FROM conversations') as cursor:
                    res = await cursor.fetchone()
                    summary['total_conversations'] = res[0] if res and res[0] else 0

                async with db.execute("SELECT COUNT(id) FROM conversations WHERE status = 'Active'") as cursor:
                    res = await cursor.fetchone()
                    summary['active_conversations'] = res[0] if res and res[0] else 0

                # Resolution rate & Escalation rate
                if summary['total_conversations'] > 0:
                    async with db.execute("SELECT COUNT(id) FROM conversations WHERE status = 'Resolved'") as cursor:
                        res = await cursor.fetchone()
                        resolved = res[0] if res and res[0] else 0
                        summary['resolution_rate'] = resolved / summary['total_conversations']

                    async with db.execute("SELECT COUNT(id) FROM conversations WHERE escalated = 1") as cursor:
                        res = await cursor.fetchone()
                        escalated = res[0] if res and res[0] else 0
                        summary['escalation_rate'] = escalated / summary['total_conversations']

                # Avg resolution time (mock implementation via SQLite text/julianday math)
                async with db.execute("SELECT AVG((julianday(resolved_at) - julianday(created_at)) * 86400) FROM conversations WHERE status = 'Resolved' AND resolved_at IS NOT NULL") as cursor:
                    res = await cursor.fetchone()
                    summary['avg_resolution_time'] = res[0] if res and res[0] else 0.0

                # CSAT Score
                async with db.execute("SELECT rating, COUNT(rating) FROM feedback GROUP BY rating") as cursor:
                    rows = await cursor.fetchall()
                    counts = {r[0]: r[1] for r in rows}
                    up = counts.get('up', 0)
                    down = counts.get('down', 0)
                    if (up + down) > 0:
                        summary['csat_score'] = up / (up + down)

                # Avg response latency
                async with db.execute("SELECT AVG(CAST(json_extract(data, '$.latency_seconds') AS REAL)) FROM analytics_events WHERE event_type = 'response_time'") as cursor:
                    res = await cursor.fetchone()
                    summary['avg_response_latency'] = res[0] if res and res[0] else 0.0

        except Exception as e:
            logger.error(f"Error getting analytics summary: {e}")
            
        return summary

    async def get_intent_distribution(self) -> list[dict]:
        """Group messages by intent, count occurrences."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT intent, COUNT(*) as count FROM messages WHERE role = 'user' AND intent != '' GROUP BY intent") as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting intent distribution: {e}")
            return []

    async def get_sentiment_trend(self, days: int = 7) -> list[dict]:
        """Average sentiment per day for the last N days."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                query = """
                    SELECT date(timestamp) as date, AVG(sentiment) as avg_sentiment
                    FROM messages
                    WHERE timestamp >= date('now', ?)
                    GROUP BY date(timestamp)
                    ORDER BY date(timestamp) ASC
                """
                async with db.execute(query, (f'-{days} days',)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting sentiment trend: {e}")
            return []

    async def get_agent_tickets(self, limit: int = 50) -> list[dict]:
        """Return active/escalated tickets with recent message and sentiment summary."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                query = '''
                    SELECT c.id, c.status, c.priority, c.language, c.created_at, c.updated_at, c.escalated,
                           (SELECT content FROM messages WHERE conversation_id = c.id ORDER BY timestamp DESC LIMIT 1) as last_message,
                           (SELECT sentiment FROM messages WHERE conversation_id = c.id ORDER BY timestamp DESC LIMIT 1) as last_sentiment,
                           (SELECT role FROM messages WHERE conversation_id = c.id ORDER BY timestamp DESC LIMIT 1) as last_sender,
                           (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id) as message_count
                    FROM conversations c
                    ORDER BY c.escalated DESC, c.updated_at DESC
                    LIMIT ?
                '''
                async with db.execute(query, (limit,)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error fetching agent tickets: {e}")
            return []

    async def get_recent_conversations(self, limit: int = 20) -> list[dict]:
        """Get the most recently updated conversations."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?", (limit,)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting recent conversations: {e}")
            return []

    async def get_low_confidence_queries(self, threshold: float = 0.5, limit: int = 20) -> list[dict]:
        """Get messages with low intent confidence."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM messages WHERE role = 'user' AND confidence < ? AND intent != '' ORDER BY timestamp DESC LIMIT ?", (threshold, limit)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting low confidence queries: {e}")
            return []

    async def get_negative_feedback(self, limit: int = 20) -> list[dict]:
        """Get messages that received negative feedback."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT m.*, f.rating, f.comment FROM feedback f JOIN messages m ON f.message_id = m.id WHERE f.rating = 'down' ORDER BY f.timestamp DESC LIMIT ?", (limit,)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting negative feedback: {e}")
            return []

    async def conversation_exists(self, session_id: str) -> bool:
        """Check if a conversation exists."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT 1 FROM conversations WHERE id = ?", (session_id,)) as cursor:
                    res = await cursor.fetchone()
                    return res is not None
        except Exception as e:
            logger.error(f"Error checking if conversation {session_id} exists: {e}")
            return False

    async def save_csat_survey(self, conversation_id: str, rating: int, categories: list[str] | None = None, feedback_text: str = '') -> None:
        """Record 5-star customer CSAT survey submission."""
        now = self._now()
        cats_json = json.dumps(categories or [])
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'INSERT INTO csat_surveys (conversation_id, rating, categories, feedback_text, timestamp) VALUES (?, ?, ?, ?, ?)',
                    (conversation_id, rating, cats_json, feedback_text, now)
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Error saving CSAT survey: {e}")

    async def get_csat_breakdown(self) -> dict:
        """Return aggregated CSAT ratings and category tag distribution."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                # Rating distribution 1-5 stars
                ratings = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
                async with db.execute("SELECT rating, COUNT(*) as cnt FROM csat_surveys GROUP BY rating") as cursor:
                    rows = await cursor.fetchall()
                    for r in rows:
                        ratings[r["rating"]] = r["cnt"]

                # Category tags breakdown
                category_counts: dict[str, int] = {}
                async with db.execute("SELECT categories FROM csat_surveys WHERE categories IS NOT NULL") as cursor:
                    rows = await cursor.fetchall()
                    for r in rows:
                        try:
                            cats = json.loads(r["categories"])
                            for c in cats:
                                category_counts[c] = category_counts.get(c, 0) + 1
                        except Exception:
                            pass

                total = sum(ratings.values())
                avg_score = (sum(k * v for k, v in ratings.items()) / total) if total > 0 else 5.0
                return {
                    "total_surveys": total,
                    "average_stars": round(avg_score, 2),
                    "distribution": ratings,
                    "categories": category_counts
                }
        except Exception as e:
            logger.error(f"Error getting CSAT breakdown: {e}")
            return {"total_surveys": 0, "average_stars": 5.0, "distribution": {}, "categories": {}}

    async def get_hourly_traffic(self) -> list[dict]:
        """Aggregate message traffic grouped by hour of day (0-23)."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                # SQLite strftime('%H', timestamp)
                async with db.execute(
                    "SELECT strftime('%H', timestamp) as hour_str, COUNT(*) as msg_count FROM messages GROUP BY hour_str ORDER BY hour_str ASC"
                ) as cursor:
                    rows = await cursor.fetchall()
                    return [{"hour": int(r["hour_str"] or 0), "count": r["msg_count"]} for r in rows if r["hour_str"]]
        except Exception as e:
            logger.error(f"Error getting hourly traffic: {e}")
            return []

    async def get_recent_csat_surveys(self, limit: int = 10) -> list[dict]:
        """Return the most recent CSAT surveys with comments, stars, and categories."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT conversation_id, rating, categories, feedback_text, timestamp FROM csat_surveys ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    results = []
                    for r in rows:
                        d = dict(r)
                        try:
                            d["categories"] = json.loads(d["categories"]) if d.get("categories") else []
                        except Exception:
                            d["categories"] = []
                        results.append(d)
                    return results
        except Exception as e:
            logger.error(f"Error getting recent CSAT surveys: {e}")
            return []
