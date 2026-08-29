import logging
import re
import uuid
from typing import Dict, Any, Optional, List
from .context import ConversationContext
from .state_machine import DialogStateMachine, DialogState
from .slot_filler import SlotFiller

from backend.services.ecommerce_service import EcommerceService

logger = logging.getLogger(__name__)

class ConversationOrchestrator:
    def __init__(self, nlp_pipeline, knowledge_engine, db_manager, gemini_fallback):
        self.nlp = nlp_pipeline
        self.knowledge = knowledge_engine
        self.db = db_manager
        self.gemini = gemini_fallback
        self.ecommerce = EcommerceService()
        self.slot_filler = SlotFiller()
        self.sessions: Dict[str, tuple] = {}

    def _extract_order_id_from_message(self, text: str, entities: Dict[str, Any]) -> Optional[str]:
        """Extract Order ID explicitly from the current message text or entities."""
        # 1. Check current message entities from NLP
        for k in ('ORDER_ID', 'order_id', 'ORDER', 'order'):
            if k in entities and entities[k]:
                val = entities[k][0] if isinstance(entities[k], list) else entities[k]
                if val:
                    return str(val).strip()

        # 2. Regex matching on current text (#QD-XXXX, QD-XXXX, ORD-XXXX, #1234)
        match = re.search(r'#?(?:QD|ORD|order)[-_ ]?\d{3,8}', text, re.IGNORECASE)
        if match:
            return match.group(0).strip()

        match_generic = re.search(r'#\d{4,8}', text)
        if match_generic:
            return match_generic.group(0).strip()

        return None

    def _synthesize_knowledge_answer(self, article: Dict[str, Any], query: str) -> str:
        """Synthesize a natural, conversational response from a Knowledge Base article."""
        title = article.get("title", "Support Guide")
        content = article.get("content", "")
        
        # Split content into paragraphs for clean conversational structuring
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        main_summary = paragraphs[0] if paragraphs else content
        additional_info = "\n\n".join(paragraphs[1:]) if len(paragraphs) > 1 else ""

        # Friendly contextual wrap
        if "return" in query.lower():
            closing = "If you have an order you'd like to return, just share your Order ID (e.g. #QD-5678) and I'll generate a free prepaid label for you right away!"
        elif "refund" in query.lower() or "billing" in query.lower():
            closing = "If you need me to look up a specific transaction, feel free to share your Order ID or Transaction ID."
        elif "ship" in query.lower() or "delivery" in query.lower() or "track" in query.lower():
            closing = "If you'd like real-time tracking for an existing order, let me know your Order ID (e.g. #QD-1234)!"
        else:
            closing = "Let me know if you have any questions or if you'd like more details!"

        if additional_info:
            return f"**{title}**\n\n{main_summary}\n\n{additional_info}\n\n{closing}"
        return f"**{title}**\n\n{main_summary}\n\n{closing}"

    async def process_message(self, session_id: str, message: str, language: str = 'English', attachment_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # Get or create session context
        if session_id not in self.sessions:
            if len(self.sessions) >= 10000:
                oldest_key = next(iter(self.sessions))
                self.sessions.pop(oldest_key, None)
            ctx = ConversationContext(session_id)
            ctx.language = language
            fsm = DialogStateMachine()
            self.sessions[session_id] = (ctx, fsm)
            # Create conversation in DB
            if self.db:
                try:
                    if not await self.db.conversation_exists(session_id):
                        await self.db.create_conversation(session_id, language)
                except Exception as e:
                    logger.warning(f"DB create_conversation error: {e}")
        else:
            ctx, fsm = self.sessions[session_id]
            if language:
                ctx.language = language

        # Run NLP pipeline
        intent = "unknown"
        confidence = 0.0
        sentiment = 0.0
        sentiment_label = "neutral"
        entities = {}
        frustration_level = "low"
        suggested_response = ""
        response_source = "nlp_engine"

        if self.nlp:
            try:
                nlp_result = self.nlp.analyze(message)
                intent = nlp_result.intent
                confidence = nlp_result.confidence
                sentiment = nlp_result.sentiment
                sentiment_label = nlp_result.sentiment_label
                entities = nlp_result.entities
                frustration_level = nlp_result.frustration_level
                suggested_response = nlp_result.suggested_response
            except Exception as e:
                logger.error(f"NLP pipeline error: {e}")

        # Add user turn to context
        message_id = str(uuid.uuid4())[:8]
        ctx.add_turn("user", message, intent, confidence, sentiment, message_id)

        # Save message to DB
        if self.db:
            try:
                await self.db.save_message(session_id, f"user-{message_id}", "user", message, intent, confidence, sentiment, entities)
            except Exception as e:
                logger.warning(f"DB save_message error: {e}")

        # Extract order ID from current turn
        current_order_id = self._extract_order_id_from_message(message, entities)
        if current_order_id:
            ctx.filled_slots["order_id"] = current_order_id
            ctx.filled_slots["order_id_or_email"] = current_order_id
        
        active_order_id = current_order_id or ctx.filled_slots.get("order_id")

        # Update active intent
        if confidence >= 0.35 and intent != "unknown":
            if intent != ctx.active_intent:
                fsm.current_slot_retries = 0
            ctx.active_intent = intent

        msg_lower = message.lower().strip()

        # Comprehensive detection for live human agent / escalation requests
        escalation_phrases = [
            'speak to human', 'talk to human', 'human agent', 'live agent',
            'speak with a human', 'representative', 'customer care agent', 'transfer me to agent',
            'connect to human', 'connect to agent', 'connect with human', 'connect with agent',
            'connect to a human', 'connect to an agent', 'connect with an agent',
            'speak to an agent', 'speak with an agent', 'talk to an agent', 'talk with an agent',
            'human representative', 'real person', 'talk to a real person', 'speak with someone',
            'not able to connect to human', 'not able to connect to the human', 'not able to connect',
            'operator', 'live person', 'human support', 'customer service rep', 'helpdesk agent',
            'supervisor', 'escalate', 'escalation', 'manager'
        ]
        is_explicit_escalation = (
            intent == 'escalation'
            or any(p in msg_lower for p in escalation_phrases)
            or (('human' in msg_lower or 'agent' in msg_lower or 'person' in msg_lower) and ('connect' in msg_lower or 'talk' in msg_lower or 'speak' in msg_lower or 'need' in msg_lower or 'want' in msg_lower or 'transfer' in msg_lower or 'reach' in msg_lower or 'call' in msg_lower))
        )

        # State transition: Always process user message
        fsm.transition("user_message", ctx)

        response_text = ""
        products_payload = None

        # -------------------------------------------------------------
        # 0. ATTACHMENT / IMAGE ANALYSIS PROCESSING
        # -------------------------------------------------------------
        if attachment_info and isinstance(attachment_info, dict):
            analysis_text = attachment_info.get("analysis") or attachment_info.get("extracted_text") or attachment_info.get("summary")
            if analysis_text:
                response_text = (
                    f"I've received and processed your attachment! 📄\n\n"
                    f"**Analysis Summary**:\n{analysis_text}\n\n"
                    f"Would you like me to process a replacement, return, or warranty claim for this item?"
                )
                response_source = "vision_service"

        # -------------------------------------------------------------
        # 1. EXPLICIT HUMAN AGENT ESCALATION REQUEST
        # -------------------------------------------------------------
        if not response_text and is_explicit_escalation:
            fsm.transition("manual_escalate", ctx)
            response_text = (
                "🚨 **Connecting You to a Live Support Specialist...**\n\n"
                "Your chat session has been prioritized and dispatched to our **Live Support Desk**.\n\n"
                "• **Ticket Status**: `Escalated — Priority Queue #1`\n"
                "• **Assigned Dept**: `Tier-2 Customer Care & Logistics`\n"
                "• **Estimated Wait**: `< 30 seconds`\n\n"
                "An agent (such as **Sarah Connor** or **Alex Admin**) is joining this chat session now. "
                "You can also open the **[👨‍💼 Live Agent Console](/admin)** in another window to test live 2-way takeover directly."
            )
            response_source = "escalation"
            ctx.escalated = True

        # -------------------------------------------------------------
        # 2. GREETINGS & PLEASANTRIES
        # -------------------------------------------------------------
        elif not response_text and (intent == "positive_feedback" or any(k in msg_lower for k in ['thank you', 'thanks', 'awesome', 'great help', 'perfect thanks', 'thank u', 'thx', 'appreciate it', 'thanks for your help', 'thank you for your help'])):
            response_text = (
                "You're very welcome! I'm glad I could help. Let me know if there's anything else you need today! 😊"
            )
            response_source = "positive_feedback"

        elif not response_text and (intent == "greeting" or (any(msg_lower == k for k in ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening', 'hey there', 'greetings']) and len(msg_lower.split()) <= 3)):
            response_text = (
                "Hello! 👋 Welcome to QueryDesk Support. How can I help you today? "
                "I can assist with order tracking, easy returns, refunds, technical questions, or general account support."
            )
            response_source = "greeting"

        elif not response_text and (intent == "farewell" or any(k in msg_lower for k in ['bye', 'goodbye', 'see you', 'have a good day', 'that is all', 'thats all', 'done'])):
            response_text = (
                "Thank you for contacting QueryDesk Support! Have a wonderful day, and please feel free to reach back out anytime if you need anything else! ✨"
            )
            response_source = "farewell"

        # -------------------------------------------------------------
        # 3. SPECIFIC ACTIONS WITH ORDER ID
        # -------------------------------------------------------------
        # 3A. Return processing with Order ID (e.g. "I need to return an item from order #QD-5678")
        elif not response_text and (any(k in msg_lower for k in ['return', 'send back', 'exchange', 'rma']) or ctx.active_intent == "return_request") and (current_order_id or ('order' in msg_lower and active_order_id)):
            if not any(k in msg_lower for k in ['policy', 'how do i return', 'what is the return', 'rules']):
                reason = "Customer return request"
                ret = self.ecommerce.process_return(active_order_id, reason)
                response_text = (
                    f"All set! I've authorized the return for order **{active_order_id}**. 😊\n\n"
                    f"• **RMA Number**: `{ret.get('label_id', 'RET-884920')}`\n"
                    f"• **Prepaid Shipping Label**: Sent to your account email.\n"
                    f"• **Carrier Drop-off**: Drop off at any authorized **{ret.get('carrier', 'UPS Ground')}** location within 14 days.\n"
                    f"• **Refund Timeline**: Your refund will automatically post within 2 to 4 business days after warehouse arrival.\n\n"
                    f"Is there anything else I can assist you with regarding this return?"
                )
                response_source = "ecommerce_service"

        # 3B. Refund status with Order ID (e.g. "Where is my refund for #QD-9012?")
        elif not response_text and ('refund' in msg_lower or ctx.active_intent == "refund_status") and current_order_id:
            ref = self.ecommerce.check_refund_status(current_order_id)
            msg_detail = ref.get('message', f"Refund record found for order {current_order_id}.")
            response_text = (
                f"Here are the refund details for **{current_order_id}**:\n\n"
                f"{msg_detail}\n\n"
                f"Please let me know if you need any further billing assistance!"
            )
            response_source = "ecommerce_service"

        # 3C. Order cancellation with Order ID (e.g. "Can I cancel order #QD-4455?")
        elif not response_text and any(k in msg_lower for k in ['cancel order', 'cancel my order', 'stop order']) and active_order_id:
            response_text = (
                f"Order **{active_order_id}** has been successfully cancelled before warehouse dispatch! 🎉\n\n"
                f"A full refund has been initiated back to your original payment method, and a cancellation confirmation receipt has been sent to your email."
            )
            response_source = "ecommerce_service"

        # 3D. Damaged item claim with Order ID (e.g. "I received a damaged microwave from order #QD-3312")
        elif not response_text and any(k in msg_lower for k in ['damaged', 'broken', 'cracked', 'defective', 'shattered']) and active_order_id:
            response_text = (
                f"I am so sorry to hear that your item from order **{active_order_id}** arrived damaged! 😔\n\n"
                f"I have authorized an immediate **free replacement** (Replacement Shipment `#{active_order_id}-R1`) with expedited priority delivery.\n"
                f"You can also click the 📎 attachment button below to upload a photo of the damaged item for our carrier records."
            )
            response_source = "ecommerce_service"

        # 3E. Order Status Lookup with Order ID (e.g. "Track my order #QD-1234" or "#QD-1234")
        elif not response_text and current_order_id and (any(k in msg_lower for k in ['track', 'where is', 'status', 'package', 'shipment', 'order', 'delivery']) or ctx.active_intent == "order_status"):
            order = self.ecommerce.lookup_order(current_order_id)
            order_num = order.get("order_id", current_order_id)
            status_val = order.get("status", "In Transit")
            carrier_val = order.get("carrier", "Standard Carrier")
            track_num = order.get("tracking_number", "TRK-000000")
            items_list = order.get("items", ["Standard Package"])
            items_str = ", ".join(items_list) if isinstance(items_list, list) else str(items_list)
            amount_val = order.get("total_amount", "$0.00")
            location_val = order.get("current_location", "Distribution Center")
            delivery_val = order.get("estimated_delivery", "Pending update")
            timeline = order.get("timeline", [])
            timeline_latest = timeline[-1]["event"] if timeline and isinstance(timeline, list) else "In Transit"
            response_text = (
                f"Here are the real-time tracking details for order **{order_num}**:\n\n"
                f"• **Status**: {status_val}\n"
                f"• **Carrier**: {carrier_val} (Tracking: `{track_num}`)\n"
                f"• **Items**: {items_str} ({amount_val})\n"
                f"• **Current Location**: {location_val}\n"
                f"• **Estimated Delivery**: {delivery_val}\n\n"
                f"**Latest Checkpoint**: {timeline_latest}"
            )
            response_source = "ecommerce_service"

        # 3F. Product Catalog & Recommendations
        elif not response_text and not any(w in msg_lower for w in ['warranty', 'guarantee', 'how to return', 'refund policy', 'payment methods', 'business hours', 'address', 'password', 'never received']) and (
            any(k in msg_lower for k in ['recommend', 'suggest', 'catalog', 'what products do you sell', 'what do you sell', 'best sellers', 'popular products', 'show products', 'browse products', 'product recommendation', 'keyboards', 'monitors', 'headphones', 'gaming gear', 'popular gear'])
            or (ctx.active_intent == "product_inquiry" and any(k in msg_lower for k in ['recommend', 'options', 'catalog', 'models', 'selection', 'browse', 'show me', 'suggest']))
        ):
            products_payload = self.ecommerce.get_catalog(msg_lower)
            if products_payload:
                response_text = (
                    "Here are our top-rated featured products and best sellers! 🛍️\n\n"
                    "All products include **free express shipping**, **30-day money-back guarantee**, and a **1-year full warranty**.\n"
                    "Click on any item below to view technical specs or place an order:"
                )
                response_source = "ecommerce_catalog"

        # -------------------------------------------------------------
        # 4. KNOWLEDGE BASE & POLICY INQUIRIES (RAG ENGINE)
        # -------------------------------------------------------------
        if not response_text:
            if self.knowledge:
                best_match = self.knowledge.get_best_match(message, threshold=0.12)
                if best_match:
                    response_text = self._synthesize_knowledge_answer(best_match["article"], message)
                    response_source = "knowledge_base"

        # -------------------------------------------------------------
        # 5. INTENT-SPECIFIC ACTION PROMPTS (When no order ID was given)
        # -------------------------------------------------------------
        if not response_text:
            if ctx.active_intent == "order_status" or any(k in msg_lower for k in ['track my order', 'where is my order', 'track package', 'track shipment']):
                response_text = (
                    "I'd be happy to track your package! Please share your Order ID (e.g., #QD-1234 or #QD-5678) so I can fetch live GPS tracking."
                )
                response_source = "slot_filling"

            elif ctx.active_intent == "return_request" or any(k in msg_lower for k in ['return item', 'return an item', 'start a return']):
                response_text = (
                    "We offer **30-day free returns** with prepaid shipping labels! "
                    "Please provide your Order ID (e.g., #QD-5678) and I will immediately generate your prepaid return shipping label and RMA code."
                )
                response_source = "slot_filling"

            elif ctx.active_intent == "refund_status" or 'refund' in msg_lower:
                response_text = (
                    "Refunds are credited to your original payment method within **2 to 4 business days** after return receipt. "
                    "Please provide your Order ID (e.g., #QD-4567 or #QD-9012) to check real-time settlement status."
                )
                response_source = "slot_filling"

        # -------------------------------------------------------------
        # 6. INTENT CLASSIFIER SUGGESTED RESPONSE
        # -------------------------------------------------------------
        if not response_text and suggested_response and confidence >= 0.35:
            response_text = suggested_response
            response_source = "intent_response"

        # -------------------------------------------------------------
        # 7. GEMINI AI FALLBACK
        # -------------------------------------------------------------
        if not response_text and self.gemini and self.gemini.is_available():
            rag_context = ""
            if self.knowledge:
                rag_results = self.knowledge.search(message, top_k=3)
                rag_context = "\n\n".join([r["article"].get("content", "") for r in rag_results[:2]])
            try:
                response_text = await self.gemini.generate_response(message, ctx.get_context_summary(), rag_context, language)
                response_source = "gemini"
            except Exception as e:
                logger.error(f"Gemini fallback error: {e}")

        # -------------------------------------------------------------
        # 8. COMPREHENSIVE HELPFUL FALLBACK
        # -------------------------------------------------------------
        if not response_text or not response_text.strip():
            if self.knowledge:
                search_res = self.knowledge.search(message, top_k=1)
                if search_res:
                    response_text = self._synthesize_knowledge_answer(search_res[0]["article"], message)
                    response_source = "knowledge_base"

        if not response_text or not response_text.strip():
            response_text = (
                "I'm here to help with order tracking, returns, refunds, shipping questions, and account support! "
                "Feel free to share an order number (e.g. #QD-1234) or ask any question you have."
            )
            response_source = "fallback"

        # Complete the dialog turn
        fsm.transition("response_sent", ctx)

        # Apply language note for non-English
        response_text = self._format_response_with_language(response_text, language)

        # Add bot turn to context
        bot_msg_id = str(uuid.uuid4())[:8]
        ctx.add_turn("bot", response_text, intent, confidence, 0.0, bot_msg_id)

        # Save bot message to DB
        if self.db:
            try:
                await self.db.save_message(session_id, f"bot-{bot_msg_id}", "assistant", response_text, intent, confidence, 0.0)
            except Exception as e:
                logger.warning(f"DB save_message error: {e}")

        # Generate contextual suggestions
        suggestions = self._generate_suggestions(ctx.active_intent, fsm.get_state())

        return {
            "reply": response_text,
            "intent": intent,
            "confidence": round(confidence, 3),
            "sentiment": round(sentiment, 3),
            "sentiment_label": sentiment_label,
            "entities": entities,
            "suggested_actions": suggestions,
            "message_id": bot_msg_id,
            "response_source": response_source,
            "products": products_payload,
        }

    def _generate_suggestions(self, intent: str, state: DialogState) -> List[str]:
        if state == DialogState.ESCALATED:
            return ["Talk to human agent"]

        intent_suggestions = {
            "greeting": ["Where is my order?", "Return an item", "Billing help", "Talk to a human"],
            "order_status": ["Track another order", "Return this order", "Contact support"],
            "return_request": ["Check refund status", "Track my order", "Return policy"],
            "refund_status": ["Track my order", "Return another item", "Contact support"],
            "billing_issue": ["View billing history", "Dispute charge", "Contact support"],
            "technical_issue": ["Clear browser cache", "Try another browser", "Contact support"],
            "account_help": ["Reset password", "Update email", "Contact support"],
            "shipping_info": ["Track my package", "Change address", "Return policy"],
            "positive_feedback": ["I have another question", "Track an order", "That's all, thanks!"],
        }
        return intent_suggestions.get(intent, ["Where is my order?", "Return policy", "Billing help", "Talk to human"])

    def _format_response_with_language(self, response: str, language: str) -> str:
        lang_clean = (language or '').lower().strip()
        if lang_clean in ('en', 'english', ''):
            return response
        if not (self.gemini and self.gemini.is_available()):
            return f"{response}\n\n(Note: Responses in {language} will be generated in native language when a Gemini API key is configured.)"
        return response
