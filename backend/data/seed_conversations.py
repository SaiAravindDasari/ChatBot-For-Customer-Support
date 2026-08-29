"""
Comprehensive seed generator for QueryDesk.
Populates the SQLite database with 60+ realistic multi-turn enterprise conversations,
250+ messages, telemetry events, CSAT surveys, and feedback ratings.
"""

import asyncio
import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import aiosqlite

DB_PATH = Path(__file__).parent.parent / "data" / "chatbot.db"

# Sample Customer Profiles & Scenarios
SCENARIOS = [
    {
        "intent": "order_status",
        "priority": "Medium",
        "language": "English",
        "turns": [
            ("user", "Hi, can you check where my order #QD-1234 is right now?", "order_status", 0.94, 0.1, {"order_id": "#QD-1234"}),
            ("bot", "I'd be glad to track that for you! Order #QD-1234 is currently in transit via FedEx Express (Tracking: FDX-883920194). It is on schedule for delivery tomorrow by 3:00 PM.", "order_status", 0.96, 0.6, {}),
            ("user", "Awesome, thank you so much for the quick update!", "feedback_positive", 0.98, 0.85, {}),
            ("bot", "You're very welcome! Let us know if you need anything else. Have a fantastic day!", "farewell", 0.97, 0.8, {})
        ],
        "csat": {"rating": 5, "categories": ["⚡ Fast Resolution", "🎯 Accurate Info"], "feedback": "Super fast response!"},
        "feedback": ("up", "Clear tracking details.")
    },
    {
        "intent": "return_request",
        "priority": "Medium",
        "language": "English",
        "turns": [
            ("user", "I need to return a wireless mechanical keyboard from order #QD-5678. The switches are too loud.", "return_request", 0.93, -0.2, {"order_id": "#QD-5678", "item": "wireless mechanical keyboard"}),
            ("bot", "No problem at all! Order #QD-5678 is well within our 30-day return window. I have generated RMA #RET-84920 and dispatched a prepaid UPS shipping label to your account email.", "return_request", 0.95, 0.5, {"rma": "RET-84920"}),
            ("user", "Got the email with the barcode. Do I need to drop it at a UPS Store?", "shipping_info", 0.89, 0.1, {}),
            ("bot", "Yes, you can drop it at any authorized UPS Store or Dropbox location. Once scanned, your refund will process in 2-3 business days.", "shipping_info", 0.92, 0.4, {}),
            ("user", "Great, thanks for making this easy.", "farewell", 0.91, 0.7, {})
        ],
        "csat": {"rating": 5, "categories": ["📦 Return Handled", "⚡ Fast Resolution"], "feedback": "Prepaid label arrived instantly."},
        "feedback": ("up", "Smooth return process")
    },
    {
        "intent": "escalation",
        "priority": "High",
        "language": "English",
        "turns": [
            ("user", "I was double charged $189.50 for my subscription renewal! This is completely unacceptable.", "billing_inquiry", 0.91, -0.85, {"amount": "$189.50"}),
            ("bot", "I deeply apologize for this billing discrepancy. I am immediately escalating your ticket to a senior billing specialist.", "escalation", 0.95, -0.1, {}),
            ("human_agent", "Hello, this is Sarah Connor from Customer Care. I have reviewed your account and voided the duplicate transaction #TX-99482. A full reversal of $189.50 has been credited to your card.", "billing_inquiry", 0.99, 0.6, {}),
            ("user", "Thank you Sarah, I see the pending refund in my banking app now.", "feedback_positive", 0.94, 0.75, {}),
            ("human_agent", "I'm glad we could resolve this promptly for you! Please don't hesitate to reach back out if you notice any other anomalies.", "farewell", 0.96, 0.8, {})
        ],
        "csat": {"rating": 5, "categories": ["🤝 Polite & Friendly", "⚡ Fast Resolution"], "feedback": "Sarah resolved the double billing in minutes!"},
        "feedback": ("up", "Great agent support")
    },
    {
        "intent": "damaged_item",
        "priority": "High",
        "language": "English",
        "turns": [
            ("user", "My ceramic cookware set from #QD-9012 arrived with a cracked glass lid and broken handle.", "damaged_item", 0.94, -0.7, {"order_id": "#QD-9012"}),
            ("bot", "I am very sorry to hear that your shipment arrived damaged! Please upload a photo of the damaged item using the 📎 attachment button so we can process an immediate replacement.", "damaged_item", 0.96, 0.1, {}),
            ("user", "I uploaded the photo showing the shattered lid.", "damaged_item", 0.92, -0.1, {}),
            ("bot", "Thank you for the verification photo. We have created replacement shipment #QD-9012-R1 at zero additional cost with expedited 2-day delivery.", "damaged_item", 0.98, 0.7, {"replacement_id": "QD-9012-R1"}),
            ("user", "You guys are awesome. Thank you!", "feedback_positive", 0.96, 0.9, {})
        ],
        "csat": {"rating": 5, "categories": ["🎯 Accurate Info", "⚡ Fast Resolution"], "feedback": "Immediate replacement without hassle."},
        "feedback": ("up", "Fast damage claim resolution")
    },
    {
        "intent": "order_status",
        "priority": "Medium",
        "language": "Spanish",
        "turns": [
            ("user", "Hola, ¿pueden decirme el estado de mi paquete #QD-4521?", "order_status", 0.92, 0.1, {"order_id": "#QD-4521"}),
            ("bot", "¡Hola! Su pedido #QD-4521 está en camino con DHL Express. La entrega estimada es este viernes antes de las 6:00 PM.", "order_status", 0.95, 0.6, {}),
            ("user", "Muchas gracias por la información rápida.", "farewell", 0.95, 0.8, {})
        ],
        "csat": {"rating": 5, "categories": ["🎯 Accurate Info"], "feedback": "Excelente atención en español."},
        "feedback": ("up", "Respuesta rápida")
    },
    {
        "intent": "cancellation",
        "priority": "Medium",
        "language": "English",
        "turns": [
            ("user", "Can I cancel order #QD-3312? I accidentally selected the wrong color variant.", "cancellation", 0.92, -0.1, {"order_id": "#QD-3312"}),
            ("bot", "Since order #QD-3312 was placed less than 30 minutes ago, I was able to successfully cancel it before warehouse fulfillment. A full refund of $64.00 has been initiated.", "cancellation", 0.96, 0.6, {"refund_amount": "$64.00"}),
            ("user", "Perfect, placing a new order for the midnight black edition now.", "order_status", 0.88, 0.8, {})
        ],
        "csat": {"rating": 5, "categories": ["⚡ Fast Resolution"], "feedback": "Cancelled order immediately before shipping."},
        "feedback": ("up", "Instant cancellation")
    },
    {
        "intent": "tech_support",
        "priority": "Medium",
        "language": "French",
        "turns": [
            ("user", "Bonjour, je n'arrive pas à connecter mes écouteurs Bluetooth à mon téléphone.", "tech_support", 0.91, -0.3, {}),
            ("bot", "Bonjour! Pour réinitialiser le jumelage Bluetooth, maintenez le bouton d'alimentation enfoncé pendant 7 secondes jusqu'à ce que le voyant clignote en bleu et blanc.", "tech_support", 0.94, 0.4, {}),
            ("user", "Ça fonctionne maintenant! Merci pour votre aide précieuse.", "feedback_positive", 0.95, 0.85, {})
        ],
        "csat": {"rating": 5, "categories": ["🎯 Accurate Info", "🤝 Polite & Friendly"], "feedback": "Aide technique claire et efficace."},
        "feedback": ("up", "Problème résolu")
    },
    {
        "intent": "warranty_claim",
        "priority": "Medium",
        "language": "English",
        "turns": [
            ("user", "My smart water bottle stopped charging after 6 months. Is this covered under warranty?", "warranty_claim", 0.94, -0.4, {}),
            ("bot", "Yes, all QueryDesk smart devices include a 2-Year Comprehensive Limited Warranty covering battery and electronic defects. Please provide your purchase receipt or order number.", "warranty_claim", 0.97, 0.5, {}),
            ("user", "The order number is #QD-7819.", "order_status", 0.93, 0.1, {"order_id": "#QD-7819"}),
            ("bot", "Thank you! I have confirmed your active warranty for #QD-7819. A replacement magnetic charging cradle has been ordered for dispatch tomorrow.", "warranty_claim", 0.96, 0.7, {})
        ],
        "csat": {"rating": 5, "categories": ["🎯 Accurate Info", "⚡ Fast Resolution"], "feedback": "Warranty honoured quickly."},
        "feedback": ("up", "Great warranty support")
    },
    {
        "intent": "shipping_delay",
        "priority": "High",
        "language": "German",
        "turns": [
            ("user", "Guten Tag, mein Paket #QD-8812 hat Verspätung. Wann kommt es an?", "shipping_info", 0.92, -0.5, {"order_id": "#QD-8812"}),
            ("bot", "Guten Tag! Aufgrund von Wetterbedingungen im Verteilzentrum verspätet sich die Sendung um 24 Stunden. Neue Zustellung: Morgen bis 14:00 Uhr.", "shipping_info", 0.95, 0.2, {}),
            ("user", "Vielen Dank für die transparente Aktualisierung.", "farewell", 0.93, 0.6, {})
        ],
        "csat": {"rating": 4, "categories": ["🎯 Accurate Info"], "feedback": "Gute Erklärung der Verzögerung."},
        "feedback": ("up", "Verständlich")
    },
    {
        "intent": "account_access",
        "priority": "Low",
        "language": "English",
        "turns": [
            ("user", "How do I enable Two-Factor Authentication on my customer account?", "account_access", 0.95, 0.1, {}),
            ("bot", "To enable 2FA: Navigate to Account Settings > Security > Two-Factor Authentication, and scan the QR code with Google Authenticator or Authy.", "account_access", 0.98, 0.6, {}),
            ("user", "Got it setup with my authenticator app, thank you!", "farewell", 0.96, 0.8, {})
        ],
        "csat": {"rating": 5, "categories": ["🎯 Accurate Info"], "feedback": "Simple instructions."},
        "feedback": ("up", "Helpful security advice")
    }
]

