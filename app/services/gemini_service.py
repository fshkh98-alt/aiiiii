import google.generativeai as genai
import json
import re
import logging
from app.config import settings
from app.prompts import SYSTEM_INSTRUCTION, QUIZ_PROMPT, NEWS_PROMPT
from app.models import Message

logger = logging.getLogger(__name__)

# Check if API key is configured
if not settings.GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY is not set!")
else:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    logger.info("Gemini API configured successfully")

class GeminiService:
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise Exception("GEMINI_API_KEY is not configured. Please set it in environment variables.")

        self.model = genai.GenerativeModel(
            settings.MODEL_NAME,
            system_instruction=SYSTEM_INSTRUCTION,
            safety_settings=settings.SAFETY_SETTINGS
        )
        logger.info(f"Gemini model initialized: {settings.MODEL_NAME}")

    def _clean_json_response(self, text: str) -> str:
        """Clean markdown code blocks and extra whitespace from JSON response."""
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)
        text = re.sub(r"^[^{\[]*", "", text)
        text = re.sub(r"[^}\]]*$", "", text)
        return text.strip()

    def _safe_json_loads(self, text: str, fallback=None):
        """Safely parse JSON with fallback."""
        try:
            cleaned = self._clean_json_response(text)
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}, text: {text[:200]}")
            return fallback
        except Exception as e:
            logger.error(f"Unexpected error parsing JSON: {e}")
            return fallback

    async def get_chat_response(self, message: str, history: list[Message]):
        """Get chat response from Gemini with history."""
        try:
            gemini_history = [
                {"role": msg.role if msg.role == "user" else "model", "parts": [msg.content]}
                for msg in history
            ]

            chat = self.model.start_chat(history=gemini_history)
            response = chat.send_message(message)

            if not response or not response.text:
                raise Exception("Empty response from Gemini API")

            return response.text

        except Exception as e:
            logger.error(f"Gemini API Error in chat: {str(e)}")
            raise Exception(f"Gemini API failed: {str(e)}")

    async def generate_quiz_question(self):
        """Generate a quiz question from Gemini."""
        try:
            temp_model = genai.GenerativeModel(
                settings.MODEL_NAME,
                safety_settings=settings.SAFETY_SETTINGS
            )
            response = temp_model.generate_content(QUIZ_PROMPT)

            if not response or not response.text:
                raise Exception("Empty response from Gemini API")

            result = self._safe_json_loads(response.text)

            if not result:
                return {
                    "question": "ما هو الهدف الرئيسي من استخدام SIEM؟",
                    "options": [
                        "تسريع أداء الشبكة",
                        "جمع وتحليل السجلات الأمنية في الوقت الفعلي",
                        "تصميم مواقع الويب",
                        "إدارة قواعد البيانات"
                    ],
                    "correct_answer": "جمع وتحليل السجلات الأمنية في الوقت الفعلي",
                    "explanation": "SIEM (Security Information and Event Management) يقوم بجمع وتحليل السجلات الأمنية من مصادر متعددة في الوقت الفعلي للكشف عن التهديدات والاستجابة لها."
                }

            return result

        except Exception as e:
            logger.error(f"Gemini API Error in quiz: {str(e)}")
            raise Exception(f"Failed to generate quiz: {str(e)}")

    async def generate_cyber_news(self):
        """Generate cybersecurity news from Gemini."""
        try:
            temp_model = genai.GenerativeModel(
                settings.MODEL_NAME,
                safety_settings=settings.SAFETY_SETTINGS
            )
            response = temp_model.generate_content(NEWS_PROMPT)

            if not response or not response.text:
                raise Exception("Empty response from Gemini API")

            result = self._safe_json_loads(response.text)

            if not result or not isinstance(result, list):
                from datetime import datetime
                today = datetime.now().strftime("%Y-%m-%d")
                return [
                    {
                        "title": "اكتشاف ثغرة Zero-Day جديدة في أنظمة Windows",
                        "summary": "أعلنت Microsoft عن وجود ثغرة أمنية خطيرة تسمح بتنفيذ كود عن بُعد. الشركة تعمل على إصدار تحديث أمني عاجل.",
                        "category": "Zero-Day",
                        "date": today
                    },
                    {
                        "title": "هجوم ransomware يستهدف قطاع الرعاية الصحية",
                        "summary": "تعرضت عدة مستشفيات لهجوم ransomware منسق. الهجوم أدى إلى تعطيل الخدمات الطبية وسرقة بيانات المرضى.",
                        "category": "Ransomware",
                        "date": today
                    },
                    {
                        "title": "ثغرة في خدمات AWS تكشف بيانات العملاء",
                        "summary": "اكتشف باحثون أمنيون ثغرة في إعدادات افتراضية لخدمات AWS. AWS أصدرت توجيهات لتصحيح الإعدادات.",
                        "category": "Cloud Security",
                        "date": today
                    }
                ]

            return result

        except Exception as e:
            logger.error(f"Gemini API Error in news: {str(e)}")
            raise Exception(f"Failed to generate news: {str(e)}")

gemini_service = GeminiService()
