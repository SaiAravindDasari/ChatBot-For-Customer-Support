import os
import logging
from typing import Optional

from backend.config import Config
logger = logging.getLogger(__name__)

try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

class GeminiFallback:
    def __init__(self):
        self.client = None
        self.available = False
        self.token_count = 0
        
        if HAS_GENAI:
            api_key = os.environ.get("GEMINI_API_KEY") or Config.GEMINI_API_KEY
            if api_key:
                try:
                    self.client = genai.Client(api_key=api_key)
                    self.available = True
                    logger.info("Initialized Gemini 2.0 client.")
                except Exception as e:
                    logger.error(f"Failed to init Gemini client: {e}")
            else:
                logger.warning("GEMINI_API_KEY not found in environment.")

    def is_available(self) -> bool:
        return self.available

    async def generate_response(self, user_message: str, conversation_context: str = '', rag_context: str = '', language: str = 'English') -> str:
        if not self.is_available():
            return "I'm currently unable to access advanced AI processing. Please contact human support."

        system_prompt = f"You are a warm, professional customer support agent for QueryDesk, an e-commerce platform. Be concise (2-4 sentences). Never invent order numbers, tracking info, or account details. If you need info, ask the customer. Always respond in {language}. If RAG context is provided, use it to ground your answer."
        
        prompt = f"System: {system_prompt}\n"
        if rag_context:
            prompt += f"Knowledge Base Context:\n{rag_context}\n"
        if conversation_context:
            prompt += f"Conversation History:\n{conversation_context}\n"
            
        prompt += f"Customer: {user_message}\nAgent:"

        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                self.token_count += getattr(response.usage_metadata, 'total_token_count', 0)
            
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return "I'm sorry, I'm experiencing some technical difficulties. Let me connect you with a human agent."