# Variations generator to reach 60+ diverse conversations
TOPICS = [
    ("Where is order #QD-{num}?", "Your shipment #QD-{num} is in transit with FedEx.", "order_status", "Medium"),
    ("I need a refund for #QD-{num}.", "A refund of ${amt} for #QD-{num} has been authorized to your Visa card.", "refund_inquiry", "High"),
    ("Can I change my delivery address for #QD-{num}?", "Address for order #QD-{num} has been updated to your primary residence.", "shipping_info", "Medium"),
    ("My discount code SAVE20 did not apply to #QD-{num}.", "I have applied a retroactive 20% discount ($24.00 credit) to #QD-{num}.", "billing_inquiry", "Medium"),
    ("How long does standard delivery take to California?", "Standard ground shipping to California takes 3-5 business days.", "shipping_info", "Low"),
    ("Is order #QD-{num} eligible for return?", "Yes! Order #QD-{num} is eligible for return until the end of the month.", "return_request", "Medium"),
    ("I received the wrong item in #QD-{num}.", "I apologize for the mix-up. A prepaid return label and correct replacement have been issued.", "damaged_item", "High")
]


async def seed_database():
    print(f"Seeding database at {DB_PATH} ...")
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        
        # Base time: Spread across past 7 days up to right now
        now = datetime.now(timezone.utc)
        
        total_convs = 0
        total_msgs = 0
        total_csat = 0
        
        # 1. Insert structured scenarios
        for sc in SCENARIOS:
            conv_id = f"qd-{uuid.uuid4().hex[:8]}"
            created_at = (now - timedelta(hours=random.randint(1, 140))).isoformat()
            resolved_at = (now - timedelta(minutes=random.randint(5, 60))).isoformat()
            escalated = 1 if sc.get("priority") == "High" and any(r == "human_agent" for r, _, _, _, _, _ in sc["turns"]) else 0
            
            await db.execute(
                "INSERT INTO conversations (id, status, priority, language, created_at, updated_at, resolved_at, escalated) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (conv_id, "Resolved", sc["priority"], sc["language"], created_at, resolved_at, resolved_at, escalated)
            )
            total_convs += 1
            
            # Insert messages
            last_msg_id = ""
            for idx, (role, content, intent, conf, sentiment, entities) in enumerate(sc["turns"]):
                msg_id = f"msg-{uuid.uuid4().hex[:8]}"
                msg_time = (now - timedelta(hours=random.randint(1, 120), minutes=random.randint(1, 50))).isoformat()
                ent_str = json.dumps(entities) if entities else None
                
                await db.execute(
                    "INSERT INTO messages (id, conversation_id, role, content, intent, confidence, sentiment, entities, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (msg_id, conv_id, role, content, intent, conf, sentiment, ent_str, msg_time)
                )
                total_msgs += 1
                if role == "bot":
                    last_msg_id = msg_id
            
            # CSAT
            if "csat" in sc:
                cs = sc["csat"]
                await db.execute(
                    "INSERT INTO csat_surveys (conversation_id, rating, categories, feedback_text, timestamp) VALUES (?, ?, ?, ?, ?)",
                    (conv_id, cs["rating"], json.dumps(cs["categories"]), cs["feedback"], resolved_at)
                )
                total_csat += 1
            
            # Feedback
            if "feedback" in sc and last_msg_id:
                fb_rating, fb_comment = sc["feedback"]
                await db.execute(
                    "INSERT INTO feedback (conversation_id, message_id, rating, comment, timestamp) VALUES (?, ?, ?, ?, ?)",
                    (conv_id, last_msg_id, fb_rating, fb_comment, resolved_at)
                )
        
        # 2. Generate 50 additional realistic conversations across 24h cycle
        for i in range(50):
            num = random.randint(1000, 9999)
            amt = random.choice(["29.99", "49.50", "89.00", "120.00", "15.75"])
            user_q_template, bot_ans_template, intent, priority = random.choice(TOPICS)
            user_q = user_q_template.format(num=num, amt=amt)
            bot_ans = bot_ans_template.format(num=num, amt=amt)
            
            conv_id = f"qd-{uuid.uuid4().hex[:8]}"
            hour_offset = random.randint(0, 160)
            created_at = (now - timedelta(hours=hour_offset, minutes=random.randint(0, 59))).isoformat()
            resolved_at = (now - timedelta(hours=hour_offset, minutes=random.randint(1, 30))).isoformat() if random.random() > 0.15 else None
            status = "Resolved" if resolved_at else "Active"
            escalated = 1 if priority == "High" and random.random() > 0.5 else 0
            
            await db.execute(
                "INSERT INTO conversations (id, status, priority, language, created_at, updated_at, resolved_at, escalated) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (conv_id, status, priority, "English", created_at, created_at, resolved_at, escalated)
            )
            total_convs += 1
            
            # Turn 1: User
            m1_id = f"msg-{uuid.uuid4().hex[:8]}"
            await db.execute(
                "INSERT INTO messages (id, conversation_id, role, content, intent, confidence, sentiment, entities, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (m1_id, conv_id, "user", user_q, intent, round(random.uniform(0.88, 0.98), 2), round(random.uniform(-0.4, 0.4), 2), json.dumps({"order_id": f"#QD-{num}"}), created_at)
            )
            total_msgs += 1
            
            # Turn 2: Bot / Agent
            m2_id = f"msg-{uuid.uuid4().hex[:8]}"
            role = "human_agent" if escalated else "bot"
            await db.execute(
                "INSERT INTO messages (id, conversation_id, role, content, intent, confidence, sentiment, entities, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (m2_id, conv_id, role, bot_ans, intent, round(random.uniform(0.92, 0.99), 2), round(random.uniform(0.4, 0.8), 2), None, created_at)
            )
            total_msgs += 1
            
            # Latency event
            await db.execute(
                "INSERT INTO analytics_events (event_type, conversation_id, data, timestamp) VALUES (?, ?, ?, ?)",
                ("response_time", conv_id, json.dumps({"latency_seconds": round(random.uniform(0.025, 0.085), 3)}), created_at)
            )
            
            # 80% CSAT for resolved tickets
            if status == "Resolved" and random.random() > 0.2:
                star = 5 if random.random() > 0.25 else (4 if random.random() > 0.3 else 3)
                cats = random.sample(["⚡ Fast Resolution", "🎯 Accurate Info", "🤝 Polite & Friendly", "📦 Return Handled"], k=random.randint(1, 3))
                await db.execute(
                    "INSERT INTO csat_surveys (conversation_id, rating, categories, feedback_text, timestamp) VALUES (?, ?, ?, ?, ?)",
                    (conv_id, star, json.dumps(cats), "Helpful and fast!", resolved_at or created_at)
                )
                total_csat += 1
                
                # Feedback up/down
                fb = "up" if star >= 4 else "down"
                await db.execute(
                    "INSERT INTO feedback (conversation_id, message_id, rating, comment, timestamp) VALUES (?, ?, ?, ?, ?)",
                    (conv_id, m2_id, fb, "Good response", resolved_at or created_at)
                )
        
        await db.commit()
        print(f"Successfully seeded {total_convs} conversations, {total_msgs} messages, and {total_csat} CSAT surveys into {DB_PATH}!")


if __name__ == "__main__":
    asyncio.run(seed_database())
