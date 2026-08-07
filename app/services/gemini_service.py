import google.generativeai as genai
import json
import re
import logging
from app.config import settings
from app.prompts import SYSTEM_INSTRUCTION, QUIZ_PROMPT, NEWS_PROMPT
from app.models import Message

logger = logging.getLogger(__name__)

# Configure API
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    logger.info("Gemini API configured")
else:
    logger.error("GEMINI_API_KEY not set!")

class GeminiService:
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise Exception("GEMINI_API_KEY is not configured!")

        self.model_name = settings.MODEL_NAME

        # v0.8.3 uses GenerativeModel with model name
        try:
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=SYSTEM_INSTRUCTION,
                safety_settings=settings.SAFETY_SETTINGS
            )
            logger.info(f"Gemini model initialized: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize model: {e}")
            # Try fallback model
            self.model_name = "models/gemini-1.5-flash-8b"
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=SYSTEM_INSTRUCTION,
                safety_settings=settings.SAFETY_SETTINGS
            )
            logger.info(f"Using fallback model: {self.model_name}")

    def _clean_json_response(self, text: str) -> str:
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)
        text = re.sub(r"^[^{\[]*", "", text)
        text = re.sub(r"[^}\]]*$", "", text)
        return text.strip()

    def _safe_json_loads(self, text: str, fallback=None):
        try:
            cleaned = self._clean_json_response(text)
            return json.loads(cleaned)
        except Exception as e:
            logger.error(f"JSON parse error: {e}")
            return fallback

    async def get_chat_response(self, message: str, history: list[Message]):
        try:
            # Build history for Gemini
            gemini_history = []
            for msg in history:
                role = "user" if msg.role == "user" else "model"
                gemini_history.append({"role": role, "parts": [msg.content]})

            # Start chat with history
            chat = self.model.start_chat(history=gemini_history)

            # Send message
            response = chat.send_message(message)

            if response and response.text:
                return response.text
            raise Exception("Empty response from Gemini")

        except Exception as e:
            logger.error(f"Chat error: {e}")
            raise Exception(f"Gemini API error: {str(e)}")

    async def generate_quiz_question(self):
        try:
            response = self.model.generate_content(QUIZ_PROMPT)

            if not response or not response.text:
                raise Exception("Empty response")

            result = self._safe_json_loads(response.text)
            if not result:
                raise Exception("Invalid JSON")

            return result

        except Exception as e:
            logger.error(f"Quiz error: {e}")
            # Return fallback
            return {
                "question": "ما هو الهدف الرئيسي من استخدام SIEM في الأمن السيبراني؟",
                "options": [
                    "تسريع أداء الشبكة",
                    "جمع وتحليل السجلات الأمنية في الوقت الفعلي",
                    "تصميم مواقع الويب",
                    "إدارة قواعد البيانات"
                ],
                "correct_answer": "جمع وتحليل السجلات الأمنية في الوقت الفعلي",
                "explanation": "SIEM (Security Information and Event Management) يقوم بجمع وتحليل السجلات الأمنية من مصادر متعددة في الوقت الفعلي للكشف عن التهديدات والاستجابة لها."
            }

    async def generate_cyber_news(self):
        try:
            response = self.model.generate_content(NEWS_PROMPT)

            if not response or not response.text:
                raise Exception("Empty response")

            result = self._safe_json_loads(response.text)
            if not result or not isinstance(result, list):
                raise Exception("Invalid JSON")

            return result

        except Exception as e:
            logger.error(f"News error: {e}")
            from datetime import datetime
            today = datetime.now().strftime("%Y-%m-%d")
            return [
                {
                    "title": "اكتشاف ثغرة Zero-Day جديدة في أنظمة Windows",
                    "summary": "أعلنت Microsoft عن وجود ثغرة أمنية خطيرة تسمح بتنفيذ كود عن بُعد.",
                    "category": "Zero-Day",
                    "date": today
                },
                {
                    "title": "هجوم ransomware يستهدف قطاع الرعاية الصحية",
                    "summary": "تعرضت عدة مستشفيات لهجوم ransomware منسق.",
                    "category": "Ransomware",
                    "date": today
                },
                {
                    "title": "ثغرة في خدمات AWS تكشف بيانات العملاء",
                    "summary": "اكتشف باحثون أمنيون ثغرة في إعدادات افتراضية لخدمات AWS.",
                    "category": "Cloud Security",
                    "date": today
                }
            ]

# Initialize
try:
    gemini_service = GeminiService()
except Exception as e:
    logger.error(f"Failed to initialize: {e}")
    class DummyService:
        async def get_chat_response(self, *args):
            return "❌ Error: " + str(e)
        async def generate_quiz_question(self, *args):
            raise Exception(str(e))
        async def generate_cyber_news(self, *args):
            raise Exception(str(e))
    gemini_service = DummyService()
